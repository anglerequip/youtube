"""Full production run through the real CLI: voice -> render -> captions -> sfx -> mux -> QC -> DB.

Uses the test-only dummy voice and a low frame rate so it runs in under a minute. Set
E2E_TTS=kokoro to run the same test with the real voice (downloads ~350 MB of model files once).
"""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_produce_end_to_end(tmp_path):
    env = dict(os.environ,
               CONTENT_DIR=str(ROOT / "tests" / "fixtures" / "episodes"),
               OUT_DIR=str(tmp_path / "out"), DATA_DIR=str(tmp_path / "data"),
               TTS_PROVIDER=os.environ.get("E2E_TTS", "dummy"), FPS="12", MIN_SECONDS="3")
    r = subprocess.run([sys.executable, "-m", "factory", "produce", "test-pendulum"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]

    video = tmp_path / "out" / "test-pendulum" / "final.mp4"
    assert video.exists() and video.stat().st_size > 10_000
    qc = json.loads((tmp_path / "out" / "test-pendulum" / "qc.json").read_text())
    failed = [c for c in qc if not c["ok"] and c["severity"] == "error"]
    assert not failed, failed

    db = sqlite3.connect(tmp_path / "data" / "factory.db")
    state, sha = db.execute("SELECT state, video_sha256 FROM videos WHERE slug='test-pendulum'").fetchone()
    assert state == "QUALITY_CHECKED" and len(sha) == 64
    path = [r[0] for r in db.execute("SELECT to_state FROM transitions WHERE slug='test-pendulum' ORDER BY id")]
    assert path == ["STORYBOARDED", "RENDERED", "QUALITY_CHECKED"]
