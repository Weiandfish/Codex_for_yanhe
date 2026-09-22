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

    compute_type = "float16" if device == "cuda" else "default"
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    pipeline = BatchedInferencePipeline(model=model)
    segments, info = pipeline.transcribe(
        str(audio),
        language=language,
        batch_size=batch_size,
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as handle:
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
    return {"duration": info.duration, "language": info.language, "segments": count}


def load_transcript(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    if not rows:
        raise ValueError(f"转写文件为空：{path}")
    return rows

