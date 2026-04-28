from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from backend.app.services.tibetan_84000_discourses import (
    build_manifest_payload,
    build_tmx_index,
    parse_primary_toh_key,
    parse_primary_toh_number,
)


def _make_workspace_test_root() -> Path:
    root = Path("D:/Buddhist_Text_Analysis_Platform/data/processed/test_tmp") / f"tibetan-84000-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parse_primary_toh_helpers() -> None:
    assert parse_primary_toh_key("034-007_toh19,554-the_perfection_of_wisdom.xml") == "toh19"
    assert parse_primary_toh_key("037-007_toh44-45-chapter_45_the_stem_array.xml") == "toh44-45"
    assert parse_primary_toh_number("toh44-45") == 44
    assert parse_primary_toh_number("toh359") == 359


def test_build_manifest_payload_prefers_latest_tmx_and_dedupes_tei() -> None:
    root = _make_workspace_test_root()
    tei_root = root / "tei"
    tmx_root = root / "tmx"
    output_root = root / "output"

    try:
        _write_text(
            tei_root / "034-007_toh19,554-the_perfection_of_wisdom_for_kausika.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title type="mainTitle" xml:lang="en">The Perfection of Wisdom “Kauśika”</title>
        <title type="mainTitle" xml:lang="bo">ཤེར་ཕྱིན་ཀཽ་ཤི་ཀ</title>
        <title type="mainTitle" xml:lang="Bo-Ltn">sher phyin kau shi ka</title>
      </titleStmt>
    </fileDesc>
  </teiHeader>
  <text>
    <front>
      <div type="summary">
        <p>This is a short summary.</p>
      </div>
    </front>
  </text>
</TEI>
""",
        )
        _write_text(
            tei_root / "034-007_toh19,554-the_shorter_alias.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title type="mainTitle" xml:lang="en">Short Alias</title>
        <title type="mainTitle" xml:lang="bo">མིང་གཞན།</title>
        <title type="mainTitle" xml:lang="Bo-Ltn">ming gzhan</title>
      </titleStmt>
    </fileDesc>
  </teiHeader>
  <text>
    <front>
      <div type="summary">
        <p>Alias summary.</p>
      </div>
    </front>
  </text>
</TEI>
""",
        )
        _write_text(
            tei_root / "111-001_toh360-tantra_out_of_range.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title type="mainTitle" xml:lang="en">Tantra Text</title>
      </titleStmt>
    </fileDesc>
  </teiHeader>
</TEI>
""",
        )
        _write_text(
            tmx_root / "toh19-v3.tmx",
            """<?xml version="1.0" encoding="UTF-8"?>
<tmx xmlns="http://www.lisa.org/tmx14">
  <body>
    <tu>
      <tuv xml:lang="bo"><seg>ཨོཾ།</seg></tuv>
      <tuv xml:lang="en"><seg>OLD</seg></tuv>
    </tu>
  </body>
</tmx>
""",
        )
        _write_text(
            tmx_root / "toh19-v4.tmx",
            """<?xml version="1.0" encoding="UTF-8"?>
<tmx xmlns="http://www.lisa.org/tmx14" xmlns:tei="http://www.tei-c.org/ns/1.0">
  <body>
    <tu>
      <tuv xml:lang="bo"><seg><tei:ref folio="F.1.a"/>ཨོཾ།</seg></tuv>
      <tuv xml:lang="en"><seg>NEW</seg></tuv>
    </tu>
    <tu>
      <tuv xml:lang="bo"><seg>བཀྲ་ཤིས།</seg></tuv>
      <tuv xml:lang="en"><seg/></tuv>
    </tu>
  </body>
</tmx>
""",
        )

        tmx_index = build_tmx_index(tmx_root)
        assert tmx_index["toh19"].name == "toh19-v4.tmx"

        payload, stats = build_manifest_payload(tei_root=tei_root, tmx_root=tmx_root, output_root=output_root)

        assert stats["texts_built"] == 1
        assert stats["duplicate_tei_matches"] == 1
        assert stats["segments_generated"] == 2
        assert stats["segments_with_gloss"] == 1
        assert payload["texts"][0]["work_id"] == "work-toh19"
        assert payload["texts"][0]["text_version"]["id"] == "tv-toh19-84000"
        assert payload["texts"][0]["text_version"]["title"] == "Short Alias (Toh 19)"

        generated_path = Path("D:/Buddhist_Text_Analysis_Platform") / payload["texts"][0]["text_path"]
        assert generated_path.read_text(encoding="utf-8").splitlines() == [
            "ཨོཾ། ||| NEW",
            "བཀྲ་ཤིས།",
        ]
    finally:
        shutil.rmtree(root, ignore_errors=True)
