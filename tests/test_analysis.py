import json
import tempfile
import unittest
from pathlib import Path

from lecture_indexer.analysis import find_events, timestamp, write_outputs
from lecture_indexer.cli import main


def row(start, end, text, words=None):
    return {"start": start, "end": end, "text": text, "words": words or []}


class AnalysisTests(unittest.TestCase):
    def test_keyword_time_and_false_positives(self):
        rows = [
            row(10, 20, "这考验算法，也需要思考科考任务。"),
            row(30, 40, "期末考试占70%，要带一张A4纸。", [
                {"word": "期末", "start": 31, "end": 32},
                {"word": "考试", "start": 32, "end": 33},
                {"word": "占70%，要带一张", "start": 34, "end": 36},
                {"word": "A4纸", "start": 36, "end": 37},
            ]),
            row(100, 110, "请完成签到，课后交作业。"),
        ]
        events = find_events(rows)
        self.assertEqual(events[0]["category"], "考试")
        self.assertEqual({item["category"] for item in events}, {"考试", "签到", "作业"})
        self.assertEqual(events[0]["start"], 31)
        self.assertIn("A4纸", events[0]["terms"])
        self.assertEqual(timestamp(7521), "02:05:21")

    def test_report_can_be_regenerated_without_transcription(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = root / "transcript.jsonl"
            transcript.write_text(json.dumps(row(60, 70, "老师说期末有考试。"), ensure_ascii=False) + "\n", encoding="utf-8")
            result = main(["report", str(transcript), "--out", str(root), "--keyword", "期末"])
            self.assertEqual(result, 0)
            report = (root / "report.md").read_text(encoding="utf-8")
            self.assertIn("00:01:00", report)
            self.assertIn("签到：未检出", report)
            self.assertTrue((root / "transcript.txt").is_file())


if __name__ == "__main__":
    unittest.main()
