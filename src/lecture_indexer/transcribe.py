"""Speech recognition and transcript storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def transcribe_audio(
    audio: Path,
    output: Path,
    *,
    model_name: str = "turbo",
    device: str = "auto",
    language: str = "zh",
    batch_size: int = 8,
) -> dict[str, Any]:
    # Imported here so `lecture-indexer report` works without loading ML libraries.
    from faster_whisper import BatchedInferencePipeline, WhisperModel

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".part")

    def run(selected_device: str) -> dict[str, Any]:
        try:
            compute_type = "float16" if selected_device == "cuda" else "default"
            model = WhisperModel(model_name, device=selected_device, compute_type=compute_type)
            pipeline = BatchedInferencePipeline(model=model)
            segments, info = pipeline.transcribe(
                str(audio),
                language=language,
                batch_size=batch_size,
                beam_size=5,
                vad_filter=True,
                word_timestamps=True,
            )
            count = 0
            with temporary.open("w", encoding="utf-8") as handle:
                for segment in segments:
                    record = {
                        "start": round(segment.start, 3),
                        "end": round(segment.end, 3),
                        "text": segment.text.strip(),
                        "words": [
                            {"start": round(word.start, 3), "end": round(word.end, 3), "word": word.word}
                            for word in (segment.words or [])
                        ],
                    }
                    if record["text"]:
                        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                        count += 1
                        if count % 50 == 0:
                            print(f"转写进度：{segment.end / 60:.1f} 分钟，{count} 段", flush=True)
            temporary.replace(output)
            return {"duration": info.duration, "language": info.language, "segments": count}
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    try:
        return run(device)
    except RuntimeError as exc:
        cuda_failure = any(word in str(exc).lower() for word in ("cuda", "cublas", "cudnn"))
        if device != "auto" or not cuda_failure:
            raise
        print(f"CUDA 不可用（{exc}）；改用 CPU 转写。", flush=True)
        return run("cpu")


def load_transcript(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    if not rows:
        raise ValueError(f"转写文件为空：{path}")
    return rows
