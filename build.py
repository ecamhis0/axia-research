#!/usr/bin/env python3
"""
Axia Research — static site generator.

Pure Python standard library, no external dependencies (npm/pip are not
reachable from this environment, and none are needed: the output is plain
static HTML/CSS that any static host — GitHub Pages, Netlify, Vercel —
can serve with zero build step).

Usage:
    python3 build.py

Reads content/<section>/*.md (simple front matter + a small markdown
subset) and content/pages/*.md, writes a full static site into docs/
(named "docs" rather than "dist" because that's one of the two folder
names GitHub Pages is willing to serve from).
To add a new post, drop a new .md file into the right content/ folder
and re-run this script.
"""
import os
import re
import shutil
import html as htmllib
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
DIST = os.path.join(ROOT, "docs")
ASSETS = os.path.join(ROOT, "assets")

SITE = {
    "name": "Axia Research",
    "tagline": "Notes on value, dislocation, and mean reversion",
    "domain": "https://axia-research.com",
    "author": "Eric Camhis",
    "description": (
        "Axia Research is a running record of investment theses, quick "
        "reactions to market moves, and portfolio updates — written in "
        "public, in real time."
    ),
}

SECTIONS = [
    {
        "slug": "theses",
        "label": "Theses",
        "singular": "Thesis",
        "description": "Long-form investment cases: the setup, the variant view, and the margin of safety.",
    },
    {
        "slug": "quick-takes",
        "label": "Quick Takes",
        "singular": "Quick Take",
        "description": "Short, timely reactions to earnings, news, and market moves.",
    },
    {
        "slug": "portfolio-updates",
        "label": "Portfolio Updates",
        "singular": "Portfolio Update",
        "description": "Position changes, sizing, and how the portfolio is evolving over time.",
    },
]
SECTION_BY_SLUG = {s["slug"]: s for s in SECTIONS}


# ---------------------------------------------------------------------------
# Tiny markdown-lite parser: paragraphs, #/##/### headings, > blockquotes,
# - bullet lists, **bold**, *italic*, `code`, [text](url), horizontal rules.
# ---------------------------------------------------------------------------

def inline(text):
    text = htmllib.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def md_table(block):
    """Render a GitHub-style pipe table: header row, |---|---| rule, data rows."""
    lines = [l for l in block.split("\n") if l.strip()]

    def split_row(line):
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [c.strip() for c in line.split("|")]

    header = split_row(lines[0])
    aligns = []
    for a in split_row(lines[1]):
        if a.startswith(":") and a.endswith(":"):
            aligns.append("center")
        elif a.endswith(":"):
            aligns.append("right")
        elif a.startswith(":"):
            aligns.append("left")
        else:
            aligns.append(None)

    def style(i):
        al = aligns[i] if i < len(aligns) else None
        return f' style="text-align:{al}"' if al else ""

    thead = "<tr>" + "".join(f"<th{style(i)}>{inline(c)}</th>" for i, c in enumerate(header)) + "</tr>"
    body_rows = []
    for line in lines[2:]:
        cells = split_row(line)
        body_rows.append("<tr>" + "".join(f"<td{style(i)}>{inline(c)}</td>" for i, c in enumerate(cells)) + "</tr>")
    return f'<div class="table-wrap"><table><thead>{thead}</thead><tbody>{"".join(body_rows)}</tbody></table></div>'


IMG_BLOCK_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
TABLE_RULE_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$")


def md_to_html(body):
    blocks = re.split(r"\n\s*\n", body.strip())
    out = []
    for block in blocks:
        block = block.strip("\n")
        if not block.strip():
            continue
        lines0 = block.split("\n")
        img_match = IMG_BLOCK_RE.match(lines0[0].strip())
        if block.strip() == "---":
            out.append("<hr>")
        elif block.startswith("### "):
            out.append(f"<h3>{inline(block[4:].strip())}</h3>")
        elif block.startswith("## "):
            out.append(f"<h2>{inline(block[3:].strip())}</h2>")
        elif block.startswith("> "):
            lines = [l[2:] if l.startswith("> ") else l for l in block.split("\n")]
            out.append(f"<blockquote><p>{inline(' '.join(lines))}</p></blockquote>")
        elif block.lstrip().startswith("- "):
            items = []
            for line in block.split("\n"):
                stripped = line.strip()
                if stripped.startswith("- "):
                    items.append(stripped[2:])
                elif stripped and items:
                    items[-1] += " " + stripped
            lis = "\n".join(f"  <li>{inline(i)}</li>" for i in items)
            out.append(f"<ul>\n{lis}\n</ul>")
        elif img_match:
            alt, srcpath = img_match.group(1), img_match.group(2)
            caption = " ".join(l.strip() for l in lines0[1:] if l.strip())
            fig = f'<figure class="post-figure"><img src="{htmllib.escape(srcpath)}" alt="{htmllib.escape(alt)}" loading="lazy">'
            if caption:
                fig += f"<figcaption>{inline(caption)}</figcaption>"
            fig += "</figure>"
            out.append(fig)
        elif block.lstrip().startswith("|") and len(lines0) >= 2 and TABLE_RULE_RE.match(lines0[1].strip()):
            out.append(md_table(block))
        else:
            paragraph = " ".join(l.strip() for l in block.split("\n"))
            out.append(f"<p>{inline(paragraph)}</p>")
    return "\n".join(out)


