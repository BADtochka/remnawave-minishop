from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARIFF_EDITOR = REPO_ROOT / "frontend/src/admin/sections/TariffEditorModal.svelte"


def test_create_tariff_save_button_uses_store_validation_instead_of_key_disable():
    source = TARIFF_EDITOR.read_text(encoding="utf-8")
    save_start = source.index("onclick={tariffsStore.saveTariffDraft}")
    save_block = source[save_start : source.index("</AdminButton>", save_start)]

    assert "disabled={tariffsSaving}" in save_block
    assert "!tariffDraft.key.trim()" not in save_block
