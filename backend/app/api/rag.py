from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.rag import (
    RagChunkRecord,
    RagAnswerRequest,
    RagAnswerResult,
    RagAnswerRunRecord,
    RagDocumentCreateRequest,
    RagDocumentIndexRequest,
    RagDocumentIndexResult,
    RagDocumentRecord,
    RagSearchRequest,
    RagSearchResult,
    RagStatsResponse,
)
from app.services import rag_service


router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post(
    "/documents",
    response_model=ApiResponse[RagDocumentRecord],
    status_code=status.HTTP_201_CREATED,
)
async def create_rag_document(
    request: Request,
    payload: RagDocumentCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    document = rag_service.create_document(db, payload)
    return {"data": document, "request_id": request.state.request_id}


@router.get("/documents", response_model=ApiResponse[ListResponse[RagDocumentRecord]])
async def list_rag_documents(
    request: Request,
    source_type: str | None = Query(default=None),
    index_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    documents = rag_service.list_documents(
        db,
        source_type=source_type,
        index_status=index_status,
    )
    return {
        "data": ListResponse(items=documents, total=len(documents)),
        "request_id": request.state.request_id,
    }


@router.get("/documents/{doc_id}", response_model=ApiResponse[RagDocumentRecord])
async def get_rag_document(
    request: Request,
    doc_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    document = rag_service.get_document(db, doc_id)
    return {"data": document, "request_id": request.state.request_id}


@router.delete("/documents/{doc_id}", response_model=ApiResponse[dict[str, object]])
async def delete_rag_document(
    request: Request,
    doc_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = rag_service.delete_document(db, doc_id)
    return {"data": result, "request_id": request.state.request_id}


@router.post(
    "/documents/{doc_id}/index",
    response_model=ApiResponse[RagDocumentIndexResult],
)
async def index_rag_document(
    request: Request,
    doc_id: str,
    payload: RagDocumentIndexRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = rag_service.index_document(db, doc_id, payload)
    return {"data": result, "request_id": request.state.request_id}


@router.get("/chunks", response_model=ApiResponse[ListResponse[RagChunkRecord]])
async def list_rag_chunks(
    request: Request,
    doc_id: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    chunks = rag_service.list_chunks(db, doc_id=doc_id, source_type=source_type)
    return {
        "data": ListResponse(items=chunks, total=len(chunks)),
        "request_id": request.state.request_id,
    }


@router.post("/search", response_model=ApiResponse[RagSearchResult])
async def search_rag_documents(
    request: Request,
    payload: RagSearchRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = rag_service.search_documents(db, payload)
    return {"data": result, "request_id": request.state.request_id}


@router.post("/answer", response_model=ApiResponse[RagAnswerResult])
async def answer_rag_question(
    request: Request,
    payload: RagAnswerRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = rag_service.answer_question(db, payload)
    return {"data": result, "request_id": request.state.request_id}


@router.get("/stats", response_model=ApiResponse[RagStatsResponse])
async def get_rag_stats(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    stats = rag_service.get_stats(db)
    return {"data": stats, "request_id": request.state.request_id}


@router.get("/answers", response_model=ApiResponse[ListResponse[RagAnswerRunRecord]])
async def list_rag_answer_runs(
    request: Request,
    grounded: bool | None = Query(default=None),
    uncertainty: str | None = Query(default=None),
    retrieval_mode: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    answer_runs = rag_service.list_answer_runs(
        db,
        grounded=grounded,
        uncertainty=uncertainty,
        retrieval_mode=retrieval_mode,
    )
    return {
        "data": ListResponse(items=answer_runs, total=len(answer_runs)),
        "request_id": request.state.request_id,
    }


@router.get(
    "/answers/{answer_run_id}",
    response_model=ApiResponse[RagAnswerRunRecord],
)
async def get_rag_answer_run(
    request: Request,
    answer_run_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    answer_run = rag_service.get_answer_run(db, answer_run_id)
    return {"data": answer_run, "request_id": request.state.request_id}