def parse_front_matter(text):
    m = re.match(r"^-{0,3}\s*\n?(.*?)\n-{3,}\n(.*)$", text, re.S) if text.startswith("---") else None
    if not m:
        # simple "key: value" lines until a line of just "---"
        parts = text.split("\n---\n", 1)
        if len(parts) != 2:
            raise ValueError("Missing front matter separator '---'")
        head, body = parts
    else:
        head, body = m.group(1), m.group(2)
    meta = {}
    for line in head.strip().split("\n"):
        if not line.strip() or ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta, body


def load_posts(section_slug):
    folder = os.path.join(CONTENT, section_slug)
    posts = []
    if not os.path.isdir(folder):
        return posts
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(folder, fname)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        meta, body = parse_front_matter(raw)
        slug = fname[:-3]
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)
        date_str = meta.get("date", "1970-01-01")
        posts.append({
            "title": meta.get("title", slug),
            "summary": meta.get("summary", ""),
            "date": date_str,
            "date_obj": datetime.strptime(date_str, "%Y-%m-%d"),
            "slug": slug,
            "section": section_slug,
            "body_html": md_to_html(body),
        })
    posts.sort(key=lambda p: p["date_obj"], reverse=True)
    return posts


def fmt_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")


# ---------------------------------------------------------------------------
# HTML shell
# ---------------------------------------------------------------------------

NAV_ITEMS = [("/", "Home")] + [(f"/{s['slug']}/", s["label"]) for s in SECTIONS] + [("/about/", "About")]


def base(title, description, content_html, path="/", og_type="website"):
    canonical = SITE["domain"] + path
    nav_html = "\n".join(
        f'<a href="{href}" class="nav-link{" nav-active" if href == path else ""}">{label}</a>'
        for href, label in NAV_ITEMS
    )
    full_title = title if title == SITE["name"] else f"{title} — {SITE['name']}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{htmllib.escape(full_title)}</title>
<meta name="description" content="{htmllib.escape(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{htmllib.escape(full_title)}">
<meta property="og:description" content="{htmllib.escape(description)}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary">
<link rel="alternate" type="application/rss+xml" title="{SITE['name']}" href="/rss.xml">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/styles.css">
</head>
<body>
<div class="skip"><a href="#main">Skip to content</a></div>
<header class="site-header">
  <div class="wrap header-row">
    <a href="/" class="brand">
      <span class="brand-mark" aria-hidden="true">A</span>
      <span class="brand-text">{SITE['name']}</span>
    </a>
    <nav class="site-nav" aria-label="Primary">
      {nav_html}
    </nav>
  </div>
</header>
<main id="main">
{content_html}
</main>
<footer class="site-footer">
  <div class="wrap footer-row">
    <p>&copy; {datetime.now().year} {SITE['author']}. Published on {SITE['name']}.</p>
    <p class="footer-meta"><a href="/rss.xml">RSS</a> &middot; Not investment advice — personal opinions only.</p>
  </div>
</footer>
</body>
</html>
"""


def post_card(post):
    section = SECTION_BY_SLUG[post["section"]]
    href = f"/{post['section']}/{post['slug']}/"
    return f"""<article class="card">
  <a href="{href}" class="card-link">
    <p class="card-meta"><span class="tag tag-{post['section']}">{section['label']}</span> <time datetime="{post['date']}">{fmt_date(post['date'])}</time></p>
    <h3 class="card-title">{htmllib.escape(post['title'])}</h3>
    <p class="card-summary">{htmllib.escape(post['summary'])}</p>
  </a>
</article>"""


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def write(path, html_str):
    full = os.path.join(DIST, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(html_str)


def build_home(all_posts):
    latest = all_posts[:6]
    cards = "\n".join(post_card(p) for p in latest)
    intro = f"""
