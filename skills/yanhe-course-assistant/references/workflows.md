# Yanhe course workflows

## Locate the project

Use the current checkout when it contains `pyproject.toml` and `src/lecture_indexer`. Otherwise find the `Codex_for_yanhe` checkout or use an installed `lecture-indexer` command. Do not silently clone or install software unless that is part of the user's request.

For a fresh checkout:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[yanhe,record]"
playwright install chromium
```

On systems where `python` is not available, try `python3`. Keep browser profiles outside version control because they may contain authenticated session data.

## Inspect a course page

For a `https://www.yanhekt.cn/course/<id>` page, use an authenticated browser read only:

1. Record the course name, teacher, schedule, and visible session dates.
2. Prefer the latest actual lecture. Scheduled holiday recordings may contain only silence or room noise.
3. Compare session IDs with existing output directories before downloading or transcribing.
4. Open a session only when needed to identify its URL or verify media availability.

Do not treat the current browser URL alone as proof that the user selected that course; confirm the visible page title and course name.

## Analyze media

Local file:

```bash
lecture-indexer analyze /path/to/lecture.aac --out outputs/course_session
```

Chinese Yanhe recording:

```bash
lecture-indexer analyze https://www.yanhekt.cn/session/123456 \
  --out outputs/course_123456 --language zh \
  --browser-profile .browser-profile
```

English recording:

```bash
lecture-indexer analyze https://www.yanhekt.cn/session/123456 \
  --out outputs/course_123456 --language en \
  --keyword homework --keyword assignment --keyword "due date" \
  --keyword exam --keyword quiz --keyword attendance --keyword "roll call"
```

Use a private persistent browser profile only when the user wants reusable login. The session page adapter waits for a separate audio URL and downloads it without saving its expiring signature in reports.

If the transcript already exists:

```bash
lecture-indexer report outputs/course_123456/transcript.jsonl \
  --out outputs/course_123456 \
  --source https://www.yanhekt.cn/session/123456
```

## Record system audio

List loopback devices, then make a short test recording before a long class:

```bash
lecture-indexer devices
lecture-indexer record test.flac --duration 10
lecture-indexer record lecture.flac --duration 5400 --analyze \
  --out outputs/course_live
```

The selected playback device's complete sound is captured. Close unrelated audio sources and keep the class playing at a stable speed. The report timeline begins when recording starts.

## Check recording quality

Before trusting content:

- verify duration and that `transcript.jsonl` contains stable speech segments;
- inspect the beginning, suspected keyword passages, and ending;
- reject repetitive text produced only after extreme gain amplification;
- if the platform has independent, camera, and VGA tracks, compare them when the main track is silent;
- classify a scheduled empty recording as unavailable rather than inventing a lesson summary.

## Review findings

Search the transcript for both direct and indirect phrasing:

- Chinese: 作业、练习、题目、提交、上交、截止、下次、下周、考试、考核、小测、签到、点名、考勤、姓名、学号、名单、请假。
- English: homework, assignment, exercise, submit, hand in, turn in, due, deadline, exam, final, midterm, quiz, test, attendance, sign in, check in, roll call, name, student ID.

Read enough surrounding text to determine whether a phrase is a real course instruction. When a teacher refers to a task without stating its title, say that a task was mentioned and list the missing details.

## Reviewed report shape

The automatic `report.md` is a starting point. Replace or supplement it with a checked report containing:

1. session metadata and audio quality;
2. an action table with timestamps and exact meaning;
3. clear conclusions for homework, exams, attendance, deadlines, and submission method;
4. a chronological course summary;
5. suggested timestamps to replay;
6. limitations such as missing audio, unreadable slides, or details announced only in a course group.

Use the recording's elapsed time, not wall clock time. State calendar dates only when the session date and relative wording make the conversion unambiguous.
