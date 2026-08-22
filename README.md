# Chloe Crochets

A real small business site for my daughter's handmade crochet business.

This is being built in two phases, in two folders:

- **[`site/`](site/)** — a static marketing/reference site. **This is the
  Day 1 priority.** No backend, no build step — just HTML/CSS/JS that any
  static host (GitHub Pages, Netlify, etc.) can serve. Meant to look good,
  tell Chloe's story, show her work, list upcoming fairs, and give people a
  way to reach out. Chloe can also pull it up on a phone at her booth as a
  quick reference/portfolio.
- **[`shop/`](shop/)** — the e-commerce piece, added later. A CLI tool that
  syncs a simple YAML product list into Square's Catalog API, so the
  Square Online storefront and in-person/fair sales (Square POS) stay in
  sync automatically. See [`shop/README.md`](shop/README.md) for full
  setup instructions.

## Planned domain layout

| Subdomain | Purpose | Hosting |
|---|---|---|
| `chloescrochets.com` | The static site in `site/` | Any static host (GitHub Pages by default — see below) |
| `shop.chloescrochets.com` | The Square Online storefront | Square Online (custom domain, configured in Square's dashboard) |

Splitting it this way means the marketing site and the shop are
independent — the shop can go live later, on its own timeline, without
touching the main site, and each is hosted where it makes the most sense.

## Day 1: get the static site live

1. **Preview locally.** `site/` is plain static files — open
   `site/index.html` directly in a browser, or serve it locally:
   ```bash
   cd site && python3 -m http.server 8000
   ```
   then visit `http://localhost:8000`.
2. **Deploy for free with GitHub Pages** (already wired up):
   - In this repo's GitHub settings, go to **Settings → Pages** and set
     **Source** to **GitHub Actions** (one-time, manual — GitHub doesn't
     allow this to be set via a pushed file).
   - `.github/workflows/deploy-site.yml` publishes the contents of `site/`
     to GitHub Pages automatically whenever `site/**` changes on `main`.
   - After the first successful deploy, GitHub gives you a
     `https://<username>.github.io/<repo>/` URL.
3. **Point the real domain at it.** Once `chloescrochets.com` is
   purchased:
   - In your domain registrar's DNS settings, follow GitHub's
     [custom domain instructions](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)
     (an `A`/`ALIAS` record for the apex domain to GitHub Pages' IPs, or a
     `CNAME` if you're pointing a subdomain like `www`).
   - Add a `CNAME` file inside `site/` containing just `chloescrochets.com`
     so GitHub Pages knows to serve that domain (also set it in the repo's
     Pages settings UI).
   - Enable "Enforce HTTPS" in Pages settings once the DNS change
     propagates.
4. **Edit content as you go** — everything in `site/index.html` is plain
   HTML with comments marking what to swap in (photos, the fair schedule,
   social links, contact email). No rebuild step; just edit and
   push/redeploy.

## Day 2+: bring the shop online

When you're ready to sell between fairs:

1. Open and verify the Square merchant account under the LLC (bank
   linking, identity verification) — done manually in Square's dashboard,
   not automated by anything here.
2. Subscribe to Square Online Plus and set its custom domain to
   `shop.chloescrochets.com` (Square walks you through the DNS record to
   add).
3. Use [`shop/`](shop/) to push products (name, price, sizes, colors,
   lead time) into Square's Catalog from a simple YAML file — see
   [`shop/README.md`](shop/README.md).

## Repo layout

```
site/                   Static marketing/reference site (Day 1)
  index.html
  assets/css/style.css
  assets/js/main.js
  assets/img/
shop/                   Square catalog sync tool (Day 2+)
  products.yaml
  sync_catalog.py
  tests/
  README.md
.github/workflows/
  deploy-site.yml       Auto-deploys site/ to GitHub Pages on push to main
```
