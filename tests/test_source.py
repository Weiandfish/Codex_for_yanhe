import unittest

from lecture_indexer.source import _media_url_from_page, display_source, is_yanhe_session


class FakePage:
    def evaluate(self, expression):
        self.expression = expression
        return ["https://host/recording.mp3", "https://host/SubAudio/audio.aac?signature=secret"]


class SourceTests(unittest.TestCase):
    def test_only_yanhe_recording_url_uses_browser_adapter(self):
        self.assertTrue(is_yanhe_session("https://www.yanhekt.cn/session/123456"))
        self.assertFalse(is_yanhe_session("https://www.yanhekt.cn/live/654321"))
        self.assertFalse(is_yanhe_session("https://yanhekt.cn.evil.test/session/123456"))

    def test_separate_audio_is_preferred(self):
        self.assertEqual(_media_url_from_page(FakePage()), "https://host/SubAudio/audio.aac?signature=secret")

    def test_report_source_drops_signed_query(self):
        self.assertEqual(display_source("https://host/audio.aac?token=private"), "https://host/audio.aac")


if __name__ == "__main__":
    unittest.main()
