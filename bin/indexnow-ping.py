#!/usr/bin/env python3
"""Submit the built site's sitemap URLs to IndexNow (Bing / Yandex / DuckDuckGo / Seznam).

Run after the site is built (target/site/ present). Collects page URLs from the
per-component sitemaps (target/site/sitemap-*.xml, skipping the sitemap index) and
POSTs them to the IndexNow API with the site's key.

The IndexNow key is public by design (served at https://<host>/<key>.txt), so it's
fine to pass in plainly. Env:
  INDEXNOW_KEY   required — the key (also the basename of the key .txt at the site root)
  SITE_HOST      default www.alexmond.org

Never fails the deploy: any error is logged and the script exits 0. Google does not
use IndexNow — this only accelerates Bing/Yandex/DuckDuckGo discovery.
"""
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request

KEY = os.environ.get("INDEXNOW_KEY")
HOST = os.environ.get("SITE_HOST", "www.alexmond.org")
ENDPOINT = "https://api.indexnow.org/IndexNow"


def main() -> int:
    if not KEY:
        print("indexnow: INDEXNOW_KEY not set; skipping")
        return 0
    urls = set()
    for path in glob.glob("target/site/sitemap-*.xml"):
        with open(path, encoding="utf-8") as fh:
            urls.update(re.findall(r"<loc>([^<]+)</loc>", fh.read()))
    urls = sorted(urls)
    if not urls:
        print("indexnow: no sitemap URLs under target/site/; skipping")
        return 0
    payload = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": f"https://{HOST}/{KEY}.txt",
        "urlList": urls,
    }).encode()
    req = urllib.request.Request(
        ENDPOINT, data=payload, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        print(f"indexnow: submitted {len(urls)} URLs -> HTTP {resp.status} (200/202 = accepted)")
    except urllib.error.HTTPError as exc:
        # 4xx here is a submission problem, not a deploy problem — log and move on.
        print(f"indexnow: HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}")
    except Exception as exc:  # noqa: BLE001 - never break the deploy on a ping
        print(f"indexnow: submission error (ignored): {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
