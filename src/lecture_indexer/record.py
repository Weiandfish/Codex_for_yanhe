"""Capture the sound sent to a system playback device."""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any


def _soundcard():
    try:
        import soundcard as sc
    except ImportError as exc:
        raise RuntimeError('录制功能需要在项目目录安装：pip install -e ".[record]"') from exc
    return sc


def loopback_devices() -> tuple[list[dict[str, str]], str | None]:
    """Return available output monitors and the default output monitor ID."""
    sc = _soundcard()
    devices = [microphone for microphone in sc.all_microphones(include_loopback=True) if microphone.isloopback]
    default_id = None
    speaker = sc.default_speaker()
    if speaker is not None:
        default = sc.get_microphone(id=speaker.name, include_loopback=True)
        if default is not None and default.isloopback:
            default_id = default.id
    return [{"id": device.id, "name": device.name} for device in devices], default_id


def _select_loopback(device_id: str | None):
    sc = _soundcard()
    devices = [microphone for microphone in sc.all_microphones(include_loopback=True) if microphone.isloopback]
    if device_id:
        matches = [device for device in devices if device.id == device_id or device.name == device_id]
        if len(matches) != 1:
            raise ValueError("找不到唯一的系统音频回环设备。先运行 lecture-indexer devices 查看设备 ID。")
        return matches[0]
    speaker = sc.default_speaker()
    if speaker is not None:
        default = sc.get_microphone(id=speaker.name, include_loopback=True)
        if default is not None and default.isloopback:
            return default
    if len(devices) == 1:
        return devices[0]
    raise RuntimeError("无法确定默认系统音频回环设备。先运行 lecture-indexer devices，再用 --loopback 指定设备 ID。")


def record_system_audio(
    output: Path,
    *,
    duration: float | None = None,
    loopback_id: str | None = None,
    sample_rate: int = 48000,
) -> dict[str, Any]:
    """Save a loopback stream until the duration expires or Ctrl+C is pressed."""
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise ValueError("--duration 必须是大于 0 的有限秒数")
    if sample_rate < 8000 or sample_rate > 192000:
        raise ValueError("--sample-rate 必须在 8000 到 192000 之间")
    if output.suffix.lower() not in {".wav", ".flac"}:
        raise ValueError("录音文件扩展名必须是 .wav 或 .flac")
    if output.exists():
        raise FileExistsError(f"录音文件已存在：{output}")

    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError('录制功能需要在项目目录安装：pip install -e ".[record]"') from exc

    microphone = _select_loopback(loopback_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames_written = 0
    captured_frames = 0
    peak = 0.0
    interrupted = False

    def pad_to(audio, target_frames: int) -> None:
        nonlocal frames_written
        while frames_written < target_frames:
            count = min(target_frames - frames_written, sample_rate)
            audio.write(np.zeros(count, dtype="float32"))
            frames_written += count

    try:
        with microphone.recorder(samplerate=sample_rate) as recorder:
            # Request all available channels. Some Windows loopback devices cannot
            # capture correctly when explicitly opened with a single channel.
            with sf.SoundFile(str(output), mode="x", samplerate=sample_rate, channels=1, subtype="PCM_16") as audio:
                started = time.monotonic()
                deadline = started + duration if duration is not None else None
                print(f"开始录制系统声音：{microphone.name}；按 Ctrl+C 停止", flush=True)
                try:
                    while True:
                        remaining = deadline - time.monotonic() if deadline is not None else None
                        if remaining is not None and remaining <= 0:
                            break
                        chunk_size = min(4800, max(1, int(remaining * sample_rate))) if remaining is not None else 4800
                        block = np.asarray(recorder.record(numframes=chunk_size))
                        elapsed = time.monotonic() - started
                        target_frames = int(min(elapsed, duration) * sample_rate) if duration is not None else int(elapsed * sample_rate)
                        if block.size == 0:
                            pad_to(audio, target_frames)
                            time.sleep(0.02)
                            continue
                        mono = block.mean(axis=1) if block.ndim == 2 else block
                        if duration is not None:
                            available = max(0, int(duration * sample_rate) - frames_written)
                            mono = mono[:available]
                        pad_to(audio, max(frames_written, target_frames - len(mono)))
                        if duration is not None:
                            mono = mono[: max(0, int(duration * sample_rate) - frames_written)]
                        audio.write(mono)
                        frames_written += len(mono)
                        captured_frames += len(mono)
                        if len(mono):
                            peak = max(peak, float(np.max(np.abs(mono))))
                        # Some backends return silent buffers faster than real time.
                        # Keep the saved audio aligned with elapsed wall-clock time.
                        ahead = frames_written / sample_rate - (time.monotonic() - started)
                        if ahead > 0.25:
                            time.sleep(min(ahead - 0.25, 0.1))
                except KeyboardInterrupt:
                    interrupted = True
                    elapsed = time.monotonic() - started
                    pad_to(audio, int(min(elapsed, duration) * sample_rate) if duration is not None else int(elapsed * sample_rate))
                if duration is not None and not interrupted:
                    pad_to(audio, int(duration * sample_rate))
    except KeyboardInterrupt:
        interrupted = True

    if frames_written == 0:
        raise RuntimeError("没有录到音频帧；请检查系统播放设备和回环设备。")
    return {
        "path": output,
        "device": microphone.name,
        "duration": frames_written / sample_rate,
        "captured_frames": captured_frames,
        "peak": peak,
        "interrupted": interrupted,
    }
