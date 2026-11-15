"""Saved styles: a style DNA learned from a reference video, kept in the workspace and applied to any of
the user's videos. A style is design language only (fonts, colours, text treatments, motion, pace, music mood);
the user's own footage and words stay theirs.

<workspace>/custom/styles/<slug>/style.json   the style DNA (nve.style_dna/2) + `saved`, `from_project`
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from nve import storyboard as SB, taste
from nve.paths import NveError
from nve.project import Project, slugify
from nve.registry import deep_merge
from nve.util import dump_json, log


def styles_dir(ws: Path) -> Path:
    return ws / "custom" / "styles"


def _path(ws: Path, name: str) -> Path:
    return styles_dir(ws) / slugify(name) / "style.json"


def save(prj: Project, ws: Path, name: str | None = None) -> dict:
    from nve_pro import ref
    chk = ref.check(prj)
    if not chk["ok"]:
        raise NveError("analysis/style_dna.json is not valid yet:\n" + "\n".join(chk["errors"]))
    dna = json.loads(prj.p("analysis", "style_dna.json").read_text(encoding="utf-8"))
    name = name or dna["name"]
    p = _path(ws, name)
    dna.update({"name": name, "saved": dt.date.today().isoformat(), "from_project": prj.path.name})
    dump_json(p, dna)
    prj.log("style saved", [f"'{name}' -> custom/styles/{p.parent.name}/style.json"])
    return {"saved": name, "path": str(p.relative_to(ws)), "missing_in_nve": dna.get("missing", [])}


def list_styles(ws: Path) -> list[dict]:
    out = []
    for p in sorted(styles_dir(ws).glob("*/style.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out.append({"name": d.get("name"), "id": p.parent.name, "summary": d.get("summary"), "fits": d.get("fits", []),
                    "saved": d.get("saved")})
    return out


def load(ws: Path, name: str) -> dict:
    p = _path(ws, name)
    if not p.exists():
        known = ", ".join(s["name"] for s in list_styles(ws)) or "none yet"
        raise NveError(f"No saved style '{name}'. Saved styles: {known}.")
    return json.loads(p.read_text(encoding="utf-8"))


def apply(prj: Project, ws: Path, name: str) -> dict:
    """Write the style's `apply` values into the project's storyboard (output, style, music), then re-apply the
    user's taste so their own corrections still win. Signature moves and limits come back as guidance."""
    dna = load(ws, name)
    ap = dna.get("apply") or {}
    sb = prj.load_storyboard()
    changed = []
    if ap.get("output"):
        sb["output"] = deep_merge(sb["output"], ap["output"])
        changed.append("output " + ", ".join(ap["output"]))
    if ap.get("style"):
        sb["style"] = deep_merge(sb.get("style", {}), ap["style"])
        changed.append("style " + ", ".join(ap["style"]))
    mu = ap.get("music") or {}
    audio = sb["tracks"].setdefault("audio", [])
    if mu.get("pick_from") and not any(a["kind"] == "bgm" for a in audio):
        audio.insert(0, {"kind": "bgm", "asset": mu["pick_from"][0], "volume": mu.get("volume", 0.1)})
        changed.append(f"music {mu['pick_from'][0]}")
    sb["style_ref"] = {"name": dna["name"], "applied": dt.date.today().isoformat()}
    rules = taste.rules_for(taste.load(ws), sb.get("template"))
    kept = taste.apply_defaults(sb, rules)
    errs = SB.validate(sb)
    if errs:
        raise NveError("The style made the storyboard invalid:\n" + "\n".join(errs))
    dump_json(prj.storyboard_path, sb)
    prj.log("style applied", [f"'{dna['name']}': {'; '.join(changed) or 'nothing to set'}"]
            + ([f"taste kept: {'; '.join(kept)}"] if kept else []))
    log(f"style '{dna['name']}' applied")
    return {"style": dna["name"], "changed": changed, "taste_kept": kept,
            "signature_moves": dna.get("signature_moves", []), "stamp": ap.get("stamp"), "limits": ap.get("limits"),
            "music": mu, "missing_in_nve": dna.get("missing", []),
            "next": "Plan the overlays in this style with the user's own words (use a signature move only where their "
                    "content gives a reason), then `nve plan refresh`."}
