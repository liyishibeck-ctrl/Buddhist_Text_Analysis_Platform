from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.models import Collection, Language, Tradition
from backend.app.services import (
    catalog_service,
    embedding_theme_map_service,
    pali_theme_map_service,
    rag_service,
    retrieval_service,
    search_service,
    sutra_explainer_service,
    unit_theme_map_service,
    vector_service,
)


router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(settings.templates_dir))


def _filter_context(db: Session) -> dict:
    traditions = db.scalars(select(Tradition).order_by(Tradition.name)).all()
    collections = db.scalars(select(Collection).order_by(Collection.title)).all()
    languages = db.scalars(select(Language).order_by(Language.name)).all()
    return {
        "traditions": traditions,
        "collections": collections,
        "languages": languages,
        "pitaka_divisions": [
            ("sutra", "经藏"),
            ("vinaya", "律藏"),
            ("abhidharma", "论藏"),
        ],
    }


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    overview = catalog_service.get_overview(db)
    han_catalog = catalog_service.get_han_catalog_overview(db)
    parallels = catalog_service.list_parallel_links(db)
    concepts = catalog_service.list_concepts(db)
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "request": request,
            "overview": overview,
            "han_catalog": han_catalog,
            "parallel_count": len(parallels),
            "concepts": concepts[:6],
        },
    )


