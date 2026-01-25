# app/routers/documents.py
"""
Document routes.

Endpoints:
- GET    /api/v1/documents          - List documents
- GET    /api/v1/documents/{id}     - Get specific document
- POST   /api/v1/documents          - Upload document metadata
- DELETE /api/v1/documents/{id}     - Delete document (admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.document import DocumentCreate, DocumentResponse
from app.dependencies import get_current_user, require_admin
from app.models import User, Document
from app.services.activity import log_activity

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"]
)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search by title"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """
    List documents with filtering and pagination.
    
    Query parameters:
    - category: Filter by category (e.g., "Policies", "Forms")
    - search: Search in document titles
    - skip: Number of records to skip (for pagination)
    - limit: Maximum records to return (default: 50, max: 100)
    
    Example: GET /api/v1/documents?category=Policies&search=handbook
    """
    
    query = select(Document)
    
    # Filter by category
    if category:
        query = query.where(Document.category == category)
    
    # Search by title (case-insensitive)
    if search:
        query = query.where(Document.title.ilike(f"%{search}%"))
    
    # Order by creation date (newest first) and paginate
    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return [DocumentResponse.from_document(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """
    Get a specific document by ID.
    """
    
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse.from_document(document)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new document entry.
    
    Note: This stores document METADATA. The actual file should be
    uploaded separately to your file storage (S3, etc.) and the
    URL provided here.
    
    Request body:
    {
        "title": "Employee Handbook",
        "category": "Policies",
        "description": "Guide for new employees",
        "file_url": "https://storage.example.com/handbook.pdf",
        "file_size": 2048576
    }
    """
    
    document = Document(
        title=data.title,
        category=data.category,
        description=data.description,
        file_url=data.file_url,
        file_size=data.file_size,
        uploaded_by=current_user.id  # Track who uploaded
    )
    
    db.add(document)
    await db.flush()
    
    # Log activity
    await log_activity(
        db,
        title=f"Document Uploaded: {data.title}",
        author=current_user.name,
        action_type="upload",
        entity_type="document",
        entity_id=document.id
    )
    
    await db.commit()
    await db.refresh(document)
    
    return DocumentResponse.from_document(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only!
):
    """
    Delete a document.
    
    Requires admin role.
    
    Note: This only deletes the metadata. You should also delete
    the actual file from your file storage.
    """
    
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    title = document.title
    
    # Log activity
    await log_activity(
        db,
        title=f"Document Deleted: {title}",
        author=current_user.name,
        action_type="delete",
        entity_type="document",
        entity_id=document_id
    )
    
    await db.delete(document)
    await db.commit()
    
    return None