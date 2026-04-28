from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.core.config import ROOT_DIR


DEFAULT_TRANSLATOR_PRIORITY: dict[str, list[str]] = {
    "en": ["sujato", "brahmali", "soma", "kelly", "anandajoti", "suddhaso", "kovilo", "patton"],
}


def uid_from_text_path(text_path: str) -> str:
    stem = Path(text_path).stem
    if "_" not in stem:
        raise ValueError(f"Unexpected CST4 text path format: {text_path}")
    return stem.split("_", 1)[1]


def build_root_index(root_base: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in sorted(root_base.rglob("*_root-pli-ms.json")):
        uid = path.name.replace("_root-pli-ms.json", "")
        index[uid] = path
    return index


def _translator_from_path(path: Path, translation_lang_base: Path) -> str:
    relative = path.relative_to(translation_lang_base)
    return relative.parts[0]


def build_translation_index(
    translation_lang_base: Path,
    *,
    language_code: str,
    preferred_translators: list[str] | None = None,
) -> dict[str, Path]:
    priority = preferred_translators or DEFAULT_TRANSLATOR_PRIORITY.get(language_code, [])
    rank = {translator: index for index, translator in enumerate(priority)}
    index: dict[str, Path] = {}

    for path in sorted(translation_lang_base.rglob(f"*_translation-{language_code}-*.json")):
        uid = path.name.split(f"_translation-{language_code}-", 1)[0]
        current = index.get(uid)
        if current is None:
            index[uid] = path
            continue

        current_translator = _translator_from_path(current, translation_lang_base)
        candidate_translator = _translator_from_path(path, translation_lang_base)
        current_rank = rank.get(current_translator, len(rank))
        candidate_rank = rank.get(candidate_translator, len(rank))
        if candidate_rank < current_rank or (
            candidate_rank == current_rank and path.as_posix() < current.as_posix()
        ):
            index[uid] = path

    return index


def load_ordered_segments(json_path: Path) -> dict[str, str]:
    with json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {json_path}")
    return payload


def render_bilingual_lines(root_segments: dict[str, str], translation_segments: dict[str, str]) -> tuple[list[str], int]:
    lines: list[str] = []
    glossed_segments = 0

    for key, root_text in root_segments.items():
        cleaned_root = (root_text or "").strip()
        if not cleaned_root:
            continue
        cleaned_translation = (translation_segments.get(key) or "").strip()
        if cleaned_translation:
            lines.append(f"{cleaned_root} ||| {cleaned_translation}")
            glossed_segments += 1
        else:
            lines.append(cleaned_root)

    if not lines:
        raise ValueError("No non-empty root segments available for bilingual render.")

    return lines, glossed_segments


def build_bilingual_manifest_payload(
    *,
    base_manifest: dict[str, Any],
    root_index: dict[str, Path],
    translation_index: dict[str, Path],
    output_root: Path,
    language_code: str,
    translation_lang_base: Path,
) -> tuple[dict[str, Any], dict[str, int]]:
    output_root.mkdir(parents=True, exist_ok=True)

    payload = {
        "source": dict(base_manifest["source"]),
        "texts": [],
    }
    payload["source"]["access_note"] = (
        (payload["source"].get("access_note") or "").strip() + " "
        + f"Aligned {language_code} gloss generated from local SuttaCentral Bilara translation data."
    ).strip()

    stats = {
        "texts_total": 0,
        "texts_with_translation_file": 0,
        "segments_total": 0,
        "segments_with_gloss": 0,
    }

    for text_item in base_manifest.get("texts", []):
        stats["texts_total"] += 1
        uid = uid_from_text_path(text_item["text_path"])
        root_path = root_index.get(uid)
        if root_path is None:
            raise FileNotFoundError(f"Missing Bilara root JSON for {uid}")

        translation_path = translation_index.get(uid)
        if translation_path:
            stats["texts_with_translation_file"] += 1
            translation_segments = load_ordered_segments(translation_path)
            translator = _translator_from_path(translation_path, translation_lang_base)
        else:
            translation_segments = {}
            translator = None

        root_segments = load_ordered_segments(root_path)
        lines, glossed_segments = render_bilingual_lines(root_segments, translation_segments)
        stats["segments_total"] += len(lines)
        stats["segments_with_gloss"] += glossed_segments

        relative_output_path = output_root / Path(text_item["text_path"]).name
        absolute_output_path = ROOT_DIR / relative_output_path
        absolute_output_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        updated_text_item = dict(text_item)
        updated_text_item["text_path"] = relative_output_path.as_posix()
        updated_text_version = dict(updated_text_item["text_version"])
        updated_text_version["script_note"] = (
            f"Aligned {language_code} gloss from SuttaCentral Bilara"
            + (f" ({translator})" if translator else "")
            + "."
        )
        updated_text_item["text_version"] = updated_text_version
        payload["texts"].append(updated_text_item)

    return payload, stats


def write_manifest(payload: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path
