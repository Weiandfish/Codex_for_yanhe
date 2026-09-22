"""Local files, direct media URLs, and Yanhe recorded-session pages."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen


MEDIA_EXTENSIONS = {".aac", ".m4a", ".mp3", ".mp4", ".wav", ".flac", ".ogg", ".webm"}


def display_source(source: str) -> str:
    """Avoid writing expiring media signatures from query strings to reports."""
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return source


def is_yanhe_session(source: str) -> bool:
    parsed = urlparse(source)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "yanhekt.cn" or host.endswith(".yanhekt.cn")) and parsed.path.startswith("/session/")


def download_media(url: str, destination: Path, *, referer: str | None = None) -> Path:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError("媒体地址必须是 HTTP(S) URL")
    headers = {"User-Agent": "Mozilla/5.0 (Lecture Audio Indexer)"}
    if referer:
        headers["Referer"] = referer
    request = Request(url, headers=headers)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    try:
        with urlopen(request, timeout=60) as response, temporary.open("wb") as handle:
            if response.status != 200:
                raise RuntimeError(f"媒体下载失败，HTTP {response.status}")
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
        if temporary.stat().st_size == 0:
            raise RuntimeError("媒体下载为空")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def _media_url_from_page(page: object) -> str | None:
    # The page's separate audio element has a normal signed AAC URL; video
    # elements backed by MediaSource often expose only unusable blob: URLs.
    candidates = page.evaluate(
        """() => [...document.querySelectorAll('audio,video')]
          .map(e => e.currentSrc || e.src || '')
          .filter(u => /^https?:\\/\\//.test(u) && /\\.(aac|m4a|mp3|wav)(\\?|$)/i.test(u))"""
    )
    return next((url for url in candidates if "SubAudio" in url), candidates[0] if candidates else None)


def yanhe_audio_url(page_url: str, *, browser_profile: Path | None = None, timeout_seconds: int = 300) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError('延河课堂页面模式需要安装可选依赖：pip install "lecture-audio-indexer[yanhe]"') from exc

    profile_manager = tempfile.TemporaryDirectory(prefix="lecture-indexer-") if browser_profile is None else None
    profile = Path(profile_manager.name) if profile_manager else browser_profile
    assert profile is not None
    profile.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(str(profile), headless=False)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(page_url, wait_until="domcontentloaded")
                print("请在弹出的浏览器中登录并打开录播，程序会等待独立音轨出现。", flush=True)
                page.wait_for_function(
                    """() => [...document.querySelectorAll('audio,video')]
                      .some(e => /^https?:\\/\\//.test(e.currentSrc || e.src || '') &&
                        /\\.(aac|m4a|mp3|wav)(\\?|$)/i.test(e.currentSrc || e.src || ''))""",
                    timeout=timeout_seconds * 1000,
                )
                url = _media_url_from_page(page)
                if not url:
                    raise RuntimeError("页面没有暴露独立音轨。请确认它是已生成的录播。")
                return url
            finally:
                context.close()
    finally:
        if profile_manager:
            profile_manager.cleanup()


def prepare_audio(source: str, output_dir: Path, *, browser_profile: Path | None = None, timeout_seconds: int = 300) -> Path:
    if is_yanhe_session(source):
        media_url = yanhe_audio_url(source, browser_profile=browser_profile, timeout_seconds=timeout_seconds)
        return download_media(media_url, output_dir / "source_audio.aac", referer="https://www.yanhekt.cn/")
    parsed = urlparse(source)
    if parsed.scheme in {"https", "http"}:
        suffix = Path(parsed.path).suffix.lower()
        if suffix not in MEDIA_EXTENSIONS:
            raise ValueError("普通网页无法直接分析；请传本地音频、直接媒体 URL，或延河课堂 /session/ 录播链接")
        return download_media(source, output_dir / f"source_audio{suffix}")
    path = Path(os.path.expanduser(source)).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"找不到音频文件：{path}")
    return path
