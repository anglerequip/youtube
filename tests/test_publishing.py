"""Publishing: package building, approval bound to the exact package, and no posting without it."""
import dataclasses
import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

import factory.publishing.package as package
import factory.publishing.telegram as telegram
import factory.storyboard_engine as storyboard_engine
from factory.configuration import settings
from factory.database import DB, TransitionError
from factory.publishing import approvals, copywriter, publisher

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "episodes" / "test-pendulum"


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    p = tmp_path_factory.mktemp("v") / "final.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=540x960:rate=2",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "62", "-c:v", "libx264",
                    "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(p)], check=True)
    return p


@pytest.fixture
def env(tmp_path, monkeypatch, video):
    s = dataclasses.replace(settings, out_dir=tmp_path / "out", data_dir=tmp_path / "data")
    for mod in (storyboard_engine, package, telegram):
        monkeypatch.setattr(mod, "settings", s)
    v = tmp_path / "final.mp4"
    v.write_bytes(video.read_bytes())
    db = approvals.init(DB(tmp_path / "t.db"))
    pkg = package.build(storyboard_engine.load(FIXTURE), video=v)
    approvals.register(db, pkg)
    return {"db": db, "pkg": pkg, "video": v, "out": s.out_dir / "test-pendulum" / "publish"}


class FakeUploader:
    def __init__(self):
        self.calls = []

    def post(self, pkg):
        self.calls.append(pkg["slug"])
        return "abc123", "https://example.invalid/abc123"


def fakes():
    return {p: FakeUploader() for p in ("youtube", "tiktok", "facebook")}


def test_package_files_and_checks(env):
    pkg, out = env["pkg"], env["out"]
    for f in ("package.json", "review.md", "cover.jpg", "cover_safezones.jpg"):
        assert (out / f).exists(), f
    assert Image.open(out / "cover.jpg").size == (1080, 1920)
    assert pkg["ok"], [c for c in pkg["checks"] if not c["ok"]]
    yt, tt, fb = (pkg["platforms"][p] for p in ("youtube", "tiktok", "facebook"))
    assert "#shorts" in yt["description"] and yt["contains_synthetic_media"] is True
    assert tt["is_aigc"] is True and fb["is_ai_generated"] is True
    assert "AI text-to-speech" in yt["description"] or "AI voice" in yt["description"]
    assert len({yt["hash"], tt["hash"], fb["hash"]}) == 3


def test_short_video_fails_length_check(env, tmp_path):
    short = tmp_path / "short.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(env["video"]), "-t", "2", "-c", "copy", str(short)],
                   check=True)
    pkg = package.build(storyboard_engine.load(FIXTURE), video=short)
    assert not pkg["ok"]
    assert any(c["name"] == "video over the minimum length" and not c["ok"] for c in pkg["checks"])


def test_copy_cleans_markup_and_banned_words():
    assert copywriter.clean("the *bottom* doesn't   fall") == "the bottom doesn't fall"
    assert copywriter.hashtag("Slinky toy!") == "#slinkytoy"
    assert "disagrees" in copywriter.BANNED


def test_nothing_posts_without_approval(env):
    up = fakes()
    assert publisher.publish_approved(env["db"], up) == []
    assert all(not u.calls for u in up.values())


def test_approval_needs_the_hash_that_was_shown(env):
    db, pkg = env["db"], env["pkg"]
    with pytest.raises(TransitionError):
        approvals.approve(db, "test-pendulum", "tiktok", "00000000", by="t")
    approvals.approve(db, "test-pendulum", "tiktok", pkg["platforms"]["tiktok"]["hash"][:16], by="t")
    up = fakes()
    res = publisher.publish_approved(db, up)
    assert [r["platform"] for r in res] == ["tiktok"] and res[0]["ok"]
    assert up["tiktok"].calls == ["test-pendulum"] and not up["youtube"].calls
    assert approvals.get(db, "test-pendulum", "tiktok")["status"] == "POSTED"
    # a second run never posts twice
    assert publisher.publish_approved(db, up) == []
    assert len(up["tiktok"].calls) == 1


def test_change_after_approval_blocks_the_post(env):
    db, pkg, out = env["db"], env["pkg"], env["out"]
    approvals.approve(db, "test-pendulum", "youtube", pkg["platforms"]["youtube"]["hash"], by="t")
    data = json.loads((out / "package.json").read_text())
    data["platforms"]["youtube"]["title"] = "Something else"           # edited behind the approval
    (out / "package.json").write_text(json.dumps(data))
    up = fakes()
    res = publisher.publish_approved(db, up)
    assert not res[0]["ok"] and not up["youtube"].calls
    assert approvals.get(db, "test-pendulum", "youtube")["status"] == "FAILED"


