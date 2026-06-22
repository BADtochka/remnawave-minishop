from __future__ import annotations

import json
from pathlib import Path

from bot.app.web.openapi import DEFAULT_OUTPUT_PATH, generate_openapi, serialize_openapi


def test_openapi_artifact_is_current():
    expected = DEFAULT_OUTPUT_PATH.read_text(encoding="utf-8")
    actual = serialize_openapi(generate_openapi())

    assert actual == expected, "Regenerate docs/openapi.json with backend/bot/app/web/openapi.py"


def test_openapi_includes_typed_promos_contracts():
    document = json.loads(DEFAULT_OUTPUT_PATH.read_text(encoding="utf-8"))

    create_operation = document["paths"]["/api/admin/promos"]["post"]
    assert (
        create_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PromoCreateBody"
    )
    assert (
        create_operation["responses"]["200"]["content"]["application/json"]["schema"]["properties"][
            "promo"
        ]["$ref"]
        == "#/components/schemas/PromoOut"
    )

    export_operation = document["paths"]["/api/admin/payments/export.csv"]["get"]
    assert "text/csv" in export_operation["responses"]["200"]["content"]


def test_openapi_lists_every_live_api_route():
    document = json.loads(DEFAULT_OUTPUT_PATH.read_text(encoding="utf-8"))
    generated = generate_openapi()

    assert set(document["paths"]) == set(generated["paths"])
    assert Path("docs/openapi.json") == DEFAULT_OUTPUT_PATH.relative_to(Path.cwd())
