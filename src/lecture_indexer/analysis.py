"""Keyword matches, readable transcripts, and source-grounded reports."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_TERMS = {
    "作业": ("作业", "交作业", "课后任务", "提交", "截止"),
    "考试": ("考试", "必考", "要考", "期末", "期中", "考题", "考核", "测验", "小测", "A4纸"),
    "签到": ("签到", "点名", "出勤", "打卡"),
    "平时练习": ("随堂", "练习", "小题", "平时分", "平时成绩", "平常成绩"),
}


def timestamp(seconds: float) -> str:
    rounded = max(0, int(round(seconds)))
    return f"{rounded // 3600:02d}:{rounded // 60 % 60:02d}:{rounded % 60:02d}"


def _normalize(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if c.isalnum())


def _word_characters(row: dict[str, Any]) -> tuple[str, list[float]]:
    characters: list[str] = []
    times: list[float] = []
    for word in row.get("words", []):
        for char in _normalize(str(word.get("word", ""))):
            characters.append(char)
            times.append(float(word.get("start", row["start"])))
    return "".join(characters), times


def _shorten(text: str, limit: int = 170) -> str:
    text = " ".join(text.split()).replace("|", "｜")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def find_events(rows: list[dict[str, Any]], extra_keywords: list[str] | None = None) -> list[dict[str, Any]]:
    terms = dict(DEFAULT_TERMS)
    if extra_keywords:
        terms["自定义"] = tuple(x.strip() for x in extra_keywords if x.strip())
    hits: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        normalized_text = _normalize(row["text"])
        word_text, word_times = _word_characters(row)
        for category, words in terms.items():
            for term in words:
                normalized_term = _normalize(term)
                if not normalized_term:
                    continue
                offset = 0
                word_offset = 0
                while (match := normalized_text.find(normalized_term, offset)) >= 0:
                    word_match = word_text.find(normalized_term, word_offset)
                    time = word_times[word_match] if word_match >= 0 and word_match < len(word_times) else float(row["start"])
                    if word_match >= 0:
                        word_offset = word_match + len(normalized_term)
                    context = row["text"]
                    if index + 1 < len(rows):
                        next_row = rows[index + 1]
                        if float(next_row["start"]) - float(row["end"]) <= 5:
                            context += " / " + next_row["text"][:90]
                    hits.append({
                        "category": category,
                        "term": term,
                        "start": round(time, 3),
                        "end": float(row["end"]),
                        "context": _shorten(context, 210),
                    })
                    offset = match + len(normalized_term)
    hits.sort(key=lambda item: (item["category"], item["start"]))
    groups: list[dict[str, Any]] = []
    for hit in hits:
        if groups and groups[-1]["category"] == hit["category"] and hit["start"] - groups[-1]["end"] <= 20:
            group = groups[-1]
            group["end"] = max(group["end"], hit["end"])
            if hit["term"] not in group["terms"]:
                group["terms"].append(hit["term"])
            if hit["context"] not in group["contexts"]:
                group["contexts"].append(hit["context"])
        else:
            groups.append({
                "category": hit["category"],
                "start": hit["start"],
                "end": hit["end"],
                "terms": [hit["term"]],
                "contexts": [hit["context"]],
            })
    return sorted(groups, key=lambda item: (item["start"], item["category"]))


def extractive_outline(rows: list[dict[str, Any]], window_seconds: int = 1200) -> list[dict[str, Any]]:
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[int(row["start"] // window_seconds)].append(row)
    outline = []
    for bucket, candidates in sorted(buckets.items()):
        def score(row: dict[str, Any]) -> float:
            text = row["text"]
            if not text:
                return 0.0
            diversity = len(set(text)) / len(text)
            topic = sum(text.count(term) for term in ("系统", "智能", "自主", "感知", "规划", "控制", "机器人", "无人", "课程"))
            return min(len(text), 140) * diversity + topic * 3

        selected = max(candidates, key=score)
        outline.append({"start": selected["start"], "text": _shorten(selected["text"], 110)})
    return outline


def _ollama_generate(prompt: str, model: str, url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Ollama 地址必须是本机 HTTP 地址")
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "think": False, "options": {"temperature": 0}}).encode()
    request = Request(url.rstrip("/") + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=600) as response:
        result = json.load(response)
    return str(result["response"]).strip()


def ollama_summary(rows: list[dict[str, Any]], model: str, url: str = "http://127.0.0.1:11434") -> str:
    buckets: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        buckets[int(row["start"] // 1800)].append(f"[{timestamp(row['start'])}] {row['text']}")
    partials = []
    for bucket, lines in sorted(buckets.items()):
        prompt = (
            "以下是课程音频的自动转写，可能有识别错误。只依据文本，用中文概括这一时段讲授的主题和关键观点，"
            "控制在三句话以内；忽略重复、噪声和听不清的词，不要编造作业或考试安排。\n\n"
            + "\n".join(lines)
        )
        partials.append(f"{timestamp(bucket * 1800)}–{timestamp((bucket + 1) * 1800)}：{_ollama_generate(prompt, model, url)}")
    final_prompt = (
        "根据下面逐时段课程摘要，写一份简洁的中文课程内容总结，分4至6点。"
        "只保留有来源支撑的内容；不要自行添加作业、考试或签到信息。\n\n" + "\n".join(partials)
    )
    return _ollama_generate(final_prompt, model, url)


def write_outputs(
    rows: list[dict[str, Any]],
    output_dir: Path,
    *,
    source: str = "",
    extra_keywords: list[str] | None = None,
    ollama_model: str | None = None,
    ollama_url: str = "http://127.0.0.1:11434",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    events = find_events(rows, extra_keywords)
    outline = extractive_outline(rows)
    transcript = output_dir / "transcript.txt"
    with transcript.open("w", encoding="utf-8") as handle:
        handle.write("自动转写；时间从音频开头计算，专有名词可能有误。\n")
        if source:
            handle.write(f"来源：{source}\n")
        handle.write("\n")
        for row in rows:
            handle.write(f"[{timestamp(row['start'])}–{timestamp(row['end'])}] {row['text']}\n")

    summary = None
    summary_error = None
    if ollama_model:
        try:
            summary = ollama_summary(rows, ollama_model, ollama_url)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            summary_error = str(exc)

    report = output_dir / "report.md"
    with report.open("w", encoding="utf-8") as handle:
        handle.write("# 课程音频分析\n\n")
        if source:
            handle.write(f"来源：{source}\n\n")
        handle.write("时间从音频开头计算。所有命中均为自动转写候选，涉及考核的内容请回听确认。\n\n")
        handle.write("## 关键词时间点\n\n")
        handle.write("| 时间 | 类别 | 命中词 | 上下文 |\n|---|---|---|---|\n")
        for event in events:
            context = _shorten(" / ".join(event["contexts"]), 240)
            handle.write(f"| {timestamp(event['start'])} | {event['category']} | {', '.join(event['terms'])} | {context} |\n")
        if not events:
            handle.write("| — | — | — | 未检出配置的关键词；这不等于音频中绝对没有相关安排。 |\n")
        handle.write("\n")
        for category in DEFAULT_TERMS:
            if not any(event["category"] == category for event in events):
                handle.write(f"- {category}：未检出明确关键词，请结合上下文人工核对。\n")
        handle.write("\n## 内容总结\n\n")
        if summary:
            handle.write(summary + "\n\n")
        else:
            handle.write("以下是按时间段挑选的原句摘录，便于快速浏览；需要完整语义总结时可启用本地 Ollama 模型。\n\n")
            for item in outline:
                handle.write(f"- {timestamp(item['start'])}：{item['text']}\n")
            handle.write("\n")
            if summary_error:
                handle.write(f"本地 Ollama 摘要未完成：{summary_error}\n\n")
        handle.write("## 文件\n\n- `transcript.txt`：完整分段转写\n- `transcript.jsonl`：含词级时间戳的机器可读转写\n")
    return {"report": report, "transcript": transcript}
