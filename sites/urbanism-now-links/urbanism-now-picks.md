---
name: urbanism-now-picks
description: Use when the user wants to pull the latest Urbanism+ News Bluesky feed posts and pick which are a good fit for Urbanism Now. Run when they say "get the new bluesky posts", "review the feed", or "what's worth sharing".
---

# Urbanism Now Picks

1. Refresh the data:
   - `uv run python3 bluesky_feed.py` (writes `bluesky_feed.json`)
   - `uv run python3 bluesky_feed.py --summary --top 300` (writes `bluesky_summary.json`)
2. Review `bluesky_summary.json` — start with `top_posts`, then check `top_urls` for stories shared many times.
3. Pick genuinely unique/interesting posts for Urbanism Now:
   - Skip recycled car/bike-lane takes and obvious re-shares of the same article.
   - Favor novel angles: unexpected third places, fresh "next frontier" framing, concrete cost math, systemic pieces, quirky cultural/historical fits.
   - Editorial emphasis: prefer good things that are happening (wins, success stories, progress), but also include things we want to stop from happening (harms, regressions, injustices worth calling out).
4. When the user asks for a URL, give both the article URL and the original post URL (from `post_url`).
