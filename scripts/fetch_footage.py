#!/usr/bin/env python3
"""Download royalty-free clips for every row of a project's shotlist.csv.

Usage:
    python3 scripts/fetch_footage.py projects/<slug> [--per-term 2] [--source pexels,wikimedia]

Clips land in projects/<slug>/footage/<rank>/ and every download is logged in
projects/<slug>/credits.csv (source, author, license, page URL) for the video
description.

Pexels: the API key is injected by the environment's network proxy, so the
script sends a placeholder Authorization header.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "RankingWorkflow/1.0 (stock footage fetcher)"
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "proxy-injected")


def get_json(url, headers=None, retries=4):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == retries:
                raise
            time.sleep(5 * 2 ** attempt)  # rate limited: back off 5, 10, 20, 40 s


def download(url, dest):
    if os.path.exists(dest):
        return
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest + ".part", "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    os.replace(dest + ".part", dest)


def search_pexels(term, n):
    q = urllib.parse.urlencode({"query": term, "per_page": n, "size": "medium"})
    data = get_json(f"https://api.pexels.com/videos/search?{q}",
                    {"Authorization": PEXELS_KEY})
    out = []
    for v in data.get("videos", []):
        # pick the HD (<=1920 wide) mp4 with the largest width
        files = [f for f in v["video_files"]
                 if f.get("file_type") == "video/mp4" and (f.get("width") or 0) <= 1920]
        if not files:
            continue
        best = max(files, key=lambda f: f.get("width") or 0)
        out.append({
            "id": f"pexels-{v['id']}", "url": best["link"], "ext": "mp4",
            "author": v["user"]["name"], "license": "Pexels License",
            "page": v["url"], "duration": v.get("duration"),
        })
    return out


def search_wikimedia(term, n):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"{term} filetype:video", "gsrnamespace": 6, "gsrlimit": n,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime",
    })
    data = get_json(f"https://commons.wikimedia.org/w/api.php?{q}")
    out = []
    for p in (data.get("query", {}).get("pages", {}) or {}).values():
        ii = p["imageinfo"][0]
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "see page")
        author = re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", "unknown")).strip()
        out.append({
            "id": "wm-" + re.sub(r"[^\w.-]", "_", p["title"].removeprefix("File:"))[:80],
            "url": ii["url"], "ext": ii["url"].rsplit(".", 1)[-1],
            "author": author, "license": lic, "page": ii["descriptionurl"],
            "duration": None,
        })
    return out


SOURCES = {"pexels": search_pexels, "wikimedia": search_wikimedia}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--per-term", type=int, default=2)
    ap.add_argument("--source", default="pexels,wikimedia")
    ap.add_argument("--only", help="comma-separated ranks to fetch, e.g. 01,02")
    args = ap.parse_args()

    only = set(args.only.split(",")) if args.only else None
    credits_path = os.path.join(args.project, "credits.csv")
    seen = set()
    if os.path.exists(credits_path):
        with open(credits_path) as f:
            seen = {r["id"] for r in csv.DictReader(f)}
    new_file = not os.path.exists(credits_path)
    cf = open(credits_path, "a", newline="")
    cw = csv.DictWriter(cf, fieldnames=["rank", "id", "file", "source", "author", "license", "page"])
    if new_file:
        cw.writeheader()

    with open(os.path.join(args.project, "shotlist.csv")) as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if only and row["rank"] not in only:
            continue
        outdir = os.path.join(args.project, "footage", row["rank"])
        os.makedirs(outdir, exist_ok=True)
        for term in row["search_terms"].split("|"):
            for src in args.source.split(","):
                try:
                    hits = SOURCES[src](term, args.per_term)
                except Exception as e:  # keep going if one source fails
                    print(f"  ! {src} '{term}': {e}", file=sys.stderr)
                    continue
                for h in hits:
                    if h["id"] in seen:
                        continue
                    dest = os.path.join(outdir, f"{h['id']}.{h['ext']}")
                    try:
                        download(h["url"], dest)
                    except Exception as e:
                        print(f"  ! download {h['id']}: {e}", file=sys.stderr)
                        continue
                    seen.add(h["id"])
                    cw.writerow({"rank": row["rank"], "id": h["id"], "file": dest,
                                 "source": src, "author": h["author"],
                                 "license": h["license"], "page": h["page"]})
                    cf.flush()
                    print(f"[{row['rank']}] {src}: {os.path.basename(dest)}")
    cf.close()


if __name__ == "__main__":
    main()
