"""
Initialize the five Nikaya collections for the complete Pali Sutta Pitaka.

This script adds the five collections to the database before batch import:
- Dīgha Nikāya (长部)
- Majjhima Nikāya (中部)
- Saṁyutta Nikāya (相应部)
- Aṅguttara Nikāya (增支部)
- Khuddaka Nikāya (小部)
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models import Collection, Tradition


NIKAYA_COLLECTIONS = [
    {
        "id": "coll-pali-dn",
        "slug": "pali-dn",
        "title": "长部 / Dīgha Nikāya",
        "tradition_id": "trad-pali",
        "description": "The Dīgha Nikāya ('Collection of Long Discourses') is the first of the five Nikāyas of the Sutta Pitaka.",
        "coverage_note": "Contains 34 long suttas.",
        "is_sample": False,
    },
    {
        "id": "coll-pali-mn",
        "slug": "pali-mn",
        "title": "中部 / Majjhima Nikāya",
        "tradition_id": "trad-pali",
        "description": "The Majjhima Nikāya ('Collection of Middle-length Discourses') is the second of the five Nikāyas.",
        "coverage_note": "Contains 152 middle-length suttas.",
        "is_sample": False,
    },
    {
        "id": "coll-pali-sn",
        "slug": "pali-sn",
        "title": "相应部 / Saṁyutta Nikāya",
        "tradition_id": "trad-pali",
        "description": "The Saṁyutta Nikāya ('Connected Discourses') is the third of the five Nikāyas.",
        "coverage_note": "Contains approximately 2,889 suttas grouped by topic.",
        "is_sample": False,
    },
    {
        "id": "coll-pali-an",
        "slug": "pali-an",
        "title": "增支部 / Aṅguttara Nikāya",
        "tradition_id": "trad-pali",
        "description": "The Aṅguttara Nikāya ('Numbered Discourses') is the fourth of the five Nikāyas.",
        "coverage_note": "Contains approximately 9,575 suttas grouped by numerical sets.",
        "is_sample": False,
    },
    {
        "id": "coll-pali-kn",
        "slug": "pali-kn",
        "title": "小部 / Khuddaka Nikāya",
        "tradition_id": "trad-pali",
        "description": "The Khuddaka Nikāya ('Minor Collection') is the fifth and last of the five Nikāyas.",
        "coverage_note": "Contains a variety of shorter texts and anthologies including Dhammapada, Udāna, Itivuttaka, etc.",
        "is_sample": False,
    },
]


def init_collections(db: Session) -> None:
    # Check that the pali tradition exists
    tradition = db.scalar(select(Tradition).where(Tradition.id == "trad-pali"))
    if not tradition:
        raise ValueError("Pali tradition (trad-pali) not found in database. Run bootstrap first.")

    for coll_data in NIKAYA_COLLECTIONS:
        existing = db.scalar(select(Collection).where(Collection.id == coll_data["id"]))
        if existing:
            print(f"WARNING: Collection {coll_data['id']} already exists, skipping.")
            continue

        collection = Collection(**coll_data)
        db.add(collection)
        print(f"Added collection: {coll_data['id']}")

    db.commit()
    print(f"\nAll five Nikaya collections initialized.")


def main() -> None:
    with SessionLocal() as session:
        init_collections(session)


if __name__ == "__main__":
    main()
