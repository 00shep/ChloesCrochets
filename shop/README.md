# Chloe Crochets — Shop Catalog Sync

A small CLI tool that syncs a YAML product spec into Square's Catalog, so
the online shop (Square Online, running at `shop.chloescrochets.com`) and
in-person/fair sales (Square POS) always show the same products, prices,
and inventory.

This tool only manages **catalog/product data** — names, prices, sizes,
colors. It never touches card numbers or payment data; Square handles all
of that on its own hosted checkout and POS.

Not live yet — see the root [README.md](../README.md) for where this fits
in the overall project plan (static site first, shop second).

## 1. Get a Square Access Token

1. Go to the [Square Developer Dashboard](https://developer.squareup.com/apps)
   and sign in with the account that will own the LLC's Square business
   account.
2. Create an application (e.g. "Chloe Crochets Catalog Sync").
3. Every app has two token sets:
   - **Sandbox** — a free, fake test account. Use this first. Under
     "Sandbox" in the app dashboard, copy the **Sandbox Access Token**.
   - **Production** — your real Square business account. Under
     "Production", copy the **Production Access Token**. Only use this
     once you've verified everything works correctly in sandbox.
4. Treat both tokens like passwords — never commit them to git.

## 2. Install

```bash
cd shop
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Set your token

```bash
export SQUARE_ACCESS_TOKEN="paste-your-sandbox-token-here"
```

(Or copy `.env.example` to `.env`, fill it in, and `set -a; source .env; set +a`
before running the script. `.env` is gitignored so it won't get committed.)

## 4. Run it

Preview the request without needing a token or touching Square at all:

```bash
python sync_catalog.py products.yaml --env sandbox --dry-run
```

Actually sync to your Square **sandbox** (safe to experiment with):

```bash
python sync_catalog.py products.yaml --env sandbox
```

Once it looks right in the sandbox and you're ready for real customers,
sync to **production** (make sure `SQUARE_ACCESS_TOKEN` is your
*production* token first):

```bash
python sync_catalog.py products.yaml --env production
```

## 5. Add or change a product

Edit `products.yaml` — no code changes needed. Example:

```yaml
- name: "Custom Crochet - Kirby Style"
  base_price: 25.00
  lead_time: "Made to order, ships in 2-3 weeks"
  description: "A soft, handmade crochet Kirby, made to order just for you."
  options:
    size:
      - {name: Small, price_delta: 0}
      - {name: Medium, price_delta: 5}
      - {name: Large, price_delta: 10}
    color:
      - {name: Blue}
      - {name: Red}
      - {name: Green}
```

- `options` is optional — omit it entirely for a simple, single-price item.
- Every combination of option values (e.g. Small+Blue, Small+Red, ...)
  becomes its own priced variation, priced at `base_price` + the sum of
  that combination's `price_delta`s.
- `lead_time` has no dedicated field in Square, so it's appended to the
  item's description automatically.

Then re-run the sync command from step 4. **Product names must stay
unique** in the file — that's how the script matches an edited product back
to the existing Square item instead of creating a duplicate.

## 6. Keep re-runs idempotent

The first successful (non `--dry-run`) sync writes real Square object IDs
to `.catalog_ids.json`, next to `products.yaml`. Re-running the script
reads that file and updates the same Square objects in place instead of
creating duplicates.

**Commit `.catalog_ids.json` after every real sync** (it's tracked in git,
not ignored) so the mapping survives across machines/clones — otherwise a
sync from a fresh checkout would think every product is new and duplicate
your whole catalog. The script prints a reminder after each successful run.

## 7. Run the tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests cover YAML parsing/validation and the exact JSON payload the script
builds for Square's `BatchUpsertCatalogObjects` endpoint (with the network
call mocked), so you can verify changes without needing a live token.

## What this tool does NOT do (on purpose)

- **Open or verify the Square merchant account** — linking a bank account,
  identity verification (KYC), and agreeing to Square's terms all happen
  manually in the [Square Dashboard](https://squareup.com/dashboard). This
  can't be automated and isn't something this script touches.
- **Set up Square Online itself** — the storefront (theme, custom domain,
  About page, etc.) is configured in Square Online's own dashboard. This
  script only pushes catalog data into it.
- **Handle payments or card data** — Square's hosted checkout and POS
  handle 100% of that; this script only ever sends product names, prices,
  and descriptions to Square's Catalog API.