<section class="hero">
  <div class="wrap">
    <h1 class="hero-title">{SITE['name']}</h1>
    <p class="hero-tagline">{SITE['tagline']}</p>
    <p class="hero-body">{SITE['description']}</p>
  </div>
</section>
<section class="wrap">
  <h2 class="section-heading">Latest</h2>
  <div class="card-grid">
    {cards}
  </div>
</section>
"""
    write("/index.html", base(SITE["name"], SITE["description"], intro, path="/"))


def build_section(section, posts):
    cards = "\n".join(post_card(p) for p in posts) if posts else "<p class='empty'>No posts yet.</p>"
    content = f"""
<section class="wrap section-page">
  <p class="eyebrow">{section['label']}</p>
  <h1 class="page-title">{section['label']}</h1>
  <p class="page-lede">{section['description']}</p>
  <div class="card-grid">
    {cards}
  </div>
</section>
"""
    write(f"/{section['slug']}/index.html", base(section["label"], section["description"], content, path=f"/{section['slug']}/"))


def build_post(post):
    section = SECTION_BY_SLUG[post["section"]]
    path = f"/{post['section']}/{post['slug']}/"
    content = f"""
<article class="wrap post">
  <p class="eyebrow"><a href="/{section['slug']}/">{section['label']}</a></p>
  <h1 class="post-title">{htmllib.escape(post['title'])}</h1>
  <p class="post-meta"><time datetime="{post['date']}">{fmt_date(post['date'])}</time> &middot; {SITE['author']}</p>
  <div class="post-body">
    {post['body_html']}
  </div>
  <p class="post-back"><a href="/{section['slug']}/">&larr; Back to {section['label']}</a></p>
</article>
"""
    write(path + "index.html", base(post["title"], post["summary"] or SITE["description"], content, path=path, og_type="article"))


def build_about():
    src = os.path.join(CONTENT, "pages", "about.md")
    with open(src, encoding="utf-8") as f:
        meta, body = parse_front_matter(f.read())
    content = f"""
<article class="wrap post about-page">
  <h1 class="post-title">{htmllib.escape(meta.get('title', 'About'))}</h1>
  <div class="post-body">
    {md_to_html(body)}
  </div>
</article>
"""
    write("/about/index.html", base("About", meta.get("summary", SITE["description"]), content, path="/about/"))


def build_404():
    content = """
<section class="wrap post">
  <h1 class="post-title">Page not found</h1>
  <p>The page you're looking for doesn't exist.</p>
  <p><a href="/">&larr; Back home</a></p>
</section>
"""
    write("/404.html", base("Not found", "Page not found", content, path="/404.html"))


def build_rss(all_posts):
    items = []
    for p in all_posts[:20]:
        link = f"{SITE['domain']}/{p['section']}/{p['slug']}/"
        pub = p["date_obj"].strftime("%a, %d %b %Y 00:00:00 +0000")
        items.append(f"""  <item>
    <title>{htmllib.escape(p['title'])}</title>
    <link>{link}</link>
    <guid>{link}</guid>
    <pubDate>{pub}</pubDate>
    <description>{htmllib.escape(p['summary'])}</description>
  </item>""")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{SITE['name']}</title>
  <link>{SITE['domain']}</link>
  <description>{htmllib.escape(SITE['description'])}</description>
{chr(10).join(items)}
</channel>
</rss>
"""
    write("/rss.xml", rss)


def build_sitemap(all_posts):
    urls = ["/", "/about/"] + [f"/{s['slug']}/" for s in SECTIONS]
    urls += [f"/{p['section']}/{p['slug']}/" for p in all_posts]
    body = "\n".join(f"  <url><loc>{SITE['domain']}{u}</loc></url>" for u in urls)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
"""
    write("/sitemap.xml", xml)


def copy_static():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    shutil.copytree(ASSETS, DIST)
    with open(os.path.join(DIST, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE['domain']}/sitemap.xml\n")
    with open(os.path.join(DIST, "CNAME"), "w") as f:
        f.write("axia-research.com\n")


def main():
    copy_static()
    all_posts = []
    for section in SECTIONS:
        posts = load_posts(section["slug"])
        all_posts.extend(posts)
        build_section(section, posts)
        for p in posts:
            build_post(p)
    all_posts.sort(key=lambda p: p["date_obj"], reverse=True)
    build_home(all_posts)
    build_about()
    build_404()
    build_rss(all_posts)
    build_sitemap(all_posts)
    print(f"Built {len(all_posts)} posts into {DIST}")


if __name__ == "__main__":
    main()
