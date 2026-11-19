# Publishing: package, approve in Telegram, post

Status 2026-11-19: package generation, approval and the three uploaders are built and tested with
fakes. Real posting needs the one-time account setup below.

**Approval channel (Caesar, 2026-11-19): the project chat.** For each platform, Claude posts a card
with the platform's text, the cover and the package hash, and two options: Post and Skip. When Caesar
taps Post, Claude runs `python -m factory post <slug> <platform> --hash <hash> --by "Caesar via project
chat"` on the PC. The Telegram bot below still works, but it's optional and isn't set up.

## How it works

```
 QA passes (produce / qa-gate)
        │
        ▼
 python -m factory package <slug>          automatic after QA; needs no credentials
   out/<slug>/publish/package.json         title, description, hashtags per platform + a hash for each
   out/<slug>/publish/review.md            the same, readable
   out/<slug>/publish/cover.jpg            1080x1920 cover in the house style
        │
        ▼
 Telegram (automatic if the bot is set up, or `python -m factory review <slug>`)
   cover + the exact video file + one message per platform:
   [Post to YouTube Shorts] [Skip]   [Post to TikTok] [Skip]   [Post to Facebook Reels] [Skip]
   Reply to a platform message to change its text ("title: ..." changes the title).
        │  (press "Post to ...")
        ▼
 python -m factory bot                     running on the PC: records the approval for that exact
                                           package hash, re-checks the files, posts, replies with the link
```

Rules the code enforces (tests in `tests/test_publishing.py`):

- Nothing posts unless you pressed "Post to <platform>" in Telegram, from your own chat id.
- Each approval covers one platform and one exact package: the video's sha256, the cover's sha256
  and that platform's text. Re-render the video or edit a caption and the approval is void; old
  buttons stop working.
- A row is claimed atomically before upload, so a double tap can't post twice.
- Production (`factory/production.py`) never imports the publishing code.
- AI labels are on by default (`AI_LABEL=true`): YouTube "altered or synthetic content",
  TikTok "AI-generated", Facebook "AI info". Our narration is a synthetic voice.
- The package checks: over 61 s, at most 90 s (Facebook's Reels limit), 9:16, title and caption
  lengths, `#shorts` present, hashtag counts, no banned wording, cover under 2 MB.

## Writing the copy

A Claude session writing an episode adds a `publish:` block to `storyboard.yaml` (see
`content/episodes/falling-slinky-3d`). Without one, defaults come from the title, the hook, the
description, sources and tags. Every number in the copy or on the cover must also be a `claims:` entry.

| Platform | What we send | Notes |
|---|---|---|
| YouTube Shorts | title (aim under 70 chars), description with lead, sources, how-it's-made line, tagline, `#shorts` + 3-4 topical hashtags; tags; category Science & Technology; not made for kids | Any vertical video up to 3 min is a Short. Custom thumbnails are tried but YouTube may keep a frame for the Shorts feed |
| TikTok | caption (one or two lines + 3-5 hashtags), AI label, cover frame time | The API can't take a custom cover image, only a frame time, so the cover frame is the same frame as cover.jpg |
| Facebook Reels | title, short description + 3 hashtags, AI label, cover image | Pages only, not personal profiles |

## What is automatic and what you do by hand

| Step | Automatic? |
|---|---|
| Titles, descriptions, hashtags, cover | Yes, after every QA pass |
| Sending the package to your phone | Yes, once the Telegram bot is set up |
| Approving each platform | **You**, one tap per platform in Telegram (by design) |
| Posting to YouTube | Yes, after your tap, once YouTube is set up |
| Posting to Facebook Reels | Yes, after your tap, once the Page token is set up |
| Posting to TikTok | Yes, after your tap, but **private-only until TikTok audits the app** (see below) |
| One-time account setup (below) | **You**, about an hour in total plus waiting for TikTok's review |
| Keeping `python -m factory bot` running on the PC | **You** start it (or Task Scheduler runs `bot --once` every few minutes) |

## One-time setup

Everything goes in `D:\CounterPhysical\youtube\.env` (git-ignored) or `D:\CounterPhysical\youtube\data\`.
Check progress any time with `python -m factory publish-check` (it posts nothing).

### 1. Telegram bot (optional, not used by default)
1. In Telegram, open @BotFather, send `/newbot`, pick a name. Copy the token into `.env` as
   `TELEGRAM_BOT_TOKEN=...`.
2. Send your new bot any message, then open `https://api.telegram.org/bot<token>/getUpdates` in a
   browser. The number after `"chat":{"id":` is your chat id: `TELEGRAM_CHAT_ID=...`.

### 2. YouTube (15 minutes)
1. Go to console.cloud.google.com, create a project (e.g. "Counterphysical uploader").
2. APIs & Services → Library → enable **YouTube Data API v3**.
3. OAuth consent screen: External, add your channel's Google account as a test user. Then press
   **Publish app** ("In production"). Unverified is fine for your own use; you'll see a warning
   screen once. While it stays in "Testing", Google expires the sign-in every 7 days.
4. Credentials → Create credentials → OAuth client ID → **Desktop app**. Download the JSON and save it
   as `D:\CounterPhysical\youtube\client_secret.json`.
5. On the PC: `python -m factory publish-auth youtube` and sign in with the channel's account.
6. Verify the channel with a phone number (youtube.com/verify) so custom thumbnails are allowed.

Limits: uploads use the API's daily quota; a few uploads a day is fine on the free default. If
uploads ever arrive locked to private, Google wants its free API compliance audit for the project.

### 3. Facebook Reels (20 minutes)
1. Create a Facebook **Page** for Counterphysical if there isn't one (Reels can't be posted to a
   personal profile through the API).
