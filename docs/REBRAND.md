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

## Caesar's decision (2026-11-26)

**Rename the existing YouTube channel and Facebook Page to AnglerMind** (keeps subscribers, the channel
ID and the upload tokens). Following from that, in this change:

- `factory/autopilot/tagline.py`: AnglerMind sign-offs per topic (`sign_off()` gives
  "AnglerMind: <line> Try it free at anglermind.com."), an "AnglerMind in action" playlist for tool demos.
- `rebrand()` runs on every description at post time in `cloud_post.py` and `facebook_post.py`, so the
  videos queued before the rename go out with "AnglerMind" in place of "Counterphysical" and the site link.
  The queue folders themselves are not edited (the hourly job may be posting them).
- New playlists are described as "AnglerMind Shorts".
- No new general-science topics: new videos follow the pillars in `docs/BRAND.md`.

Merge this after the channel is renamed in YouTube Studio, so posts never say AnglerMind on a channel
still called CounterPhysical.

## Deliberately not changed yet

| Thing | Why it waits |
|---|---|
| The queued `package.json` files | Rewritten at post time by `rebrand()` instead, so no folder the hourly job is posting gets edited |
| `docs/index.html`, `docs/privacy.html` (GitHub Pages) | They are the homepage and privacy policy that Google and Meta checked for the "CounterPhysical uploader" app. Change them together with the app's display name in Google Cloud and Meta, or the reviews can flag a mismatch |
| Google Cloud project `counterphysical-uploader`, GitHub secrets | Internal IDs, never shown to viewers. Renaming would mean new tokens for nothing |
| `D:\CounterPhysical` on Caesar's PC, `counterphysical/` in project files | Working folders; renaming breaks paths for no gain. New AnglerMind work can go in `D:\CounterPhysical\anglermind\` |
| `content/episodes/*`, `content/ledger/topics.jsonl` | History of what was made and posted. The ledger keeps refusing repeats |
| Visual Blueprint in `CLAUDE.md` | Replaced by the art-style study in its own thread, once Caesar picks the new look and character |

## Needs Caesar (only he can do these)

1. Decided 2026-11-26: rename both. Renaming in YouTube Studio keeps the subscribers, the channel ID
   and our upload token, so the cloud queue keeps working without new sign-ins.
2. YouTube Studio, Customisation, Basic info (name, handle `@anglermind` if free,
   description, link to anglermind.com); new avatar and banner. Facebook Page name change goes
   through Meta's review.
3. TikTok `@anglermind`: create or claim the account, then we connect it.

## Still to do

- Pages site and privacy page renamed together with the Google and Meta app names.
- Avatar and banner made from the site logo and colours.
- Autopilot topics switch from general science to the AnglerMind pillars in `docs/BRAND.md`.
