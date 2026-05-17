from fastapi import APIRouter

from app.rag import get_collection_size

router = APIRouter()


@router.get("/")
def root():
    return {
        "service": "Clinora API",
        "version": "4.0.0",
        "rag_db_size": get_collection_size(),
        "status": "ok",
    }


@router.get("/api/rag/status")
def rag_status():
    size = get_collection_size()
    return {"document_count": size, "status": "ready" if size > 0 else "empty"}
