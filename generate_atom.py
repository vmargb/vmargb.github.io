#!/usr/bin/env python3
"""
Reads blog.html, extracts every .post-row entry (date, title, tag, excerpt,
link), and writes out a valid atom.xml feed next to it

Usage: python3 generate_atom.py
"""

import re
import html
import uuid
from datetime import datetime, timezone

# -------------------------------------------------
BASE_URL = "https://vmargb.github.io"
SITE_TITLE = "vmargb@portfolio: ~/blog"
SITE_DESCRIPTION = "Writing about things I find interesting. Sometimes dev, sometimes not."
AUTHOR_NAME = "vmargb"
# -------------------------------------------------

SOURCE_HTML = "blog.html"
OUTPUT_XML = "atom.xml"

# matches: <div class="year-label">2026</div>
YEAR_RE = re.compile(r'<div class="year-label">\s*(\d{4})\s*</div>')

# matches one full .post-row <a>...</a> block
POST_RE = re.compile(
    r'<a href="([^"]+)" class="post-row">\s*'
    r'<span class="post-date">([^<]+)</span>\s*'
    r'<span class="post-title">([^<]+)</span>\s*'
    r'<span class="post-tag">([^<]+)</span>\s*'
    r'<span class="post-excerpt">([^<]+)</span>\s*'
    r'</a>',
    re.DOTALL,
)

def parse_posts(raw_html: str):
    """
    Walk the HTML top to bottom, tracking which year-group we're in,
    so "Jul 11" can be resolved to a full date like "Jul 11 2026".
    """
    tokens = []
    for m in YEAR_RE.finditer(raw_html):
        tokens.append(("year", m.start(), m.group(1)))
    for m in POST_RE.finditer(raw_html):
        tokens.append(("post", m.start(), m))
    tokens.sort(key=lambda t: t[1])

    posts = []
    current_year = None
    for kind, _, payload in tokens:
        if kind == "year":
            current_year = payload
        else:
            href, date_str, title, tag, excerpt = payload.groups()
            if current_year is None:
                continue  # skip anything before the first year label
            dt = datetime.strptime(f"{date_str.strip()} {current_year}", "%b %d %Y")
            dt = dt.replace(tzinfo=timezone.utc)
            posts.append({
                "href": href.strip(),
                "title": html.unescape(title.strip()),
                "tag": html.unescape(tag.strip()),
                "excerpt": html.unescape(excerpt.strip()),
                "date": dt,
            })
    # newest first
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def iso8601(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def stable_id(link: str) -> str:
    """Deterministic tag: URI so the same post always gets the same <id>."""
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, link)}"


def build_atom(posts):
    now = iso8601(datetime.now(timezone.utc))
    entries = []
    for p in posts:
        link = f"{BASE_URL}/{p['href'].lstrip('/')}"
        entries.append(f"""  <entry>
    <title>{escape_xml(p['title'])}</title>
    <link href="{escape_xml(link)}" />
    <id>{escape_xml(stable_id(link))}</id>
    <published>{iso8601(p['date'])}</published>
    <updated>{iso8601(p['date'])}</updated>
    <category term="{escape_xml(p['tag'])}" />
    <summary>{escape_xml(p['excerpt'])}</summary>
  </entry>""")

    entries_xml = "\n".join(entries)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{escape_xml(SITE_TITLE)}</title>
  <subtitle>{escape_xml(SITE_DESCRIPTION)}</subtitle>
  <link href="{escape_xml(BASE_URL)}/atom.xml" rel="self" />
  <link href="{escape_xml(BASE_URL)}/blog.html" />
  <id>{escape_xml(BASE_URL)}/</id>
  <updated>{now}</updated>
  <author><name>{escape_xml(AUTHOR_NAME)}</name></author>
{entries_xml}
</feed>
"""


def escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&apos;")
    )


def main():
    with open(SOURCE_HTML, "r", encoding="utf-8") as f:
        raw = f.read()

    posts = parse_posts(raw)
    if not posts:
        print("No posts found, check that blog.html matches the expected .post-row format.")
        return

    atom = build_atom(posts)
    with open(OUTPUT_XML, "w", encoding="utf-8") as f:
        f.write(atom)

    print(f"Wrote {OUTPUT_XML} with {len(posts)} posts.")


if __name__ == "__main__":
    main()
