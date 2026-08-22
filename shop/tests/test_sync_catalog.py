import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sync_catalog as sc

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_spec_parses_example_products():
    products = sc.load_spec(REPO_ROOT / "products.yaml")
    assert len(products) == 3
    assert products[0]["name"] == "Custom Crochet - Kirby Style"
    assert products[0]["options"]["size"][2] == {"name": "Large", "price_delta": 10}


def test_load_spec_rejects_duplicate_names(tmp_path):
    spec = tmp_path / "bad.yaml"
    spec.write_text("- name: A\n  base_price: 1\n- name: A\n  base_price: 2\n")
    with pytest.raises(ValueError, match="unique"):
        sc.load_spec(spec)


def test_load_spec_requires_name_and_base_price(tmp_path):
    spec = tmp_path / "bad.yaml"
    spec.write_text("- name: A\n")
    with pytest.raises(ValueError, match="base_price"):
        sc.load_spec(spec)


def test_dollars_to_cents():
    assert sc.dollars_to_cents(25) == 2500
    assert sc.dollars_to_cents(25.5) == 2550
    assert sc.dollars_to_cents("9.999") == 1000


def test_build_description_appends_lead_time():
    assert (
        sc.build_description({"description": "Cute thing.", "lead_time": "Ships in 2 weeks"})
        == "Cute thing.\n\nShips in 2 weeks"
    )
    assert sc.build_description({"lead_time": "Ships in 2 weeks"}) == "Ships in 2 weeks"
    assert sc.build_description({"description": "Cute thing."}) == "Cute thing."
    assert sc.build_description({}) == ""


def test_build_objects_for_product_creates_all_variation_combos():
    product = {
        "name": "Kirby",
        "base_price": 25.0,
        "options": {
            "size": [
                {"name": "Small", "price_delta": 0},
                {"name": "Large", "price_delta": 10},
            ],
            "color": [
                {"name": "Blue"},
                {"name": "Red"},
            ],
        },
    }
    objects, id_plan = sc.build_objects_for_product(product, existing={})

    item_options = [o for o in objects if o["type"] == "ITEM_OPTION"]
    items = [o for o in objects if o["type"] == "ITEM"]
    assert len(item_options) == 2
    assert len(items) == 1

    item = items[0]
    variations = item["item_data"]["variations"]
    assert len(variations) == 4  # 2 sizes x 2 colors

    prices = sorted(v["item_variation_data"]["price_money"]["amount"] for v in variations)
    assert prices == [2500, 2500, 3500, 3500]

    for variation in variations:
        vd = variation["item_variation_data"]
        assert vd["item_id"] == item["id"]
        assert vd["pricing_type"] == "FIXED_PRICING"
        assert len(vd["item_option_values"]) == 2
        for pair in vd["item_option_values"]:
            assert "item_option_id" in pair and "item_option_value_id" in pair

    assert len(id_plan["variation_ids"]) == 4


def test_build_objects_for_product_no_options_creates_single_variation():
    product = {"name": "Bouquet", "base_price": 15.0}
    objects, _id_plan = sc.build_objects_for_product(product, existing={})
    item = next(o for o in objects if o["type"] == "ITEM")
    variations = item["item_data"]["variations"]
    assert len(variations) == 1
    assert variations[0]["item_variation_data"]["price_money"]["amount"] == 1500
    assert "item_option_values" not in variations[0]["item_variation_data"]
    assert "item_options" not in item["item_data"]


def test_build_objects_for_product_reuses_existing_ids_for_idempotency():
    product = {
        "name": "Keychain",
        "base_price": 8.0,
        "options": {"color": [{"name": "Blue"}, {"name": "Red"}]},
    }
    _objects, id_plan = sc.build_objects_for_product(product, existing={})
    assert id_plan["item_id"].startswith("#")

    fake_existing = {
        "item_id": "REAL_ITEM_ID",
        "option_ids": {"color": "REAL_OPT_ID"},
        "option_value_ids": {"color": {"Blue": "REAL_BLUE_ID", "Red": "REAL_RED_ID"}},
        "variation_ids": id_plan["variation_ids"],
    }

    objects2, _id_plan2 = sc.build_objects_for_product(product, existing=fake_existing)
    item2 = next(o for o in objects2 if o["type"] == "ITEM")
    assert item2["id"] == "REAL_ITEM_ID"

    option2 = next(o for o in objects2 if o["type"] == "ITEM_OPTION")
    assert option2["id"] == "REAL_OPT_ID"

    value_ids = {v["item_option_value_data"]["name"]: v["id"] for v in option2["item_option_data"]["values"]}
    assert value_ids == {"Blue": "REAL_BLUE_ID", "Red": "REAL_RED_ID"}


