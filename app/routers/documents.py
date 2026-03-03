# app/routers/documents.py
"""
Document routes.

Endpoints:
    GET    /api/v1/documents                 - List documents
    GET    /api/v1/documents/shared-with-me  - List Drive shared-with-me files
    GET    /api/v1/documents/{id}            - Get specific document
    POST   /api/v1/documents                 - Upload document metadata
    POST   /api/v1/documents/from-drive      - Register a Google Drive file
    DELETE /api/v1/documents/{id}            - Delete document (admin)

Note: /shared-with-me and /from-drive must be defined BEFORE /{id}
to prevent FastAPI matching them as integer IDs.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.document import DocumentCreate, DriveDocumentCreate, DocumentResponse
from app.dependencies import get_current_user, require_admin
from app.models import User, Document
from app.services.activity import log_activity

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    category: str | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    List documents with optional category filter, search, and pagination.
    """
    query = select(Document)

    if category:
        query = query.where(Document.category == category)
    if search:
        query = query.where(Document.title.ilike(f"%{search}%"))

    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()

    return [DocumentResponse.from_document(d) for d in documents]


@router.get("/shared-with-me", response_model=list[DocumentResponse])
async def list_shared_with_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch files shared with the current user from Google Drive.

    Calls the Drive API on behalf of the user, then syncs any new
    files into the local documents table so they appear in the app.

    Requires the user to have Drive tokens stored (i.e. signed in
    with Google and granted Drive permissions).

    References:
        files.list with sharedWithMe=true:
        https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list
    """
    from app.services.google_drive import get_shared_with_me, DriveAuthError

    try:
        drive_files = await get_shared_with_me(current_user, db)
    except DriveAuthError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    results = []

    for f in drive_files:
        # Check if already synced into DB by Drive file ID
        existing = await db.execute(
            select(Document).where(Document.drive_file_id == f["id"])
        )
        doc = existing.scalar_one_or_none()

        if not doc:
            # Sync new shared file into local DB
            owner_email = None
            if f.get("owners"):
                owner_email = f["owners"][0].get("emailAddress")

            doc = Document(
                title=f["name"],
                category="Shared With Me",
                drive_file_id=f["id"],
                web_view_link=f.get("webViewLink"),
                mime_type=f.get("mimeType"),
                drive_owner_email=owner_email,
                file_url=f.get("webViewLink", ""),
                is_shared_with_me=True,
                uploaded_by=current_user.id,
                file_size=int(f.get("size", 0)),
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)

        results.append(DocumentResponse.from_document(doc))

    return results


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a specific document by ID."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    return DocumentResponse.from_document(document)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a standard (non-Drive) document entry.
    Stores metadata only — file should be hosted externally.
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


@router.post(
    "/from-drive", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def create_document_from_drive(
    data: DriveDocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a Google Drive file as a document in the app.

    Sets sharing permissions on the Drive file automatically via the Drive API.
    The file is not copied — only its metadata and Drive reference are stored.

    References:
        permissions.create:
        https://developers.google.com/workspace/drive/api/reference/rest/v3/permissions/create
    """
    from app.services.google_drive import set_file_permission, DriveAuthError
    from app.config import get_settings

    settings = get_settings()

    try:
        permission_id = await set_file_permission(
            file_id=data.drive_file_id,
            user=current_user,
            db=db,
            role="reader",
            permission_type="domain",
            domain=getattr(settings, "school_domain", None),
        )
    except DriveAuthError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    document = Document(
        title=data.title,
        category=data.category,
        description=data.description,
        file_url=data.web_view_link,
        drive_file_id=data.drive_file_id,
        drive_permission_id=permission_id,
        web_view_link=data.web_view_link,
        mime_type=data.mime_type,
        uploaded_by=current_user.id,
    )

    db.add(document)
    await db.flush()

    await log_activity(
        db,
        title=f"Drive Document Added: {data.title}",
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
    """
    Delete a document. Admin only.

    For Drive documents, also revokes the sharing permission set at upload time.
    Does not delete the file from Google Drive itself.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Revoke Drive permission if this was a Drive document
    if document.drive_file_id and document.drive_permission_id:
        from app.services.google_drive import revoke_file_permission, DriveAuthError

        try:
            await revoke_file_permission(
                file_id=document.drive_file_id,
                permission_id=document.drive_permission_id,
                user=current_user,
                db=db,
            )
        except DriveAuthError:
            pass  # Don't block deletion if Drive revocation fails

    await log_activity(
        db,
        title=f"Document Deleted: {document.title}",
        author=current_user.name,
        action_type="delete",
        entity_type="document",
        entity_id=document_id,
    )

    await db.delete(document)
    await db.commit()

    return None
