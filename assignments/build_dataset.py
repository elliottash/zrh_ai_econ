"""Build the problem-set dataset: news videos from Fox News and MSNBC.

Two collection modes:

  RSS  (default, no credentials)  the 15 most recent videos per channel.
       Good for a quick refresh and for checking the pipeline works.

  API  (--api, needs a free YouTube Data API v3 key in YOUTUBE_API_KEY)
       thousands of videos per channel, plus likeCount and commentCount.
       This is the mode to use for the real dataset. The key is free, needs
       no billing account, and the daily quota is far more than enough:
       ~2,500 videos costs about 100 of the 10,000 daily units.

  YTDLP (--ytdlp, no credentials) same coverage in principle, but UNRELIABLE.
       YouTube now serves a "confirm you're not a bot" challenge after a few
       dozen requests from one IP, at any concurrency. Kept because it works
       for small batches and needs no key, but do not plan around it.

Both modes write the same columns, so the notebook does not care which was used.

  video_id, outlet, channel_id, title, description, published_at,
  thumbnail_url, view_count, like_count, comment_count, duration_seconds, url

Usage
-----
    python3 build_dataset.py                        # RSS, ~45 rows
    python3 build_dataset.py --ytdlp --per-channel 600
    python3 build_dataset.py --api --per-channel 800
    python3 build_dataset.py --api --per-channel 800 --since 2026-01-01
"""
import argparse
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd

CHANNELS = {
    "Fox News": "UCXIJgqnII2ZOINSWNOGFThA",
    "MSNBC": "UCaXkIU1QidjPwiAYu6GcHjg",
}

# The NYT channel (UCqnbDFdCpuN8CMEg0VuEBqA) was dropped: it posts roughly two
# videos a day against ~50 for the two cable outlets, so any common time window
# leaves it an order of magnitude smaller and the comparison unbalanced.

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "m": "http://search.yahoo.com/mrss/",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}

COLUMNS = ["video_id", "outlet", "channel_id", "title", "description",
           "published_at", "thumbnail_url", "view_count", "like_count",
           "comment_count", "duration_seconds", "url"]

# days_since_publication is derived in main() and appended to the output.


def _get(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 * (k + 1))


# ----------------------------------------------------------------- RSS mode
def collect_rss():
    rows = []
    for outlet, cid in CHANNELS.items():
        xml = _get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
        root = ET.fromstring(xml)
        for e in root.findall("a:entry", NS):
            grp = e.find("m:group", NS)
            stats = grp.find("m:community/m:statistics", NS)
            rating = grp.find("m:community/m:starRating", NS)
            rows.append({
                "video_id": e.find("yt:videoId", NS).text,
                "outlet": outlet,
                "channel_id": cid,
                "title": e.find("a:title", NS).text,
                "description": (grp.find("m:description", NS).text or ""),
                "published_at": e.find("a:published", NS).text,
                "thumbnail_url": grp.find("m:thumbnail", NS).get("url"),
                "view_count": int(stats.get("views")) if stats is not None else None,
                # RSS gives a star-rating count, which is the closest thing to likes.
                "like_count": int(rating.get("count")) if rating is not None else None,
                "comment_count": None,
                "duration_seconds": None,
            })
        print(f"  {outlet}: {sum(r['outlet'] == outlet for r in rows)} videos")
    return rows


# --------------------------------------------------------------- yt-dlp mode
def collect_ytdlp(per_channel, workers=8):
    """Channel listing is cheap; per-video metadata is not, so thread it."""
    import yt_dlp
    from concurrent.futures import ThreadPoolExecutor

    def video_ids(cid):
        opts = {"quiet": True, "extract_flat": True, "skip_download": True,
                "no_warnings": True, "playlistend": per_channel}
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(
                f"https://www.youtube.com/channel/{cid}/videos", download=False)
        return [e["id"] for e in info.get("entries", []) if e.get("id")]

    def one(vid):
        opts = {"quiet": True, "skip_download": True, "no_warnings": True}
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                return y.extract_info(f"https://www.youtube.com/watch?v={vid}",
                                      download=False)
        except Exception:
            return None

    rows = []
    for outlet, cid in CHANNELS.items():
        ids = video_ids(cid)
        print(f"  {outlet}: {len(ids)} ids, fetching metadata ...", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            metas = list(ex.map(one, ids))
        got = 0
        for d in metas:
            if not d:
                continue
            ts = d.get("timestamp")
            up = d.get("upload_date")
            published = (pd.to_datetime(ts, unit="s", utc=True).isoformat() if ts
                         else (f"{up[:4]}-{up[4:6]}-{up[6:8]}T00:00:00+00:00" if up else None))
            rows.append({
                "video_id": d.get("id"),
                "outlet": outlet,
                "channel_id": cid,
                "title": d.get("title", ""),
                "description": d.get("description") or "",
                "published_at": published,
                # normalise to the stable jpg thumbnail URL pattern
                "thumbnail_url": f"https://i.ytimg.com/vi/{d.get('id')}/hqdefault.jpg",
                "view_count": d.get("view_count"),
                "like_count": d.get("like_count"),
                "comment_count": d.get("comment_count"),
                "duration_seconds": d.get("duration"),
            })
            got += 1
        print(f"  {outlet}: {got} videos with metadata", flush=True)
    return rows


# ----------------------------------------------------------------- API mode
def _api(endpoint, params, key):
    params = dict(params, key=key)
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}?{urllib.parse.urlencode(params)}"
    import json
    return json.loads(_get(url))