def test_rerender_after_approval_blocks_the_post(env):
    db, pkg = env["db"], env["pkg"]
    approvals.approve(db, "test-pendulum", "facebook", pkg["platforms"]["facebook"]["hash"], by="t")
    with open(env["video"], "ab") as f:
        f.write(b"\0")
    up = fakes()
    res = publisher.publish_approved(db, up)
    assert not res[0]["ok"] and "video changed" in res[0]["error"] and not up["facebook"].calls


def test_rebuilt_package_voids_old_approval(env):
    db, pkg = env["db"], env["pkg"]
    approvals.approve(db, "test-pendulum", "tiktok", pkg["platforms"]["tiktok"]["hash"], by="t")
    pkg2 = json.loads(json.dumps(pkg))
    pkg2["platforms"]["tiktok"]["hash"] = "f" * 64
    assert approvals.register(db, pkg2) == ["tiktok"]
    assert approvals.get(db, "test-pendulum", "tiktok")["status"] == "READY"


class FakeTG:
    chat_id = "42"

    def __init__(self):
        self.calls, self.n = [], 100

    def call(self, method, files=None, **kw):
        self.calls.append((method, kw))
        self.n += 1
        return {"message_id": self.n}

    def send(self, text, **kw):
        return self.call("sendMessage", text=text, **kw)


def _press(tg, pkg, platform, user_id="42", action="ok"):
    data = telegram.buttons(pkg, platform)["inline_keyboard"][0][0 if action == "ok" else 1]["callback_data"]
    return {"id": "cb", "from": {"id": int(user_id), "username": "caesar"}, "data": data,
            "message": {"message_id": 7}}


def test_telegram_review_then_approve_posts(env):
    db, pkg = env["db"], env["pkg"]
    tg = FakeTG()
    ids = telegram.send_review(db, "test-pendulum", tg)
    assert len(ids) == 3 and approvals.get(db, "test-pendulum", "youtube")["status"] == "IN_REVIEW"
    assert any(m == "sendPhoto" for m, _ in tg.calls)
    up = fakes()
    telegram.handle_callback(db, tg, _press(tg, pkg, "youtube", user_id="999"), up)   # a stranger
    assert not up["youtube"].calls and approvals.get(db, "test-pendulum", "youtube")["status"] == "IN_REVIEW"
    telegram.handle_callback(db, tg, _press(tg, pkg, "youtube"), up)
    assert up["youtube"].calls == ["test-pendulum"]
    assert approvals.get(db, "test-pendulum", "youtube")["status"] == "POSTED"
    telegram.handle_callback(db, tg, _press(tg, pkg, "facebook", action="no"), up)
    assert approvals.get(db, "test-pendulum", "facebook")["status"] == "SKIPPED" and not up["facebook"].calls


def test_telegram_reply_edits_caption_and_voids_old_button(env):
    db, pkg = env["db"], env["pkg"]
    tg = FakeTG()
    telegram.send_review(db, "test-pendulum", tg)
    msg_id = approvals.get(db, "test-pendulum", "tiktok")["review_msg_id"]
    telegram.handle_edit(db, tg, {"message_id": 500, "from": {"id": 42}, "text": "New caption #physics #science #test",
                                  "reply_to_message": {"message_id": msg_id}})
    new = package.load_package("test-pendulum")
    assert new["platforms"]["tiktok"]["caption"] == "New caption #physics #science #test"
    assert new["platforms"]["tiktok"]["hash"] != pkg["platforms"]["tiktok"]["hash"]
    up = fakes()
    telegram.handle_callback(db, tg, _press(tg, pkg, "tiktok"), up)          # the old button
    assert not up["tiktok"].calls
    telegram.handle_callback(db, tg, _press(tg, new, "tiktok"), up)          # the new one
    assert up["tiktok"].calls == ["test-pendulum"]


def test_production_never_imports_publishing():
    src = (ROOT / "factory" / "production.py").read_text()
    assert "publishing" not in src.replace("Publishing is a separate workflow", "")


def test_cli_post_refuses_a_hash_caesar_did_not_see(tmp_path, video):
    import os
    import sys
    env = dict(os.environ, CONTENT_DIR=str(FIXTURE.parent), OUT_DIR=str(tmp_path / "out"),
               DATA_DIR=str(tmp_path / "data"), MIN_SECONDS="3")
    run = lambda *a: subprocess.run([sys.executable, "-m", "factory", *a], cwd=ROOT, env=env,
                                    capture_output=True, text=True)
    assert run("package", "test-pendulum", "--video", str(video)).returncode == 0
    r = run("post", "test-pendulum", "youtube", "--hash", "deadbeef", "--by", "test")
    assert r.returncode == 2 and "NOT APPROVED" in r.stdout
    r = run("posts", "test-pendulum")
    assert "POSTED" not in r.stdout and "APPROVED" not in r.stdout
