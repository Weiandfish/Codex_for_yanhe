---
name: yanhe-course-assistant
description: Inspect, record, transcribe, and review Yanhe Classroom lectures when a user asks about new recordings, course content, homework, exams, attendance, or precise video timestamps.
---

# Yanhe Course Assistant

Use the repository's `lecture-indexer` CLI to turn authorized Yanhe Classroom recordings or system audio into timestamped evidence and a concise course report.

## Choose the shortest reliable path

1. If a usable `transcript.jsonl` already exists, run `lecture-indexer report` and review the relevant passages. Do not transcribe the same audio again.
2. For a local audio/video file or direct media URL, run `lecture-indexer analyze`.
3. For a generated `https://www.yanhekt.cn/session/...` recording, use `lecture-indexer analyze`. It opens a separate Playwright browser profile and cannot reuse the Codex or ordinary Chrome login automatically.
4. For a live class, a protected player, or a recording whose media cannot be extracted, play it in the user's browser and use `lecture-indexer record` to capture system audio. Preserve silence so timestamps remain aligned with playback.
5. For a `/course/...` page, inspect the authenticated page first, record the course name and visible sessions, and process only sessions that are new or requested.

Read [references/workflows.md](references/workflows.md) when choosing commands, checking silent recordings, handling English classes, or producing the final report.

## Required review

- Treat generated keyword matches as candidates. Read the surrounding transcript before calling something an assignment, exam, deadline, or attendance action.
- Report explicit facts, reasonable inferences, and missing information separately. Never infer a task title, deadline, or submission channel from a generic mention.
- Recheck suspicious automatic text against nearby segments or the source audio. Common false positives include technical uses of “提交”, “作业环境”, “打卡” examples, and substrings such as “要考” inside “需要考虑”.
- If audio is nearly silent or contains only room noise, do not summarize hallucinated text. State that the recording has no reliable lecture audio and, when available, inspect alternate platform tracks.
- Use `--language en` for English teaching and include English terms such as `homework`, `assignment`, `due`, `exam`, `quiz`, `attendance`, and `roll call` in the review.

## Deliverables

Keep one directory per course session. Preserve `transcript.jsonl`, `transcript.txt`, and `report.md`. A reviewed report should include:

- course, teacher when known, session ID, date, and source URL;
- homework, exam, attendance, deadline, and submission findings with timestamps;
- a time ordered content summary;
- uncertain or unavailable information and the reason;
- the distinction between keyword candidates and manually checked conclusions.

Return the important conclusion directly to the user and link the local report. Do not make the user read the raw transcript to find the answer.
