from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from pathlib import Path

from backend.app.services.pali_bilara_gloss import (
    build_bilingual_manifest_payload,
    build_root_index,
    build_translation_index,
    render_bilingual_lines,
    uid_from_text_path,
)


def test_uid_from_text_path_and_render_bilingual_lines() -> None:
    assert uid_from_text_path("data/raw/pali/cst4-full/an001_an1.1-10.txt") == "an1.1-10"

    lines, glossed_count = render_bilingual_lines(
        {
            "an1.1:0.1": "Aṅguttara Nikāya 1 ",
            "an1.1:1.1": "Evaṁ me sutaṁ—",
            "an1.1:1.2": "ekaṁ samayaṁ",
        },
        {
            "an1.1:0.1": "Numbered Discourses 1.1–10 ",
            "an1.1:1.1": "So I have heard. ",
        },
    )

    assert lines == [
        "Aṅguttara Nikāya 1 ||| Numbered Discourses 1.1–10",
        "Evaṁ me sutaṁ— ||| So I have heard.",
        "ekaṁ samayaṁ",
    ]
    assert glossed_count == 2


def test_build_bilingual_manifest_payload_prefers_sujato_translation() -> None:
    tmp_path = Path(tempfile.gettempdir()) / "buddha_mvp_pali_bilara" / uuid.uuid4().hex
    root_base = tmp_path / "root" / "pli" / "ms" / "sutta" / "an" / "an1"
    en_base = tmp_path / "translation" / "en"
    output_root = Path("data/processed/test-pali-bilara")
    root_base.mkdir(parents=True)
    (en_base / "kelly" / "sutta" / "an" / "an1").mkdir(parents=True)
    (en_base / "sujato" / "sutta" / "an" / "an1").mkdir(parents=True)

    try:
        root_path = root_base / "an1.1-10_root-pli-ms.json"
        root_path.write_text(
            json.dumps(
                {
                    "an1.1:0.1": "Aṅguttara Nikāya 1 ",
                    "an1.1:1.1": "Evaṁ me sutaṁ—",
                    "an1.1:1.2": "ekaṁ samayaṁ",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (en_base / "kelly" / "sutta" / "an" / "an1" / "an1.1-10_translation-en-kelly.json").write_text(
            json.dumps({"an1.1:1.1": "Kelly translation."}, ensure_ascii=False),
            encoding="utf-8",
        )
        (en_base / "sujato" / "sutta" / "an" / "an1" / "an1.1-10_translation-en-sujato.json").write_text(
            json.dumps(
                {
                    "an1.1:0.1": "Numbered Discourses 1.1–10 ",
                    "an1.1:1.1": "So I have heard.",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        base_manifest = {
            "source": {
                "id": "source-pali-cst4-complete",
                "slug": "pali-cst4-complete",
                "title": "Pali Tipitaka CST4 complete edition",
                "source_type": "canon",
                "citation": "test citation",
                "url": "https://example.com",
                "access_note": "test note",
                "is_sample": False,
            },
            "texts": [
                {
                    "work_id": "work-pi-an-1-10",
                    "canonical_code": "AN 1.1-10",
                    "language_id": "lang-pi",
                    "text_path": "data/raw/pali/cst4-full/an001_an1.1-10.txt",
                    "segment_by": "line",
                    "is_sample": False,
                    "text_version": {
                        "id": "tv-an-1-10-cst4",
                        "slug": "an-1-10-cst4",
                        "title": "AN 1.1-10",
                        "version_label": "CST4 Pali",
                        "summary": "test summary",
                        "sample_note": None,
                        "is_sample": False,
                    },
                    "person_roles": [],
                }
            ],
        }

        root_index = build_root_index(tmp_path / "root" / "pli" / "ms" / "sutta")
        translation_index = build_translation_index(en_base, language_code="en")
        payload, stats = build_bilingual_manifest_payload(
            base_manifest=base_manifest,
            root_index=root_index,
            translation_index=translation_index,
            output_root=output_root,
            language_code="en",
            translation_lang_base=en_base,
        )

        generated_path = Path("D:/Buddhist_Text_Analysis_Platform") / payload["texts"][0]["text_path"]
        generated_content = generated_path.read_text(encoding="utf-8")
        assert "Aṅguttara Nikāya 1 ||| Numbered Discourses 1.1–10" in generated_content
        assert "Evaṁ me sutaṁ— ||| So I have heard." in generated_content
        assert "Kelly translation." not in generated_content
        assert payload["texts"][0]["text_version"]["script_note"] == "Aligned en gloss from SuttaCentral Bilara (sujato)."
        assert stats["texts_with_translation_file"] == 1
        assert stats["segments_with_gloss"] == 2
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
        generated_root = Path("D:/Buddhist_Text_Analysis_Platform") / output_root
        if generated_root.exists():
            shutil.rmtree(generated_root, ignore_errors=True)
