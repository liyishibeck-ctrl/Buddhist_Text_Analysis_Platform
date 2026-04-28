from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from backend.app.services import plain_text_loader
from scripts.ingest.pali import batch_import_cst4


def _write_text(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_workspace_test_root() -> Path:
    root = Path("D:/Buddhist_Text_Analysis_Platform/data/processed/test_tmp") / f"pali-import-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_parse_filename_returns_canonical_reference_and_slug() -> None:
    parsed = batch_import_cst4.parse_filename("an001_an1.1-10.txt")

    assert parsed == {
        "nikaya_code": "an",
        "canonical_ref": "1.1-10",
        "reference_slug": "1-1-10",
    }


def test_scan_directory_generates_readable_ids_and_kn_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_workspace_test_root()
    input_dir = root / "data" / "raw" / "pali" / "cst4-full"
    try:
        _write_text(
            root,
            "data/raw/pali/cst4-full/sn047_sn47.45.txt",
            "\n".join(
                [
                    "Saṁyutta Nikāya 47.45",
                    "5. Amatavagga",
                    "Kusalarāsisutta",
                    "Evaṁ me sutaṁ—",
                    "",
                ]
            ),
        )
        _write_text(
            root,
            "data/raw/pali/texts/dhammapada.txt",
            "\n".join(
                [
                    "**Dhammapada - Selected Verses**",
                    "",
                    "Manopubbaṅgamā dhammā manasetu manosevitā ||| 诸法意先导",
                    "",
                ]
            ),
        )
        monkeypatch.setattr(batch_import_cst4, "ROOT_DIR", root)

        result = batch_import_cst4.scan_directory(input_dir)

        sn_entry = next(item for item in result["texts"] if item["canonical_code"] == "SN 47.45")
        kn_entry = next(item for item in result["texts"] if item["canonical_code"] == "KN Dhp")

        assert sn_entry["work_id"] == "work-pi-sn-47-45"
        assert sn_entry["text_version"]["id"] == "tv-sn-47-45-cst4"
        assert sn_entry["text_version"]["slug"] == "sn-47-45-cst4"
        assert sn_entry["text_version"]["title"] == "Kusalarāsisutta (SN 47.45)"
        assert sn_entry["work_metadata"]["pitaka_division"] == "sutra"
        assert sn_entry["segment_by"] == "line"

        assert kn_entry["work_id"] == "work-pi-kn-dhp"
        assert kn_entry["text_version"]["title"] == "Dhammapada (KN Dhp)"
        assert result["stats"]["kn_fallback_added"] == 1
        assert result["stats"]["by_nikaya"]["kn"] == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_scan_directory_skips_group_headings_when_no_sutta_title_found(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_workspace_test_root()
    input_dir = root / "data" / "raw" / "pali" / "cst4-full"
    try:
        _write_text(
            root,
            "data/raw/pali/cst4-full/an001_an1.1-10.txt",
            "\n".join(
                [
                    "Aṅguttara Nikāya 1",
                    "1. Rūpādivagga",
                    "1",
                    "Evaṁ me sutaṁ—",
                    "",
                ]
            ),
        )
        _write_text(root, "data/raw/pali/texts/dhammapada.txt", "Dhammapada\n")
        monkeypatch.setattr(batch_import_cst4, "ROOT_DIR", root)

        result = batch_import_cst4.scan_directory(input_dir)

        an_entry = next(item for item in result["texts"] if item["canonical_code"] == "AN 1.1-10")

        assert an_entry["work_id"] == "work-pi-an-1-1-10"
        assert an_entry["text_version"]["id"] == "tv-an-1-1-10-cst4"
        assert an_entry["text_version"]["title"] == "AN 1.1-10"
        assert an_entry["work_metadata"]["title"] == "Aṅguttara Nikāya 1.1-10"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_stable_segment_id_slugifies_canonical_code() -> None:
    assert plain_text_loader._stable_segment_id("SN 47.45", 1) == "seg-plain-sn-47-45-001"
