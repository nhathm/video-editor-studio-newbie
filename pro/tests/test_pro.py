"""Tests for the Pro-only features (pro/python/nve_pro). Run: cd core && ../.venv/bin/python -m pytest -q ../pro/tests"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "core"), str(ROOT / "pro" / "python"), str(ROOT / "core" / "tests")]

from nve.paths import NveError  # noqa: E402
from test_core import _ff, _taste_sb, synth  # noqa: E402,F401  (shared helpers and the synthetic clips fixture)


def test_ref_analyze_and_clean(synth, tmp_path, monkeypatch):
    from nve import project
    from nve_pro import ref
    prj = project.create(tmp_path, [], name="mau")
    res = ref.analyze(prj, str(synth / "cuts.mp4"))
    assert res["id"] == "r1" and res["pace"]["shots"] == 5 and res["aspect"] == "9:16"
    assert {Path(s).name for s in res["sheets"]} >= {"overview.jpg", "shots_1.jpg", "strip_1.jpg"}
    assert all(prj.p(s).exists() for s in res["sheets"])
    out = ref.clean(prj)
    assert out["removed"] == ["r1"] and not prj.p("reference", "r1").exists()
    kept = json.loads(prj.p("analysis", "ref_r1.json").read_text())
    assert kept["cleaned"] and kept["sheets"] == [] and len(kept["shots"]) == 5
    assert ref.analyze(prj, str(synth / "flash.mp4"))["id"] == "r2"


def test_download_never_uses_cookies_and_explains_blocks(tmp_path, monkeypatch):
    from nve_pro import download
    from nve import util
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "", "ERROR: [youtube] x: Sign in to confirm you're not a bot")
    monkeypatch.setattr(download, "run", fake_run)
    monkeypatch.setattr(download, "ytdlp_cmd", lambda: ["yt-dlp"])
    with pytest.raises(NveError, match="never uses the user's accounts"):
        download.fetch("https://www.youtube.com/shorts/abc", tmp_path)
    assert len(calls) == 2  # retried exactly once
    assert "--no-cookies" in calls[0] and not any("cookies-from-browser" in c for c in calls[0])
    assert download.is_url("https://fb.com/reel/1") and not download.is_url("/tmp/a.mp4")


def test_shots_fade_in_joins_first_shot(synth, tmp_path):
    from nve.analyze import shots as S
    out = tmp_path / "fadein.mp4"
    _ff("-f", "lavfi", "-i", "color=c=black:s=160x284:r=30:d=0.3", "-f", "lavfi", "-i", "testsrc2=s=160x284:r=30:d=2",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", out)
    sh = S.shots_of(str(out), 30)
    assert len(sh) == 1 and sh[0]["fade_in"] and sh[0]["start"] == 0.0



DNA = {"schema": "nve.style_dna/2", "refs": ["r1"], "name": "Warm podcast bold", "summary": "warm dark room, big condensed titles",
       "fits": ["talking head"],
       "style": {"type": {"title": {"nve_font": "Anton", "case": "upper", "keyword_color": "#E53935"}},
                 "sound": {"music_mood": "warm, mellow", "sfx_density": "light"}},
       "signature_moves": [{"name": "wall of past videos", "what": "grid of thumbnails zooming in", "nve": "core:media.wall"}],
       "apply": {"output": {"speed": 1.1}, "style": {"font": {"title": "Anton", "caption": "Anton"}, "palette": {"accent": "#FFD400"}},
                 "music": {"mood": "warm", "volume": 0.1, "pick_from": ["lib:bgm/inspired"]}, "limits": {"stamps_per_min": 8}},
       "missing": ["captions without a pill"]}


def test_style_save_list_apply_keeps_taste(tmp_path):
    from nve import project, taste
    from nve_pro import styles
    ws = tmp_path
    prj = project.create(ws, [], name="dna")
    (prj.p("analysis") / "style_dna.json").write_text(json.dumps(DNA))
    saved = styles.save(prj, ws)
    assert saved["path"] == "custom/styles/warm-podcast-bold/style.json"
    assert [s["name"] for s in styles.list_styles(ws)] == ["Warm podcast bold"]
    target = project.create(ws, [], name="video")
    target.storyboard_path.write_text(json.dumps(_taste_sb()))
    taste.add(ws, "đừng tăng tốc", sets=["output.speed=1.0"])
    res = styles.apply(target, ws, "warm podcast bold")
    sb = json.loads(target.storyboard_path.read_text())
    assert sb["style"]["font"]["title"] == "Anton" and sb["style"]["palette"]["accent"] == "#FFD400"
    assert sb["output"]["speed"] == 1.0                      # the user's taste wins over the style
    assert sb["style_ref"]["name"] == "Warm podcast bold" and res["signature_moves"][0]["nve"] == "core:media.wall"
    assert sum(a["kind"] == "bgm" for a in sb["tracks"]["audio"]) == 1   # the storyboard already had music: kept
    with pytest.raises(NveError, match="No saved style"):
        styles.load(ws, "nope")


def test_style_dna_v1_is_rejected(tmp_path):
    from nve import project
    from nve_pro import ref
    prj = project.create(tmp_path, [], name="old")
    (prj.p("analysis") / "style_dna.json").write_text(json.dumps({"schema": "nve.style_dna/1", "refs": ["r1"]}))
    assert not ref.check(prj)["ok"]
