import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now


class FakeRecorder:
    def __init__(self, clock):
        self.clock = clock

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def record(self, numframes):
        import numpy as np

        self.clock.now += 0.5
        return np.full((4800, 2), 0.2, dtype="float32")


class FakeMicrophone:
    name = "Test system output"

    def __init__(self, clock):
        self.clock = clock

    def recorder(self, samplerate):
        return FakeRecorder(self.clock)


class InterruptingMicrophone(FakeMicrophone):
    def recorder(self, samplerate):
        clock = self.clock

        class InterruptingRecorder(FakeRecorder):
            calls = 0

            def record(self, numframes):
                self.calls += 1
                if self.calls == 2:
                    clock.now += 0.5
                    raise KeyboardInterrupt
                return super().record(numframes)

        return InterruptingRecorder(clock)


class RecordTests(unittest.TestCase):
    def test_silent_gaps_keep_wall_clock_timestamps(self):
        import soundfile as sf
        from lecture_indexer import record

        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lecture.flac"
            with patch.object(record, "_select_loopback", return_value=FakeMicrophone(clock)), patch.object(record.time, "monotonic", clock.monotonic):
                result = record.record_system_audio(path, duration=1, sample_rate=48000)
            samples, rate = sf.read(path)
            self.assertEqual(rate, 48000)
            self.assertEqual(len(samples), 48000)
            self.assertEqual(result["duration"], 1)
            self.assertEqual(result["captured_frames"], 9600)
            self.assertTrue((samples[:19000] == 0).all())
            self.assertGreater(abs(samples[20000:24000]).max(), 0.1)

    def test_existing_recording_is_not_overwritten(self):
        from lecture_indexer.record import record_system_audio

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lecture.flac"
            path.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                record_system_audio(path, duration=1)
            self.assertEqual(path.read_bytes(), b"existing")

    def test_ctrl_c_finalizes_file_and_keeps_last_gap(self):
        import soundfile as sf
        from lecture_indexer import record

        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lecture.flac"
            with patch.object(record, "_select_loopback", return_value=InterruptingMicrophone(clock)), patch.object(record.time, "monotonic", clock.monotonic):
                result = record.record_system_audio(path, sample_rate=48000)
            self.assertTrue(result["interrupted"])
            self.assertEqual(sf.info(path).frames, 48000)

    def test_record_then_analyze_uses_saved_audio(self):
        from lecture_indexer import cli

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lecture.flac"
            with patch("lecture_indexer.record.record_system_audio", return_value={"duration": 1, "peak": 0.2}) as capture, patch.object(cli, "transcribe_audio", return_value={"segments": 1, "duration": 1}) as transcribe, patch.object(cli, "load_transcript", return_value=[{"start": 0, "end": 1, "text": "考试"}]), patch.object(cli, "write_outputs", return_value={"report": Path(directory) / "report.md", "transcript": Path(directory) / "transcript.txt"}):
                self.assertEqual(cli.main(["record", str(path), "--duration", "1", "--analyze"]), 0)
            capture.assert_called_once()
            self.assertEqual(transcribe.call_args.args[0], path)
            self.assertEqual(transcribe.call_args.args[1], Path(directory) / "lecture" / "transcript.jsonl")


if __name__ == "__main__":
    unittest.main()
