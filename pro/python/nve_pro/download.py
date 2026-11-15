"""Fetch a reference video from a link (Facebook reel, YouTube / Shorts, TikTok, ...) with yt-dlp.

Never uses the user's browser cookies or logins: only public videos. The file is temporary; `nve ref --clean`
deletes it once the style has been written down.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import sys
from pathlib import Path

from nve.paths import NveError
from nve.util import retry_once, run

URL_RE = re.compile(r"^https?://", re.I)
MAX_MB = 400


def is_url(s: str) -> bool:
    return bool(URL_RE.match(s.strip()))


def ytdlp_cmd() -> list[str] | None:
    """yt-dlp from nve's own Python first (kept up to date by nve-setup), else the one on PATH."""
    if importlib.util.find_spec("yt_dlp") is not None:
        return [sys.executable, "-m", "yt_dlp"]
    exe = shutil.which("yt-dlp")
    return [exe] if exe else None


def ytdlp_version() -> str | None:
    cmd = ytdlp_cmd()
    if not cmd:
        return None
    r = run([*cmd, "--version"], check=False)
    return (r.stdout or "").strip() or None


def fetch(url: str, out_dir: Path) -> Path:
    """Download one public video to out_dir/video.mp4 (<= 1080x1920). Retries once, then explains."""
    cmd = ytdlp_cmd()
    if not cmd:
        raise NveError("yt-dlp is not installed. Local: run nve-setup again (or `pip install -U yt-dlp`). "
                       "Otherwise ask the user to download the video and send the file.")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("video.*"):
        old.unlink()
    args = [*cmd, "--no-playlist", "--no-cookies", "--no-warnings", "--quiet", "--no-progress",
            "-f", "bv*[height<=1920][width<=1920]+ba/b[height<=1920]/b", "--merge-output-format", "mp4",
            "--max-filesize", f"{MAX_MB}M", "--socket-timeout", "30", "-o", str(out_dir / "video.%(ext)s"), url]

    def go():
        r = run(args, check=False, timeout=600)
        got = sorted(out_dir.glob("video.*"))
        if r.returncode != 0 or not got:
            tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
            raise RuntimeError(" | ".join(tail) or f"yt-dlp exit {r.returncode}")
        return got[0]

    try:
        return retry_once(go, "download of the reference video")
    except RuntimeError as e:
        msg = str(e)
        hint = ("The site blocked the download (common for YouTube from servers, or private / age-limited videos). "
                "Ask the user to download the video and send the file.")
        if "Unsupported URL" in msg:
            hint = "This link is not a video yt-dlp knows. Ask for a direct link to the video, or the file."
        elif "Sign in" in msg or "login" in msg.lower() or "private" in msg.lower():
            hint = "The video needs a login or is private; nve never uses the user's accounts. Ask for the file."
        raise NveError(f"Could not download the reference video: {msg[:300]}\n{hint}") from None
