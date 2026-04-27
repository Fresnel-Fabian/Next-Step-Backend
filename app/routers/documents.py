# app/routers/documents.py
"""
Document routes.

Endpoints:
- GET    /api/v1/documents                          - List documents (filtered by role)
- GET    /api/v1/documents/announcement-attachments - Announcements with file attachments
- GET    /api/v1/documents/{id}                     - Get specific document
- POST   /api/v1/documents/upload                   - Upload actual file (returns URL)
- POST   /api/v1/documents                          - Upload document metadata (admin)
- DELETE /api/v1/documents/{id}                     - Delete document (admin)
"""

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.document import DocumentCreate, DocumentResponse
from app.dependencies import get_current_user, require_admin, require_roles
from app.models import User, Document, Announcement
from app.models.user import UserRole
from app.services.activity import log_activity
from app.services.notifications import broadcast_to_all

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    category: str | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List documents filtered by the current user's role.
    - ADMIN   → sees all documents
    - TEACHER → sees ALL + TEACHERS documents
    - STUDENT → sees ALL + STUDENTS documents
    """
    query = select(Document)

    if current_user.role == UserRole.TEACHER:
        query = query.where(Document.access_level.in_(["ALL", "TEACHERS"]))
    elif current_user.role == UserRole.STUDENT:
        query = query.where(Document.access_level.in_(["ALL", "STUDENTS"]))
    # ADMIN sees everything

    if category:
        query = query.where(Document.category == category)
    if search:
        query = query.where(Document.title.ilike(f"%{search}%"))

    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return [DocumentResponse.from_document(d) for d in result.scalars().all()]


# IMPORTANT: this must be before /{document_id} to avoid route conflict
@router.get("/announcement-attachments")
async def list_announcement_attachments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return all announcements that have a file attachment."""
    result = await db.execute(
        select(Announcement)
        .where(Announcement.file_url.isnot(None))
        .order_by(Announcement.created_at.desc())
    )
    announcements = result.scalars().all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "message": a.message,
            "file_url": a.file_url,
            "file_name": a.file_name,
            "created_at": a.created_at.isoformat(),
        }
        for a in announcements
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    return DocumentResponse.from_document(document)


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    allowed_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png'}
    ext = os.path.splitext(file.filename or '')[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed. Allowed: PDF, Word, Excel, JPEG, PNG",
        )

    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    return {
        "fileUrl": f"/uploads/{unique_filename}",
        "fileName": file.filename,
        "fileSize": len(contents),
    }


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a document entry. Admin only. access_level controls who can see it."""
    document = Document(
        title=data.title,
        category=data.category,
        description=data.description,
        file_url=data.file_url,
        file_size=data.file_size,
        access_level=data.access_level.value,
        uploaded_by=current_user.id,
    )

    db.add(document)
    await db.flush()

    await broadcast_to_all(
        db,
        title=f"New Document: {data.title}",
        message=data.description or f"A new document '{data.title}' has been uploaded.",
        notification_type="info",
        entity_type="document",
        file_url=data.file_url,
    )

    await log_activity(
        db,
        title=f"Document Uploaded: {data.title}",
        author=current_user.name,
        action_type="upload",
        entity_type="document",
        entity_id=document.id,
    )

    await db.commit()
    await db.refresh(document)

    return DocumentResponse.from_document(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    title = document.title

    if document.file_url and document.file_url.startswith("/uploads/"):
        file_path = document.file_url.lstrip("/")
        if os.path.exists(file_path):
            os.remove(file_path)

    await log_activity(
        db,
        title=f"Document Deleted: {title}",
        author=current_user.name,
        action_type="delete",
        entity_type="document",
        entity_id=document_id,
    )

    await db.delete(document)
    await db.commit()
    return None