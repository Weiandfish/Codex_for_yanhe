import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class TranscribeTests(unittest.TestCase):
    def test_auto_retries_on_cpu_when_cuda_library_is_missing(self):
        from lecture_indexer.transcribe import transcribe_audio

        devices = []

        class FakeModel:
            def __init__(self, model_name, *, device, compute_type):
                devices.append(device)
                if device == "auto":
                    raise RuntimeError("Library libcublas.so.12 is not found")

        class FakePipeline:
            def __init__(self, *, model):
                pass

            def transcribe(self, *args, **kwargs):
                segment = types.SimpleNamespace(start=1, end=2, text="  考试  ", words=[])
                info = types.SimpleNamespace(duration=3, language="zh")
                return [segment], info

        fake_module = types.ModuleType("faster_whisper")
        fake_module.WhisperModel = FakeModel
        fake_module.BatchedInferencePipeline = FakePipeline

        with tempfile.TemporaryDirectory() as directory, patch.dict("sys.modules", {"faster_whisper": fake_module}):
            output = Path(directory) / "transcript.jsonl"
            result = transcribe_audio(Path(directory) / "lecture.flac", output)
            self.assertEqual(devices, ["auto", "cpu"])
            self.assertEqual(result["segments"], 1)
            self.assertIn("考试", output.read_text(encoding="utf-8"))
            self.assertFalse(output.with_name(output.name + ".part").exists())


if __name__ == "__main__":
    unittest.main()
