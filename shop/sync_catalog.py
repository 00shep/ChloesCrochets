#!/usr/bin/env python3
"""
sync_catalog.py — Sync a YAML product spec into Square's Catalog API.

For each product in the spec, creates/updates:
  - one CatalogItem
  - one CatalogItemOption per option group (e.g. Size, Color)
  - one CatalogItemOptionValue per value in each group
  - one CatalogItemVariation per combination of option values, each
    individually priced (base_price + the sum of that combo's price_deltas)

Re-running with an edited spec updates the existing catalog objects in
place instead of creating duplicates: real Square object IDs are cached in
a local JSON file (default: .catalog_ids.json next to the spec) and reused
on the next run.

This script only manages catalog/product data via Square's Catalog API.
No payment or card data is ever handled here — checkout and payment
processing happen entirely on Square's side (Square Online / Square POS).

Usage:
    python sync_catalog.py products.yaml --env sandbox
    python sync_catalog.py products.yaml --env production
    python sync_catalog.py products.yaml --env sandbox --dry-run

Environment:
    SQUARE_ACCESS_TOKEN   Square Personal Access Token (sandbox or
                           production, matching --env). Not required with
                           --dry-run.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import uuid
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import requests
import yaml

SQUARE_VERSION = "2024-08-21"
BASE_URLS = {
    "sandbox": "https://connect.squareupsandbox.com",
    "production": "https://connect.squareup.com",
}


def dollars_to_cents(amount: Any) -> int:
    cents = (Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def new_temp_id(prefix: str) -> str:
    return f"#{prefix}-{uuid.uuid4().hex[:12]}"


def load_spec(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text()) or []
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a YAML list of products at the top level")
    names = [p.get("name") for p in data]
    if len(names) != len(set(names)):
        raise ValueError(f"{path}: product names must be unique (used to match existing Square items)")
    for product in data:
        if "name" not in product or "base_price" not in product:
            raise ValueError(f"{path}: every product needs at least 'name' and 'base_price': {product}")
    return data


def load_id_map(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_id_map(path: Path, id_map: dict) -> None:
    path.write_text(json.dumps(id_map, indent=2, sort_keys=True) + "\n")


def build_description(product: dict) -> str:
    description = (product.get("description") or "").strip()
    lead_time = (product.get("lead_time") or "").strip()
    if not lead_time:
        return description
    return f"{description}\n\n{lead_time}".strip() if description else lead_time


def variation_name(combo: list[tuple[str, str]]) -> str:
    if not combo:
        return "Regular"
    return ", ".join(value for _opt, value in combo)


def build_objects_for_product(product: dict, existing: dict) -> tuple[list[dict], dict]:
    """
    Build the Square CatalogObjects (ITEM_OPTION[s], ITEM with nested
    ITEM_VARIATIONs) for one product, reusing real Square object IDs from
    `existing` wherever we have them so the upsert updates in place.

    Returns (objects, id_plan). `id_plan` mirrors the shape stored in
    .catalog_ids.json, using temp IDs (prefixed "#") for anything that
    doesn't already have a real Square ID yet.
    """
    name = product["name"]
    base_price = product["base_price"]
    options: dict = product.get("options") or {}

    existing = existing or {}
    existing_options = existing.get("option_ids", {})
    existing_values = existing.get("option_value_ids", {})
    existing_variations = existing.get("variation_ids", {})

    item_id = existing.get("item_id") or new_temp_id("item")
    id_plan: dict = {
        "item_id": item_id,
        "option_ids": {},
        "option_value_ids": {},
        "variation_ids": {},
    }

    objects: list[dict] = []
    item_options_for_item = []
    combo_axes: list[list[tuple[str, str, Decimal]]] = []

    for opt_name, values in options.items():
        opt_id = existing_options.get(opt_name) or new_temp_id("opt")
        id_plan["option_ids"][opt_name] = opt_id
        id_plan["option_value_ids"].setdefault(opt_name, {})

        value_objects = []
        axis = []
        for val in values:
            val_name = val["name"]
            delta = Decimal(str(val.get("price_delta", 0)))
            val_id = existing_values.get(opt_name, {}).get(val_name) or new_temp_id("optval")
            id_plan["option_value_ids"][opt_name][val_name] = val_id
            value_objects.append(
                {
                    "type": "ITEM_OPTION_VAL",
                    "id": val_id,
                    "item_option_value_data": {
                        "item_option_id": opt_id,
                        "name": val_name,
                    },
                }
            )
            axis.append((opt_name, val_name, delta))
        combo_axes.append(axis)

        objects.append(
            {
                "type": "ITEM_OPTION",
                "id": opt_id,
                "item_option_data": {
                    "name": opt_name.title(),
                    "display_name": opt_name.title(),
                    "values": value_objects,
                },
            }
        )
        item_options_for_item.append({"item_option_id": opt_id})

    variations = []
    for combo in itertools.product(*combo_axes):
        opt_value_pairs = [(opt_name, val_name) for opt_name, val_name, _delta in combo]
        total_delta = sum((delta for _o, _v, delta in combo), Decimal("0"))
        price = Decimal(str(base_price)) + total_delta

        combo_key = "|".join(f"{o}={v}" for o, v in opt_value_pairs) or "_default"
        var_id = existing_variations.get(combo_key) or new_temp_id("var")
        id_plan["variation_ids"][combo_key] = var_id

        variation_data = {
            "item_id": item_id,
            "name": variation_name(opt_value_pairs),
            "pricing_type": "FIXED_PRICING",
            "price_money": {
                "amount": dollars_to_cents(price),
                "currency": "USD",
            },
        }
        if opt_value_pairs:
            variation_data["item_option_values"] = [
                {
                    "item_option_id": id_plan["option_ids"][opt_name],
                    "item_option_value_id": id_plan["option_value_ids"][opt_name][val_name],
                }
                for opt_name, val_name in opt_value_pairs
            ]

        variations.append(
            {
                "type": "ITEM_VARIATION",
                "id": var_id,
                "item_variation_data": variation_data,
            }
        )

    item_data = {
        "name": name,
        "description": build_description(product),
        "variations": variations,
    }
    if item_options_for_item:
        item_data["item_options"] = item_options_for_item

    objects.append(
        {
            "type": "ITEM",
            "id": item_id,
            "item_data": item_data,
        }
    )

    return objects, id_plan


def build_batch_request(products: list[dict], id_map: dict) -> tuple[dict, dict]:
    all_objects: list[dict] = []
    id_plans: dict = {}
    for product in products:
        name = product["name"]
        objects, id_plan = build_objects_for_product(product, id_map.get(name, {}))
        all_objects.extend(objects)
        id_plans[name] = id_plan

    request_body = {
        "idempotency_key": uuid.uuid4().hex,
        "batches": [{"objects": all_objects}],
    }
    return request_body, id_plans


def resolve_id_plan(id_plan: dict, temp_to_real: dict) -> dict:
    def resolve(value: str) -> str:
        return temp_to_real.get(value, value)

    return {
        "item_id": resolve(id_plan["item_id"]),
        "option_ids": {opt: resolve(oid) for opt, oid in id_plan["option_ids"].items()},
        "option_value_ids": {
            opt: {val: resolve(vid) for val, vid in vals.items()}
            for opt, vals in id_plan["option_value_ids"].items()
        },
        "variation_ids": {combo: resolve(vid) for combo, vid in id_plan["variation_ids"].items()},
    }


def call_batch_upsert(base_url: str, token: str, request_body: dict) -> dict:
    response = requests.post(
        f"{base_url}/v2/catalog/batch-upsert",
        headers={
            "Authorization": f"Bearer {token}",
            "Square-Version": SQUARE_VERSION,
            "Content-Type": "application/json",
        },
        json=request_body,
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Square API error {response.status_code}: {response.text}")
    data = response.json()
    if data.get("errors"):
        raise RuntimeError(f"Square API returned errors:\n{json.dumps(data['errors'], indent=2)}")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync a YAML product spec into Square Catalog.")
    parser.add_argument("spec", type=Path, help="Path to the product YAML spec (e.g. products.yaml)")
    parser.add_argument("--env", choices=["sandbox", "production"], required=True)
    parser.add_argument(
        "--ids-file",
        type=Path,
        default=None,
        help="Path to the local ID-tracking file (default: .catalog_ids.json next to the spec)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the Square API request without calling the API or requiring a token",
    )
    args = parser.parse_args(argv)

    spec_path: Path = args.spec
    if not spec_path.exists():
        print(f"error: spec file not found: {spec_path}", file=sys.stderr)
        return 1

    ids_path: Path = args.ids_file or spec_path.parent / ".catalog_ids.json"

    try:
        products = load_spec(spec_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    id_map = load_id_map(ids_path)
    request_body, id_plans = build_batch_request(products, id_map)
    object_count = len(request_body["batches"][0]["objects"])
    print(f"Prepared {len(products)} product(s), {object_count} catalog object(s).")

    if args.dry_run:
        print(json.dumps(request_body, indent=2))
        print("\n--dry-run: not calling the Square API.")
        return 0

    token = os.environ.get("SQUARE_ACCESS_TOKEN")
    if not token:
        print(
            "error: SQUARE_ACCESS_TOKEN is not set. Export it, or use --dry-run to build "
            "the request without calling Square.",
            file=sys.stderr,
        )
        return 1

    base_url = BASE_URLS[args.env]
    try:
        response = call_batch_upsert(base_url, token, request_body)
    except (RuntimeError, requests.RequestException) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    temp_to_real = {m["client_object_id"]: m["object_id"] for m in response.get("id_mappings", [])}
    for name, id_plan in id_plans.items():
        id_map[name] = resolve_id_plan(id_plan, temp_to_real)

    save_id_map(ids_path, id_map)
    print(f"Synced {len(products)} product(s) to Square ({args.env}). IDs saved to {ids_path}.")
    print("Commit the updated ID file so future runs (from any machine) stay idempotent:")
    print(f"  git add {ids_path.name} && git commit -m 'Update catalog IDs'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
