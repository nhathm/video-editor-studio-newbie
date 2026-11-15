"""Newbie edition only: the whisper model mirror on GitHub (nve.resources, added by build/export_newbie.py)."""


def test_resources_sparse_fetch_join_and_checksums(tmp_path, monkeypatch):
    import hashlib
    import json
    import shutil
    import subprocess

    import pytest
    from nve import resources
    from nve.paths import NveError
    blob = bytes(range(256)) * 100
    repo = tmp_path / "res"
    d = repo / "thing" / "v1"
    d.mkdir(parents=True)
    (repo / "other").mkdir()
    (repo / "other" / "big.bin").write_bytes(b"z" * 5000)
    parts = {"model.bin.part-aa": blob[:10000], "model.bin.part-ab": blob[10000:]}
    for n, b in parts.items():
        (d / n).write_bytes(b)
    (d / "config.json").write_text("{}")
    sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    files = {n: sha(b) for n, b in parts.items()}
    files.update({"config.json": sha(b"{}"), "model.bin": sha(blob)})
    cat = tmp_path / "resources.json"
    cat.write_text(json.dumps({"thing": {"version": "v1", "repo": f"file://{repo}", "path": "thing/v1",
                                         "join": {"model.bin": sorted(parts)}, "files": files}}))
    g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)  # noqa: E731
    g("init", "-q"); g("add", "-A"); g("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "m")
    monkeypatch.setattr(resources, "CATALOG", cat)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    out = resources.fetch("thing")
    assert (out / "model.bin").read_bytes() == blob and (out / "config.json").exists() and resources.is_cached("thing")
    assert not (out / "model.bin.part-aa").exists()
    shutil.rmtree(out)
    (d / "model.bin.part-ab").write_bytes(b"x" + blob[10001:])
    g("commit", "-qam", "bad")
    with pytest.raises(NveError):
        resources.fetch("thing")
