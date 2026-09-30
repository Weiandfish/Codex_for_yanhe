# Codex for Yanhe

面向延河课堂的本地课程录制、语音转写和课程信息核对工具，并提供可直接安装到 Codex 的 `yanhe-course-assistant` Skill。

项目可以把课程音频整理为带时间戳的完整转写，定位作业、考试、签到、截止时间等候选语句，并生成课程内容提要。音频和转写默认保留在本机；配置本机 Ollama 后，可以生成更自然的分段总结。

## 项目组成

| 组件 | 用途 |
|---|---|
| `lecture-indexer` | Python 命令行工具，负责音频获取、系统声音录制、Faster-Whisper 转写和报告生成 |
| `skills/yanhe-course-assistant` | Codex Skill，负责识别课程页面、选择处理方式、复核关键词上下文并整理最终结论 |

支持的来源：

- 本地音频或视频文件；
- 直接媒体 URL；
- 已生成的延河课堂录播页面（`/session/`）；
- 浏览器正在播放的直播、录播或其他系统声音；
- 已有的 `transcript.jsonl`，可跳过重复转写并重新生成报告。

中文和英文课程都支持。默认关键词包括 homework、assignment、due、exam、quiz、attendance、roll call 等英文表达。

## 安装

需要 Python 3.10 或更高版本。

```bash
git clone git@github.com:Weiandfish/Codex_for_yanhe.git
cd Codex_for_yanhe
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[yanhe,record]"
```

Windows PowerShell 激活虚拟环境：

```powershell
.venv\Scripts\Activate.ps1
pip install -e ".[yanhe,record]"
```

分析延河录播页面还需要安装 Playwright 浏览器：

```bash
playwright install chromium
```

首次转写会下载 Faster-Whisper 模型。CPU 可以直接使用；有 NVIDIA CUDA 12 和 cuDNN 9 时可传入 `--device cuda`。默认的 `--device auto` 在 CUDA 运行库不可用时自动改用 CPU。

## 安装 Codex Skill

命令行工具负责执行，Skill 负责让 Codex 选择正确流程并核对结果。建议把仓库中的 Skill 链接到 Codex Skills 目录，这样更新仓库后 Skill 也会同步更新。

Linux/macOS：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$(pwd)/skills/yanhe-course-assistant" \
  "${CODEX_HOME:-$HOME/.codex}/skills/yanhe-course-assistant"
```

如果目标位置已经存在，请先检查它是旧副本还是已有链接，再决定更新方式。Windows 也可以把 `skills\yanhe-course-assistant` 整个目录复制到 `%USERPROFILE%\.codex\skills\`。

重新打开 Codex 或开始一个新任务后，可以直接调用：

```text
$yanhe-course-assistant 检查这个延河课堂课程有没有新的录播；有的话转写并告诉我作业、考试、签到和课程内容。
```

也可以自然地提出这些请求：

```text
检查这节英文课有没有留 homework，给出视频时间。
录制当前浏览器播放的课程，结束后生成课程总结。
复查上次课程有没有点名，区分真正的考勤和普通技术语句。
```

Skill 的详细行为见 [SKILL.md](skills/yanhe-course-assistant/SKILL.md)。它会优先复用已有转写，并把自动关键词命中视为待核对候选，避免把“作业环境”“人脸打卡示例”“需要考虑”等内容误判成课程通知。

## 命令行快速开始

### 分析本地文件

```bash
lecture-indexer analyze /path/to/lecture.aac --out outputs/lecture
```

结果写入 `outputs/lecture/`。常用选项：

```bash
lecture-indexer analyze lecture.mp3 --out outputs/lecture \
  --language zh --model turbo --device auto \
  --keyword "课程论文" --keyword "补考"
```

### 分析延河课堂录播

```bash
lecture-indexer analyze https://www.yanhekt.cn/session/123456 \
  --out outputs/course_123456 \
  --browser-profile .browser-profile
