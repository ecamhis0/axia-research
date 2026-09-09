# Axia Research

A hand-built static site (pure HTML/CSS, no framework, no build dependencies)
for publishing investment theses, quick takes, and portfolio updates.

## Structure

- `content/theses/`, `content/quick-takes/`, `content/portfolio-updates/` —
  your posts, one markdown file each. Filename can start with `YYYY-MM-DD-`
  (recommended, for sorting) but the `date:` field in the front matter is
  what's actually used.
- `content/pages/about.md` — the About page.
- `assets/` — styles.css and favicon.svg, copied into the output as-is.
- `build.py` — the generator. Run `python3 build.py` any time you add or
  edit a post; it regenerates everything in `docs/`.
- `docs/` — the finished static site. This is what you deploy (named "docs"
  rather than "dist" because that's the folder name GitHub Pages requires).

## Adding a new post

Create a new file, e.g. `content/theses/2026-09-15-my-new-thesis.md`:

```
title: My New Thesis
date: 2026-09-15
summary: One or two sentences for the card preview and RSS feed.
---
Your post body goes here, in a small markdown subset:
**bold**, *italic*, `code`, [links](https://example.com),
## and ### headings, > blockquotes, and - bullet lists.
```

Then run:

```
python3 build.py
```

and redeploy `docs/` (see DEPLOY.md).

## Local preview

```
cd docs && python3 -m http.server 8000
```

then open http://localhost:8000
