# app/routers/documents.py
"""
Document routes.

Endpoints:
- GET    /api/v1/documents          - List documents
- GET    /api/v1/documents/{id}     - Get specific document
- POST   /api/v1/documents          - Upload document metadata + notify all users
- POST   /api/v1/documents/upload   - Upload actual file (returns URL)
- DELETE /api/v1/documents/{id}     - Delete document (admin)
"""

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.document import DocumentCreate, DocumentResponse
from app.dependencies import get_current_user, require_admin, require_roles
from app.models import User, Document
from app.models.user import UserRole
from app.services.activity import log_activity
from app.services.notifications import broadcast_to_all

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

# Local upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    category: str | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Document)

    if category:
        query = query.where(Document.category == category)
    if search:
        query = query.where(Document.title.ilike(f"%{search}%"))

    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()

    return [DocumentResponse.from_document(d) for d in documents]


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
    request: Request,  # add this
    file: UploadFile = File(...),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    print("Content-Type:", request.headers.get("content-type"))
    print("File:", file)
    # Allowed extensions
    allowed_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png'}

    # Get extension from filename
    ext = os.path.splitext(file.filename or '')[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: PDF, Word, Excel, JPEG, PNG",
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file to disk
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    file_size = len(contents)
    file_url = f"/uploads/{unique_filename}"

    return {
        "fileUrl": file_url,
        "fileName": file.filename,
        "fileSize": file_size,
    }


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """
    Create a document entry and broadcast a notification to all users.
    Admin and Teacher only.
    """
    document = Document(
        title=data.title,
        category=data.category,
        description=data.description,
        file_url=data.file_url,
        file_size=data.file_size,
        uploaded_by=current_user.id,
    )

    db.add(document)
    await db.flush()

    # Broadcast notification with download link to all users
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

    # Delete file from disk if it's a local upload
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