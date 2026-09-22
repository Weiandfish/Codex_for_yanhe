"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analysis import write_outputs
from .source import display_source, prepare_audio
from .transcribe import load_transcript, transcribe_audio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lecture-indexer", description="把课程音频转换为时间戳、关键词索引和课程提要")
    subcommands = parser.add_subparsers(dest="command", required=True)

    analyze = subcommands.add_parser("analyze", help="分析本地音频、直接媒体 URL 或延河课堂录播链接")
    analyze.add_argument("source", help="本地音频路径、媒体 URL 或 https://www.yanhekt.cn/session/... 链接")
    analyze.add_argument("--out", type=Path, default=Path("analysis"), help="输出目录，默认 ./analysis")
    analyze.add_argument("--model", default="turbo", help="Faster-Whisper 模型，默认 turbo")
    analyze.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    analyze.add_argument("--language", default="zh", help="音频语言，默认 zh")
    analyze.add_argument("--batch-size", type=int, default=8)
    analyze.add_argument("--browser-profile", type=Path, help="延河课堂登录专用浏览器目录；省略时登录只保留本次运行")
    analyze.add_argument("--browser-timeout", type=int, default=300, help="等待登录及音频加载的秒数")

    report = subcommands.add_parser("report", help="用已有 transcript.jsonl 重新生成索引和报告，无需再次转写")
    report.add_argument("transcript", type=Path)
    report.add_argument("--out", type=Path, help="输出目录，默认转写文件所在目录")
    report.add_argument("--source", default="", help="报告中显示的原始页面或文件路径")

    for command in (analyze, report):
        command.add_argument("--keyword", action="append", default=[], help="额外检索词，可重复传入")
        command.add_argument("--ollama-model", help="本机 Ollama 模型名称；不传则使用原句摘录")
        command.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="本机 Ollama 地址")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze":
            if args.batch_size < 1:
                raise ValueError("--batch-size 必须大于 0")
            output_dir = args.out.resolve()
            audio = prepare_audio(args.source, output_dir, browser_profile=args.browser_profile, timeout_seconds=args.browser_timeout)
            print(f"分析音频：{audio}", flush=True)
            metadata = transcribe_audio(audio, output_dir / "transcript.jsonl", model_name=args.model, device=args.device, language=args.language, batch_size=args.batch_size)
            print(f"转写完成：{metadata['segments']} 段，约 {metadata['duration'] / 60:.1f} 分钟", flush=True)
            source = display_source(args.source)
            rows = load_transcript(output_dir / "transcript.jsonl")
        else:
            output_dir = (args.out or args.transcript.parent).resolve()
            rows = load_transcript(args.transcript)
            source = display_source(args.source)
        paths = write_outputs(rows, output_dir, source=source, extra_keywords=args.keyword, ollama_model=args.ollama_model, ollama_url=args.ollama_url)
        print(f"报告：{paths['report']}\n转写：{paths['transcript']}", flush=True)
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