2. developers.facebook.com → My Apps → Create app → type **Business**.
3. Tools → Graph API Explorer: pick the app, add permissions `pages_show_list`,
   `pages_read_engagement`, `pages_manage_posts`, generate a user token and accept.
4. Exchange it for a long-lived token (Access Token Debugger → "Extend access token"), then in the
   Explorer call `me/accounts` with that token. Copy your Page's `id` and `access_token` into `.env`
   as `FACEBOOK_PAGE_ID` and `FACEBOOK_PAGE_TOKEN`. A Page token made this way does not expire.

As the app's admin posting to your own Page this works in development mode. If reels don't show
publicly, Meta wants App Review for `pages_manage_posts` (and may ask for business verification).

### 4. TikTok (30 minutes + review wait)
1. developers.tiktok.com → log in → Manage apps → Connect an app.
2. Add products **Login Kit** and **Content Posting API**, and switch on **Direct Post**.
3. Register a redirect URI and put it in `.env` as `TIKTOK_REDIRECT_URI`. Copy the Client key and
   Client secret into `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET`.
4. On the PC: `python -m factory publish-auth tiktok`, open the link, sign in as @counterphysical,
   paste back the address you land on.
5. Submit the app for review. Until TikTok approves it, the API only posts **private** videos
   (SELF_ONLY) and only to a **private** account. After approval set
   `TIKTOK_PRIVACY=PUBLIC_TO_EVERYONE`.

TikTok's review checks that the posting flow shows the account, lets you choose privacy and
interaction settings, and that you actively confirm each post. Our Telegram card shows the text,
AI label and privacy, and nothing posts without your tap; we may need to add a privacy picker to
the card if the reviewers ask. Personal tools are sometimes refused. If that happens the fallback
is TikTok's draft upload: the video lands in your TikTok inbox and you tap Post in the app.

## Commands

```
python -m factory package <slug> [--video f] [--send]
python -m factory review <slug>
python -m factory bot [--once]
python -m factory publish            # retry rows that are approved but not yet posted
python -m factory posts [<slug>]
python -m factory publish-auth youtube|tiktok
python -m factory publish-check
```

## Sources

- YouTube Data API, videos.insert: developers.google.com/youtube/v3/docs/videos/insert
- TikTok Content Posting API, Direct Post: developers.tiktok.com/doc/content-posting-api-reference-direct-post
- Facebook Reels Publishing API: developers.facebook.com/docs/video-api/guides/reels-publishing
