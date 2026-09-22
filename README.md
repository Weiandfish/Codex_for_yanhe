# Lecture Audio Indexer

把课程音频转成可搜索的时间戳转写、作业／考试／签到索引和课程提要。默认全部在本机处理；如已运行本机 Ollama，可选择生成更自然的内容摘要。

支持本地音频、直接媒体 URL，以及已生成的延河课堂录播链接（`/session/`）。**直播、视频画面中的文字和课件 OCR 不在当前版本范围内。**

## 快速开始

需要 Python 3.10+。在项目目录中运行：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
lecture-indexer analyze /path/to/lecture.aac --out analysis
```

首次运行会下载语音识别模型。CPU 可直接使用；有 NVIDIA CUDA 12 / cuDNN 9 环境时可用 `--device cuda` 加速。Faster-Whisper 使用 PyAV 解码，不要求单独安装 FFmpeg。GPU 环境的配置以 [Faster-Whisper 官方说明](https://github.com/SYSTRAN/faster-whisper#gpu)为准。

### 延河课堂录播

额外安装浏览器支持：

```bash
pip install -e ".[yanhe]"
playwright install chromium
lecture-indexer analyze https://www.yanhekt.cn/session/123456 --out analysis
```

程序会打开**单独的浏览器窗口**。请在该窗口登录并打开录播；检测到网页里的独立 AAC 音轨后，程序将音频下载到 `analysis/source_audio.aac` 再转写。它不会读取你平常 Chrome 或 Codex 内置浏览器的登录状态。默认登录资料只存在于本次运行的临时浏览器目录；若想复用登录，可显式提供 `--browser-profile /path/to/private-profile`，并妥善保管该目录。

这一适配基于录播页目前暴露独立音轨的方式，尚未在独立的 Playwright 登录流程中完成端到端验证。网站调整播放器后，可能需要更新 `source.py`。媒体签名会过期；如果下载失败，重新运行，让网页生成新地址即可。程序不在输出文件中保存带签名的地址。

### 关键词与课程摘要

```bash
lecture-indexer analyze lecture.mp3 --out analysis --device cuda \
  --keyword "课程论文" --keyword "补考"
```

默认检索作业、考试、签到，以及随堂练习相关说法。`--keyword` 可重复使用。报告中的命中是**待核对的候选**：例如“提交”可能是技术讨论，“随堂练习”也不一定是正式作业。

默认报告给出按时间段挑选的**原句摘录**，不假装它是模型写出的语义总结。如果已在本机运行 Ollama，并已准备适合中文的模型，可加 `--ollama-model 模型名` 来生成分时段和整体摘要：

```bash
lecture-indexer report analysis/transcript.jsonl --out analysis \
  --ollama-model qwen3:8b
```

摘要只发送到本机 `127.0.0.1:11434` 的 Ollama 服务。模型不存在或服务未启动时，报告会保留原句摘录并说明失败原因。可单独用 `report` 命令重复调整关键词或摘要，无需重新转写。Ollama 接口用法见其[官方 API 文档](https://docs.ollama.com/api/generate)。

## 输出文件

| 文件 | 内容 |
|---|---|
| `report.md` | 关键词时间点、未检出类别、课程提要 |
| `transcript.txt` | 便于阅读的完整分段转写 |
| `transcript.jsonl` | 含词级时间戳，便于二次检索与开发 |
| `source_audio.*` | 用网页或媒体 URL 分析时保存的原始音频 |

时间从录播／音频开头计算。语音识别对专有名词、噪声和老师口误可能不准确；考试与截止时间请回听原音确认。当前版本不会自动识别仅出现在 PPT 中的文字。

## 开发

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

核心模块：`source.py` 取得音频，`transcribe.py` 运行 Faster-Whisper，`analysis.py` 生成索引和报告，`cli.py` 提供命令行。欢迎通过 issue 和 pull request 改进其他平台适配、关键词规则与报告模板。

仅处理你有权访问和保存的课程内容；使用时遵守课程平台和学校规定。

## 许可证

MIT。见 [LICENSE](LICENSE)。
