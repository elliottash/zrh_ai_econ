# Problem set — Text and Image as Data

Week 1 assignment for Andrea's two Monday sessions.

| File | What it is |
|---|---|
| `problem_set.pdf` | the assignment |
| `news_videos.csv.gz` | the dataset, 23,689 rows (gzipped, 4.8 MB) |
| `build_dataset.py` | rebuilds or extends the dataset |

## The dataset

23,689 YouTube videos from **Fox News** (11,540) and **MSNBC** (12,149),
covering **January to August 2026**. One row per video, 13 columns.
Gzipped; `pd.read_csv` decompresses transparently.

| Column | Notes |
|---|---|
| `video_id`, `url` | identifier and link |
| `outlet`, `channel_id` | Fox News or MSNBC |
| `title`, `description` | the text |
| `published_at` | UTC timestamp |
| `thumbnail_url` | the image, fetched live from `i.ytimg.com` |
| `view_count`, `like_count`, `comment_count` | engagement |
| `duration_seconds` | video length |
| `days_since_publication` | exposure time, as of collection |

Complete apart from 12 missing `comment_count` (comments disabled). No
duplicate video ids. Both outlets post 1,350–1,700 videos a month, so the
panel is near-balanced in every month, giving eight months of within-outlet
variation as well as the cross-section.

Two design choices worth knowing:

**The NYT was dropped.** It posts about two videos a day against ~50 for the
two cable outlets, so any common time window left it an order of magnitude
smaller. Its channel id is still in `build_dataset.py` if you want it back.

**No forced balancing.** The two outlets happen to post at similar rates, so
the 5% gap in counts is real rather than a sampling artefact. Views accumulate,
so engagement comparisons need `days_since_publication` as a control; the
problem set says so.

## Rebuilding

Needs a free YouTube Data API v3 key from
[console.cloud.google.com](https://console.cloud.google.com/apis/credentials)
with the API enabled. No billing account. The daily quota is 10,000 units and
this whole dataset costs about 200.

```bash
YOUTUBE_API_KEY=... python3 build_dataset.py --api \
    --per-channel 30000 --since 2026-01-01 --out news_videos.csv.gz
```

That is how this file was built; it costs about 1,000 of the 10,000 daily
units and takes a few minutes. Writing to a `.gz` path compresses
automatically. Other flags: `--balance N` to sample N per outlet, and no flags
at all for a 15-video RSS pull that needs no key. There is also a `--ytdlp` mode that needs no key,
but YouTube bot-challenges it after a few dozen requests from one IP, so do not
plan around it.

## Analysis cautions

23,689 thumbnails is more than a free Colab session will embed comfortably.
Subsample to a few thousand, get the pipeline working, and scale up only if
needed.

Both outlets brand their thumbnails: logos, chyrons, recurring studio sets.
A near-perfect outlet classifier may have learned to find a logo rather than
political style. Inspect the images driving predictions and test whether the
result survives cropping or masking branded regions.
