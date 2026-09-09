# Deploying Axia Research to axia-research.com

This site has no build step and no dependencies — `docs/` is the finished
site, ready to serve as-is. That makes GitHub Pages the simplest host: push
the code, flip one setting, point the domain, done. (It's named `docs/`
rather than `dist/` because GitHub Pages will only serve from the repo root
or a folder literally named `docs` — nothing else is selectable.)

## 1. Register the domain

Buy `axia-research.com` at a registrar. Recommended, since both sell at (or
close to) cost with no renewal markup:

- Cloudflare Registrar — https://www.cloudflare.com/products/registrar/ (~$10-11/yr)
- Porkbun — https://porkbun.com (~$10/yr)

Either is fine; Cloudflare is a slightly smoother fit if you ever want its
CDN/DNS in front of the site, but it's not required.

## 2. Create a GitHub repository

1. Create a free GitHub account if you don't have one: https://github.com/signup
2. Create a new repository, e.g. `axia-research` (public or private — GitHub
   Pages works either way on a personal account with Pages enabled).
3. From this project folder, push it:

```
cd axia-research
git init
git add .
git commit -m "Initial site"
git branch -M main
git remote add origin https://github.com/<your-username>/axia-research.git
git push -u origin main
```

## 3. Enable GitHub Pages

1. In the repo, go to **Settings → Pages**.
2. Under "Build and deployment", set **Source** to "Deploy from a branch".
3. Set **Branch** to `main` and the folder to `/docs`, then Save.
4. GitHub will give you a URL like `https://<your-username>.github.io/axia-research/`
   — confirm the site loads there first.

## 4. Point the domain at GitHub Pages

The `docs/CNAME` file already contains `axia-research.com`, which tells
GitHub Pages which custom domain to expect — you don't need to re-add it,
but you do need to point DNS at GitHub:

At your registrar's DNS settings for axia-research.com, add:

- Four **A** records for the root domain (`@`), pointing to GitHub Pages' IPs:
  - 185.199.108.153
  - 185.199.109.153
  - 185.199.110.153
  - 185.199.111.153
- One **CNAME** record for `www`, pointing to `<your-username>.github.io`

Back in **Settings → Pages** on GitHub, enter `axia-research.com` as the
custom domain and wait for DNS to verify (can take a few minutes to a few
hours). Once verified, check "Enforce HTTPS."

## 5. Publishing new posts going forward

```
# add or edit a .md file in content/
python3 build.py
git add .
git commit -m "New post: <title>"
git push
```

GitHub Pages redeploys automatically on push — usually live within a minute.

## Alternative: Netlify or Vercel

If you'd rather not deal with DNS A-records by hand, both Netlify and Vercel
let you drag-and-drop the `docs/` folder (or connect the GitHub repo) and
handle the custom domain through a simpler UI, including automatic HTTPS.
Either works fine for this site since there's no build command needed — set
the "publish directory" to `docs` and leave the build command blank.