def _iso8601_to_seconds(s):
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return None
    h, mi, se = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + se


def collect_api(per_channel, since=None):
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        sys.exit("Set YOUTUBE_API_KEY (free, from console.cloud.google.com).")

    rows = []
    for outlet, cid in CHANNELS.items():
        ch = _api("channels", {"part": "contentDetails", "id": cid}, key)
        uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        ids, page, exhausted = [], None, False
        while len(ids) < per_channel and not exhausted:
            resp = _api("playlistItems",
                        {"part": "contentDetails", "playlistId": uploads,
                         "maxResults": 50, **({"pageToken": page} if page else {})}, key)
            batch = resp.get("items", [])
            if not batch:
                break
            for it in batch:
                d = it["contentDetails"]
                # The uploads playlist is newest-first, so the first video older
                # than `since` means everything after it is older too.
                if since and d.get("videoPublishedAt", "") < since:
                    exhausted = True
                    break
                ids.append(d["videoId"])
            page = resp.get("nextPageToken")
            if not page:
                break

        ids = ids[:per_channel]
        for i in range(0, len(ids), 50):
            chunk = ids[i:i + 50]
            resp = _api("videos",
                        {"part": "snippet,statistics,contentDetails",
                         "id": ",".join(chunk)}, key)
            for v in resp.get("items", []):
                sn, st = v["snippet"], v.get("statistics", {})
                thumbs = sn.get("thumbnails", {})
                best = (thumbs.get("maxres") or thumbs.get("standard")
                        or thumbs.get("high") or thumbs.get("medium") or {})
                rows.append({
                    "video_id": v["id"],
                    "outlet": outlet,
                    "channel_id": cid,
                    "title": sn.get("title", ""),
                    "description": sn.get("description", ""),
                    "published_at": sn.get("publishedAt"),
                    "thumbnail_url": best.get("url"),
                    "view_count": int(st["viewCount"]) if "viewCount" in st else None,
                    "like_count": int(st["likeCount"]) if "likeCount" in st else None,
                    "comment_count": int(st["commentCount"]) if "commentCount" in st else None,
                    "duration_seconds": _iso8601_to_seconds(
                        v.get("contentDetails", {}).get("duration")),
                })
        print(f"  {outlet}: {sum(r['outlet'] == outlet for r in rows)} videos")
    return rows


# ----------------------------------------------------------------- assemble
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", action="store_true", help="use the YouTube Data API")
    ap.add_argument("--ytdlp", action="store_true", help="use yt-dlp, no key needed")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--per-channel", type=int, default=800)
    ap.add_argument("--since", default=None, help="ISO date, API mode only")
    ap.add_argument("--out", default="news_videos.csv")
    ap.add_argument("--balance", type=int, default=None,
                    help="sample at most N videos per outlet (seeded)")
    args = ap.parse_args()

    mode = "API" if args.api else ("yt-dlp" if args.ytdlp else "RSS")
    print("Collecting via", mode)
    if args.api:
        rows = collect_api(args.per_channel, args.since)
    elif args.ytdlp:
        rows = collect_ytdlp(args.per_channel, args.workers)
    else:
        rows = collect_rss()

    df = pd.DataFrame(rows)
    df["url"] = "https://www.youtube.com/watch?v=" + df["video_id"]
    df = df[COLUMNS].drop_duplicates("video_id")
    df["published_at"] = pd.to_datetime(df["published_at"], format="ISO8601", utc=True)
    df = df.sort_values(["outlet", "published_at"]).reset_index(drop=True)

    # Exposure time: views accumulate, so a raw view count is not comparable
    # across videos of different ages.
    now = pd.Timestamp.now(tz="UTC")
    df["days_since_publication"] = (now - df["published_at"]).dt.total_seconds() / 86400
    df["days_since_publication"] = df["days_since_publication"].round(2)

    if args.balance:
        parts = [g.sample(min(len(g), args.balance), random_state=0)
                 for _, g in df.groupby("outlet")]
        df = (pd.concat(parts)
                .sort_values(["outlet", "published_at"])
                .reset_index(drop=True))

    df.to_csv(args.out, index=False,
              compression="gzip" if args.out.endswith(".gz") else None)
    import os as _os
    mb = _os.path.getsize(args.out) / 1048576
    print(f"\nwrote {args.out}: {len(df)} rows x {len(df.columns)} cols, {mb:.1f} MB")
    print(df.groupby("outlet").agg(
        videos=("video_id", "size"),
        median_views=("view_count", "median"),
        median_age_days=("days_since_publication", "median"),
        first=("published_at", "min"),
        last=("published_at", "max"),
    ).round(1).to_string())


if __name__ == "__main__":
    main()