@router.get("/works")
def works_page(
    request: Request,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    pitaka_division: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    works = catalog_service.list_works(
        db,
        tradition_id=tradition_id,
        collection_id=collection_id,
        language_id=language_id,
        pitaka_division=pitaka_division,
        q=q,
    )
    context = _filter_context(db)
    context.update(
        {
            "request": request,
            "works": works,
            "selected_tradition": tradition_id,
            "selected_collection": collection_id,
            "selected_language": language_id,
            "selected_pitaka_division": pitaka_division,
            "search_term": q or "",
        }
    )
    return templates.TemplateResponse(request, "works.html", context)


@router.get("/works/{work_id}")
def work_detail_page(request: Request, work_id: str, db: Session = Depends(get_db)):
    work = catalog_service.get_work_detail(db, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return templates.TemplateResponse(request, "work_detail.html", {"request": request, "work": work})


@router.get("/text-versions/{text_version_id}")
def text_version_detail_page(request: Request, text_version_id: str, db: Session = Depends(get_db)):
    reading_limit = 200
    text_version = catalog_service.get_text_version_page_detail(db, text_version_id)
    if not text_version:
        raise HTTPException(status_code=404, detail="Text version not found")
    reading_segments = catalog_service.list_text_version_reading_segments(
        db,
        text_version_id=text_version_id,
        limit=reading_limit,
    )
    return templates.TemplateResponse(
        request,
        "text_version_detail.html",
        {
            "request": request,
            "text_version": text_version,
            "reading_segments": reading_segments,
            "reading_limit": reading_limit,
        },
    )


@router.get("/segments/{segment_id}")
def segment_detail_page(request: Request, segment_id: str, db: Session = Depends(get_db)):
    segment = catalog_service.get_segment_detail(db, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return templates.TemplateResponse(request, "segment_detail.html", {"request": request, "segment": segment})


@router.get("/parallels")
def parallels_page(request: Request, db: Session = Depends(get_db)):
    parallels = catalog_service.list_parallel_links(db)
    return templates.TemplateResponse(request, "parallels.html", {"request": request, "parallels": parallels})


@router.get("/han/catalog")
def han_catalog_page(request: Request, db: Session = Depends(get_db)):
    overview = catalog_service.get_han_catalog_overview(db)
    if not overview:
        raise HTTPException(status_code=404, detail="Han catalog not found")
    return templates.TemplateResponse(request, "han_catalog.html", {"request": request, "catalog": overview})


@router.get("/concepts")
def concepts_page(request: Request, db: Session = Depends(get_db)):
    concepts = catalog_service.list_concepts(db)
    return templates.TemplateResponse(request, "concepts.html", {"request": request, "concepts": concepts})


@router.get("/concepts/{concept_slug}")
def concept_detail_page(request: Request, concept_slug: str, db: Session = Depends(get_db)):
    concept = catalog_service.get_concept_detail(db, concept_slug)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return templates.TemplateResponse(request, "concept_detail.html", {"request": request, "concept": concept})


@router.get("/theme-map")
def embedding_theme_map_page(request: Request):
    theme_maps = embedding_theme_map_service.load_embedding_theme_maps_snapshot()
    return templates.TemplateResponse(
        request,
        "embedding_theme_map.html",
        {
            "request": request,
            "theme_maps": theme_maps,
            "selected_tradition": None,
        },
    )


@router.get("/unit-theme-map")
def unit_theme_map_page(request: Request):
    unit_theme_maps = unit_theme_map_service.load_unit_theme_maps_snapshot()
    return templates.TemplateResponse(
        request,
        "unit_theme_map.html",
        {
            "request": request,
            "unit_theme_maps": unit_theme_maps,
        },
    )


@router.get("/concept-system-map")
def concept_system_map_page(request: Request):
    return templates.TemplateResponse(request, "concept_system_map.html", {"request": request})


@router.get("/sutra-explainer")
def sutra_explainer_page(
    request: Request,
    q: Optional[str] = None,
    mode: str = "hybrid",
    top_k: int = 12,
    style: str = "comparative",
    generate: bool = False,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    context = _filter_context(db)
    context.update(
        {
            "request": request,
            "query_text": q or "",
            "selected_mode": mode,
            "selected_top_k": top_k,
            "selected_style": style,
            "selected_generate": generate,
            "selected_tradition": tradition_id,
            "selected_collection": collection_id,
            "selected_language": language_id,
            "explain_payload": None,
        }
    )
    if q:
        context["explain_payload"] = sutra_explainer_service.explain_sutra_query(
            db,
            query_text=q,
            top_k=top_k,
            retrieval_mode=mode,
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
            explanation_style=style,
            generate_answer=generate,
        )
    return templates.TemplateResponse(request, "sutra_explainer.html", context)


@router.get("/pali/theme-map")
def pali_theme_map_page(request: Request):
    theme_maps = embedding_theme_map_service.load_embedding_theme_maps_snapshot()
    if theme_maps:
        return templates.TemplateResponse(
            request,
            "embedding_theme_map.html",
            {
                "request": request,
                "theme_maps": theme_maps,
                "selected_tradition": "trad-pali",
            },
        )
    theme_map = pali_theme_map_service.load_pali_theme_map_snapshot()
    return templates.TemplateResponse(
        request,
        "pali_theme_map.html",
        {
            "request": request,
            "theme_map": theme_map,
        },
    )


@router.get("/research")
def research_page(
    request: Request,
    q: Optional[str] = None,
    mode: str = "hybrid",
    top_k: int = 8,
    tradition_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    language_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    context = _filter_context(db)
    context.update(
        {
            "request": request,
            "query_text": q or "",
            "selected_mode": mode,
            "selected_top_k": top_k,
            "selected_tradition": tradition_id,
            "selected_collection": collection_id,
            "selected_language": language_id,
            "keyword_hits": [],
            "hybrid_payload": None,
            "vector_payload": None,
            "rag_payload": None,
        }
    )
    if q:
        context["keyword_hits"] = search_service.search_segments(
            db,
            q=q,
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
            limit=max(top_k, 8),
        )
        context["vector_payload"] = vector_service.vector_search(
            db,
            query_text=q,
            top_k=max(top_k, 8),
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
        )
        context["hybrid_payload"] = retrieval_service.hybrid_search(
            db,
            query_text=q,
            top_k=top_k,
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
        )
        context["rag_payload"] = rag_service.build_rag_context(
            db,
            query_text=q,
            top_k=top_k,
            retrieval_mode=mode,
            tradition_id=tradition_id,
            collection_id=collection_id,
            language_id=language_id,
        )
    return templates.TemplateResponse(request, "research.html", context)
