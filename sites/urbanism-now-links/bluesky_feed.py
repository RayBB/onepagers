"""Fetch the last week of posts from the Urbanism+ News Bluesky custom feed.

How it works:
- The feed URL .../did:<did>/feed/<rkey> maps to an AT-URI of the form
  at://<did>/app.bsky.feed.generator/<rkey>.
- Posts are read from Bluesky's public app.bsky.feed.getFeed endpoint, which
  needs no auth and is paginated by cursor (newest-first).
- We walk pages, keeping posts whose record createdAt is within the window,
  then stop once we age out of it. An exception is made for out-of-order old
  posts (e.g. a pinned feed description) that the generator injects at the top:
  those are skipped until the first in-window post is seen.
- Each post's shared link is normalized so duplicates collapse together:
  shorteners are resolved to their destination (cached), YouTube URLs are
  canonicalized to https://www.youtube.com/watch?v=<id>, and query strings and
  fragments are stripped.

Running this file writes the collected posts to bluesky_feed.json.
"""

import argparse
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit, urlunsplit

# The feed URL https://bsky.app/profile/did:plc:lptjvw6ut224kwrj7ub3sqbe/feed/aaapugyzmggrw
# maps to this AT-URI: at://<did>/app.bsky.feed.generator/<record_key>
FEED_URI = "at://did:plc:lptjvw6ut224kwrj7ub3sqbe/app.bsky.feed.generator/aaapugyzmggrw"
GET_FEED = "https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed"

# Domains that only exist to redirect elsewhere; resolve them to their target.
SHORTENERS = {
    "tinyurl.com",
    "bit.ly",
    "t.co",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "rebrand.ly",
    "lnkd.in",
    "fb.me",
    "j.mp",
    "shorturl.at",
    "t.ly",
    "tiny.cc",
    "cutt.ly",
    "rb.gy",
    "conta.cc",
    "share.google",
    "snip.ly",
    "trib.al",
}

_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_YT_ID = r"[A-Za-z0-9_-]{11}"
_resolve_cache: dict[str, str] = {}


def _resolve_shortener(url: str, timeout: float = 5.0) -> str:
    """Follow redirects to the final destination if `url` is a shortener."""
    if url in _resolve_cache:
        return _resolve_cache[url]
    if (urlsplit(url).hostname or "").lower() not in SHORTENERS:
        _resolve_cache[url] = url
        return url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resolved = resp.geturl()
    except Exception:
        resolved = url
    _resolve_cache[url] = resolved
    return resolved


def _normalize_youtube(url: str) -> str | None:
    """Collapse any YouTube URL form to https://www.youtube.com/watch?v=<id>."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host in _YT_HOSTS:
        if parts.path == "/watch":
            vid = parse_qs(parts.query).get("v", [""])[0]
            if re.fullmatch(_YT_ID, vid):
                return f"https://www.youtube.com/watch?v={vid}"
        m = re.match(rf"^/(?:embed|shorts|v)/({_YT_ID})", parts.path)
        if m:
            return f"https://www.youtube.com/watch?v={m.group(1)}"
    elif host == "youtu.be":
        m = re.match(rf"^/({_YT_ID})", parts.path)
        if m:
            return f"https://www.youtube.com/watch?v={m.group(1)}"
    return None


def normalize_url(url: str) -> str:
    """Resolve shorteners, canonicalize YouTube, strip query params/fragment."""
    if not url:
        return ""
    url = _resolve_shortener(url)
    yt = _normalize_youtube(url)
    if yt:
        return yt
    parts = urlsplit(url)
    return urlunsplit(
        (parts.scheme.lower(), (parts.hostname or "").lower(), parts.path, "", "")
    )


OUTPUT_FILE = "bluesky_feed.json"


def get_week_posts(days: int = 7, max_pages: int = 20) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cursor = None
    out: list[dict] = []
    started = False

    for _ in range(max_pages):
        params = {"feed": FEED_URI, "limit": 100}
        if cursor:
            params["cursor"] = cursor
        with urllib.request.urlopen(
            GET_FEED + "?" + urllib.parse.urlencode(params)
        ) as r:
            data = json.load(r)

        for item in data.get("feed", []):
            post = item["post"]
            created = datetime.fromisoformat(
                post["record"]["createdAt"].replace("Z", "+00:00")
            )
            if created >= cutoff:
                started = True
                rkey = post["uri"].rsplit("/", 1)[-1]
                embed = post.get("embed") or post["record"].get("embed")
                link = ""
                if embed and embed.get("external"):
                    link = normalize_url(embed["external"].get("uri", ""))
                out.append(
                    {
                        "text": post["record"].get("text", ""),
                        "post_url": f"https://bsky.app/profile/{post['author']['handle']}/post/{rkey}",
                        "url": link,
                        "comments": post.get("replyCount", 0),
                        "hearts": post.get("likeCount", 0),
                        "reshares": post.get("repostCount", 0),
                        "created_at": created.isoformat(),
                    }
                )
            elif started:
                # Feed is sorted newest-first; once we exit the recent window,
                # stop. (Old posts before any recent one are e.g. pinned posts.)
                return out

        cursor = data.get("cursor")
        if not cursor:
            break

    return out


def build_summary(posts: list[dict], top_n: int = 200) -> dict:
    """Build a summary with top posts and most-shared URLs."""
    sorted_posts = sorted(
        posts, key=lambda p: p["hearts"] + p["reshares"] + p["comments"], reverse=True
    )
    top_posts = sorted_posts[:top_n]

    url_groups: dict[str, list[dict]] = defaultdict(list)
    for p in posts:
        if p["url"]:
            url_groups[p["url"]].append(p)

    top_urls = [
        {"url": url, "count": len(grp), "posts": grp}
        for url, grp in sorted(url_groups.items(), key=lambda x: -len(x[1]))
        if len(grp) > 2
    ]

    return {"top_posts": top_posts, "top_urls": top_urls}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Output summary JSON with top posts and most-shared URLs",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=200,
        help="Number of top posts for summary (default: 200)",
    )
    args = parser.parse_args()

    posts = get_week_posts()

    if args.summary:
        summary = build_summary(posts, args.top)
        out = "bluesky_summary.json"
        with open(out, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        tp = len(summary["top_posts"])
        tu = len(summary["top_urls"])
        print(f"Wrote {tp} top posts and {tu} URL groups to {out}")
    else:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(posts)} posts to {OUTPUT_FILE}")
