# Rebrand: Counterphysical to AnglerMind

Started 2026-11-26 on Caesar's request ("make this project into an anglermind marketing project").
Brand rules for new videos: `docs/BRAND.md`.

## Done in this change (safe, nothing live moves)

- `CLAUDE.md`, `README.md`, `docs/ARCHITECTURE.md`: renamed to the AnglerMind video factory, with the
  new purpose (marketing and ads for anglermind.com) and a pointer to the brand brief.
- `docs/BRAND.md`: what AnglerMind is, which tools a video may show, how links work (site, never
  Amazon), pillars, colours, tagline, call to action.
- Default channel name, tagline and site in `factory/configuration.py` and `.env.example`
  (`CHANNEL_NAME=AnglerMind`, `CHANNEL_TAGLINE`, new `CHANNEL_SITE=anglermind.com`). Used by new
  storyboard descriptions and the old 2D wordmark.
- Brand names in code comments, the reviewer brief (`factory/qa/critic.py`) and the presenter scripts.

## Deliberately not changed yet

| Thing | Why it waits |
|---|---|
| `factory/autopilot/cloud_post.py`, `facebook_post.py` and the queued packages | They post live from `main` every hour. The last science Shorts in the queue keep their own copy. Switch the posting copy when the channel itself is renamed |
| `docs/index.html`, `docs/privacy.html` (GitHub Pages) | They are the homepage and privacy policy that Google and Meta checked for the "CounterPhysical uploader" app. Change them together with the app's display name in Google Cloud and Meta, or the reviews can flag a mismatch |
| Google Cloud project `counterphysical-uploader`, GitHub secrets | Internal IDs, never shown to viewers. Renaming would mean new tokens for nothing |
| `D:\CounterPhysical` on Caesar's PC, `counterphysical/` in project files | Working folders; renaming breaks paths for no gain. New AnglerMind work can go in `D:\CounterPhysical\anglermind\` |
| `content/episodes/*`, `content/ledger/topics.jsonl` | History of what was made and posted. The ledger keeps refusing repeats |
| Visual Blueprint in `CLAUDE.md` | Replaced by the art-style study in its own thread, once Caesar picks the new look and character |

## Needs Caesar (only he can do these)

1. Decide what happens to the existing YouTube channel and Facebook Page (rename to AnglerMind, or
   start new ones). Renaming in YouTube Studio keeps the subscribers, the channel ID and our upload
   token, so the cloud queue keeps working without new sign-ins.
2. If renamed: YouTube Studio, Customisation, Basic info (name, handle `@anglermind` if free,
   description, link to anglermind.com); new avatar and banner. Facebook Page name change goes
   through Meta's review.
3. TikTok `@anglermind`: create or claim the account, then we connect it.

## After Caesar decides

- Posting copy in `cloud_post.py` / `facebook_post.py` and `factory/autopilot/tagline.py` switches
  to AnglerMind sign-offs and playlists (fishing series, tool demos).
- Pages site and privacy page renamed together with the Google and Meta app names.
- Avatar and banner made from the site logo and colours.
- Autopilot topics switch from general science to the AnglerMind pillars in `docs/BRAND.md`.