```

程序会打开一个单独的 Playwright 浏览器窗口。请在该窗口登录并进入录播页面；程序检测到独立音轨后，会将其保存为 `source_audio.aac` 并开始转写。

这个浏览器不会自动继承普通 Chrome 或 Codex 内置浏览器的登录状态。`--browser-profile` 可以复用登录状态，其中可能含有账户会话信息，项目已经默认忽略 `.browser-profile/`，请勿提交到 Git。

媒体签名会过期。下载失败时重新运行，让网页生成新地址即可；报告只记录无查询参数的来源页面，不保存带签名的媒体地址。

### 录制直播或系统声音

先查看可用回环设备：

```bash
lecture-indexer devices
```

建议先试录 10 秒并确认声音正常：

```bash
lecture-indexer record test.flac --duration 10
```

正式录制：

```bash
lecture-indexer record lecture.flac
```

按 `Ctrl+C` 停止，文件会正常保存。也可以指定时长并在停止后自动分析：

```bash
lecture-indexer record lecture.flac --duration 5400 --analyze \
  --out outputs/lecture-live
```

录制的是所选播放设备的全部声音，包括其他应用的提示音。录制前应关闭无关音源。报告时间从开始录音计算，播放暂停期间的静音会保留，因此时间戳仍与录制时间轴一致。

Linux 需要可用的 PulseAudio 或 PipeWire 回环输入；其他系统需要 `lecture-indexer devices` 能列出回环设备。无法自动选择时，可传入设备 ID：

```bash
lecture-indexer record lecture.flac --loopback DEVICE_ID
```

### 英文课程

```bash
lecture-indexer analyze english-class.aac --out outputs/english-class \
  --language en
```

英文作业、考试和签到词已经包含在默认规则中。仍可以增加课程特有说法：

```bash
lecture-indexer report outputs/english-class/transcript.jsonl \
  --keyword "problem set" --keyword "office hours"
```

### 复用已有转写

调整关键词或重新生成报告时，无需重复运行 Whisper：

```bash
lecture-indexer report outputs/lecture/transcript.jsonl \
  --out outputs/lecture \
  --source https://www.yanhekt.cn/session/123456 \
  --keyword "课程论文"
```

### 使用本机 Ollama 生成总结

不指定模型时，报告使用按时间段挑选的原句摘录。已经在本机运行 Ollama 时，可以传入模型名称：

```bash
lecture-indexer report outputs/lecture/transcript.jsonl \
  --out outputs/lecture \
  --ollama-model qwen3:8b
```

摘要内容只发送到 `127.0.0.1:11434`。服务未启动或模型不存在时，程序保留原句摘录并记录失败原因。

## 输出文件

| 文件 | 内容 |
|---|---|
| `report.md` | 关键词时间点、未检出类别和课程提要 |
| `transcript.txt` | 便于阅读的完整分段转写 |
| `transcript.jsonl` | 含词级时间戳的机器可读转写 |
| `source_audio.*` | 从网页或媒体 URL 获取的原始音频 |

推荐按课程和 session ID 建目录，例如：

```text
outputs/
└── 强化学习理论与应用_录播900139/
    ├── source_audio.aac
    ├── transcript.jsonl
    ├── transcript.txt
    └── report.md
```

自动报告中的命中是候选证据。涉及作业题目、考试安排、签到、提交渠道和截止时间时，应阅读上下文并回听原音。语音识别对专有名词、公式、教室噪声和口音可能不准确。

当录播只有静音或环境声时，增益放大可能产生重复的幻听文本。可靠流程应检查音频能量、有效语音段和平台的独立音轨、摄像机音轨及 VGA 音轨，并将无法确认的课程标记为“无可靠授课音频”。

当前版本不自动识别只出现在 PPT、板书或课程群里的文字。`/course/` 页面用于查看课程与 session 列表，实际分析对象应是本地媒体、系统录音或 `/session/` 录播页面。

## 开发与验证

运行单元测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

验证 Skill 结构：

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py \
  skills/yanhe-course-assistant
```

核心模块：

- `source.py`：本地文件、媒体 URL 和延河 session 音轨获取；
- `record.py`：系统声音回环录制；
- `transcribe.py`：Faster-Whisper 转写与词级时间戳；
- `analysis.py`：中英文关键词索引和报告；
- `cli.py`：命令行入口；
- `skills/yanhe-course-assistant/`：Codex 工作流与报告核对规范。

## 使用范围

请仅处理自己有权访问和保存的课程内容，并遵守课程平台、学校和授课教师的规定。

## 许可证

MIT，见 [LICENSE](LICENSE)。
