"""`nve ref`: measure a reference video's style and lay out sheets for Claude, then delete the video.

projects/<p>/reference/<id>/video.*, sheets/*.jpg   temporary, removed by clean()
projects/<p>/analysis/ref_<id>.json                 measurements (pace, shots, voice / music / tempo / beat)
projects/<p>/analysis/style_dna.json                written by Claude from the sheets + measurements
"""
from __future__ import annotations

import shutil
from pathlib import Path

from nve.analyze import beat, shots as AS
from nve_pro import download, sheets
from nve.paths import NveError
from nve.project import Project
from nve.util import VIDEO_EXT, dump_json, load_data, log, media_info


def _next_id(prj: Project) -> str:
    n = 1
    while prj.p("analysis", f"ref_r{n}.json").exists() or prj.p("reference", f"r{n}").exists():
        n += 1
    return f"r{n}"


def _aspect(w: int, h: int) -> str:
    for name, r in (("9:16", 9 / 16), ("16:9", 16 / 9), ("1:1", 1.0), ("4:5", 0.8), ("3:4", 0.75), ("4:3", 4 / 3)):
        if h and abs(w / h - r) < 0.03:
            return name
    return f"{w}:{h}"


def analyze(prj: Project, source: str, ref_id: str | None = None) -> dict:
    rid = ref_id or _next_id(prj)
    d = prj.p("reference", rid)
    if download.is_url(source):
        log(f"downloading the reference video ({rid})")
        video = download.fetch(source, d)
        origin = source
    else:
        f = Path(source).expanduser().resolve()
        if not f.exists():
            raise NveError(f"File not found: {f}")
        if f.suffix.lower() not in VIDEO_EXT:
            raise NveError(f"Not a video file: {f.name}")
        d.mkdir(parents=True, exist_ok=True)
        video = d / f"video{f.suffix.lower()}"
        shutil.copy2(f, video)
        origin = f.name
    info = media_info(video)
    if info["kind"] != "video":
        raise NveError("The reference has no video stream.")
    dur, fps = info["duration"], info.get("fps") or 30.0
    log(f"finding shots in {dur:.0f} s of video")
    shot_list = AS.shots_of(str(video), fps)
    pace = AS.pace(shot_list, dur)
    audio = None
    if info.get("has_audio"):
        log("measuring the soundtrack (voice, music, tempo, beat)")
        audio = beat.analyze(video, cut_times=[x["start"] for x in shot_list[1:]])
    sd = d / "sheets"
    sd.mkdir(parents=True, exist_ok=True)
    log("making sheets")
    made = [sheets.overview(video, dur, sd / "overview.jpg")]
    made += sheets.shot_sheets(video, shot_list, sd)
    made += sheets.strips(video, shot_list, sd, sheets.strip_starts(shot_list))
    res = {"schema": "nve.ref/1", "id": rid, "source": origin, "duration": dur, "width": info.get("width"),
           "height": info.get("height"), "aspect": _aspect(info.get("width") or 0, info.get("height") or 0), "fps": fps,
           "has_audio": info.get("has_audio"), "pace": pace, "hook_shot_s": shot_list[0]["duration"] if shot_list else None,
           "shots": shot_list, "audio": audio,
           "sheets": [str(p.relative_to(prj.path)) for p in made if p],
           "cleaned": False}
    dump_json(prj.p("analysis", f"ref_{rid}.json"), res)
    prj.log("reference", [f"{rid}: {origin}, {dur:.1f} s, {pace['shots']} shots, {pace['cuts_per_min']} cuts/min"])
    out = {k: v for k, v in res.items() if k != "shots"}
    if audio and audio.get("music"):  # keep the printed summary short; the full beat list stays in the JSON
        out["audio"] = {**audio, "music": {k: v for k, v in audio["music"].items() if k not in ("beats", "segments")}}
    out["next"] = ("Look at every sheet (overview, shots_*, strip_*) and write the style's design language to "
                   "analysis/style_dna.json (pro/skills/reference-style.md), `nve ref <project> --check`, "
                   "`nve style save <project>`, then `nve ref <project> --clean`.")
    return out


def clean(prj: Project, ref_id: str | None = None) -> dict:
    """Delete downloaded/copied reference videos and their sheets; keep the measurements and style_dna."""
    removed = []
    for d in sorted(prj.p("reference").glob(ref_id or "r*")):
        if d.is_dir():
            shutil.rmtree(d)
            removed.append(d.name)
            j = prj.p("analysis", f"ref_{d.name}.json")
            if j.exists():
                data = load_data(j)
                data.update({"cleaned": True, "sheets": []})
                dump_json(j, data)
    if removed:
        prj.log("reference cleaned", [f"deleted video and sheets of {', '.join(removed)}"])
    return {"removed": removed, "kept": [str(p.relative_to(prj.path)) for p in sorted(prj.p("analysis").glob("ref_*.json"))]
            + (["analysis/style_dna.json"] if prj.p("analysis", "style_dna.json").exists() else [])}


def check(prj: Project) -> dict:
    """Validate analysis/style_dna.json against nve.style_dna/2."""
    import json
    p = prj.p("analysis", "style_dna.json")
    if not p.exists():
        raise NveError("No analysis/style_dna.json yet: write it from the sheets first.")
    data = json.loads(p.read_text(encoding="utf-8"))
    schema = json.loads((Path(__file__).resolve().parent / "schema" / "style_dna.schema.json").read_text())
    try:
        import jsonschema
        errors = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}"
                  for e in jsonschema.Draft202012Validator(schema).iter_errors(data)]
    except ImportError:
        errors = [f"(root): '{k}' is required" for k in schema["required"] if k not in data]
    missing = data.get("missing") or []
    return {"ok": not errors, "errors": errors, "missing_in_nve": missing}