def test_build_batch_request_produces_valid_json_payload():
    products = sc.load_spec(REPO_ROOT / "products.yaml")
    request_body, id_plans = sc.build_batch_request(products, id_map={})

    json.dumps(request_body)  # must be JSON-serializable, exactly what requests would send

    assert "idempotency_key" in request_body
    assert len(request_body["batches"]) == 1
    objects = request_body["batches"][0]["objects"]
    assert any(o["type"] == "ITEM" for o in objects)
    assert len(id_plans) == len(products)


def test_dry_run_end_to_end(tmp_path, capsys):
    spec = tmp_path / "products.yaml"
    spec.write_text("- name: Test Item\n  base_price: 10\n  options:\n    color:\n      - {name: Blue}\n")

    rc = sc.main([str(spec), "--env", "sandbox", "--dry-run"])

    assert rc == 0
    out = capsys.readouterr().out
    assert '"type": "ITEM"' in out
    assert not (tmp_path / ".catalog_ids.json").exists()


def test_missing_token_without_dry_run_errors(tmp_path, monkeypatch, capsys):
    spec = tmp_path / "products.yaml"
    spec.write_text("- name: Test Item\n  base_price: 10\n")
    monkeypatch.delenv("SQUARE_ACCESS_TOKEN", raising=False)

    rc = sc.main([str(spec), "--env", "sandbox"])

    assert rc == 1
    assert "SQUARE_ACCESS_TOKEN" in capsys.readouterr().err


def test_sync_with_mocked_api_call_updates_id_map(tmp_path, monkeypatch):
    spec = tmp_path / "products.yaml"
    spec.write_text("- name: Test Item\n  base_price: 10\n  options:\n    color:\n      - {name: Blue}\n")
    monkeypatch.setenv("SQUARE_ACCESS_TOKEN", "sandbox-sq0atb-fake")

    captured = {}

    def fake_call_batch_upsert(base_url, token, request_body):
        captured["base_url"] = base_url
        captured["token"] = token
        captured["request_body"] = request_body
        mappings = []
        for obj in request_body["batches"][0]["objects"]:
            mappings.append({"client_object_id": obj["id"], "object_id": obj["id"].replace("#", "SQ_")})
            if obj["type"] == "ITEM":
                for variation in obj["item_data"]["variations"]:
                    mappings.append(
                        {"client_object_id": variation["id"], "object_id": variation["id"].replace("#", "SQ_")}
                    )
            if obj["type"] == "ITEM_OPTION":
                for value in obj["item_option_data"]["values"]:
                    mappings.append({"client_object_id": value["id"], "object_id": value["id"].replace("#", "SQ_")})
        return {"id_mappings": mappings}

    monkeypatch.setattr(sc, "call_batch_upsert", fake_call_batch_upsert)

    rc = sc.main([str(spec), "--env", "sandbox"])

    assert rc == 0
    assert captured["base_url"] == sc.BASE_URLS["sandbox"]
    assert captured["token"] == "sandbox-sq0atb-fake"

    id_map = json.loads((tmp_path / ".catalog_ids.json").read_text())
    plan = id_map["Test Item"]
    assert plan["item_id"].startswith("SQ_")
    assert not plan["item_id"].startswith("#")

    # Re-running should reuse the now-real IDs instead of minting new temp ones.
    rc2 = sc.main([str(spec), "--env", "sandbox"])
    assert rc2 == 0
    assert captured["request_body"]["batches"][0]["objects"][-1]["id"] == plan["item_id"]
