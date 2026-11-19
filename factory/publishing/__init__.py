"""Publishing workflow: package -> human approval (per platform) -> post.

This package is separate from production on purpose. Nothing in production imports it to upload,
and nothing here posts a video unless the matching platform entry was approved by the human in
Telegram for the exact package hash (video sha256 + cover sha256 + the platform's text).

  package.py     builds out/<slug>/publish/: package.json, review.md, cover.jpg (no credentials needed)
  copywriter.py  per-platform title / caption / hashtags from the storyboard (+ its `publish:` block)
  cover.py       the cover image in the house style (a frame from the video + headline + label card)
  approvals.py   the `posts` table: one row per (video, platform), approval bound to the package hash
  telegram.py    sends the package for review and handles the Approve / Skip buttons and text edits
  publisher.py   posts every APPROVED row whose hash still matches, through platforms/*
  platforms/     youtube.py (Data API v3), tiktok.py (Content Posting API), facebook.py (Reels API)
"""

PLATFORMS = ("youtube", "tiktok", "facebook")
