"""
Kage Scan — Project CRUD Routes
POST /   → Create project + upload images
GET  /   → List all projects
GET  /{id} → Get project details (with pages & text blocks)
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.project import Page, Project, TextBlock
from app.schemas.project import ProjectListItem, ProjectResponse, TextBlockResponse, TextBlockUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])


# ── POST / — Create Project + Upload ──────────────────────────────────
@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    name: str = Form(..., min_length=1, max_length=255),
    source_language: str = Form(default="ja"),
    target_language: str = Form(default="pt-br"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Create a new translation project from a ZIP or image upload."""
    # Lazy import to avoid circular deps at module level
    from app.utils.file_handler import process_upload

    # 1. Create the project record
    project = Project(
        name=name,
        source_language=source_language,
        target_language=target_language,
        status="processing",
    )
    db.add(project)
    await db.flush()  # Flush to get the generated UUID

    logger.info(f"Created project '{name}' (id={project.id})")

    # 2. Process the uploaded file (ZIP or image)
    try:
        image_paths = await process_upload(file, project.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process uploaded file.")

    # 3. Create Page records for each extracted image
    for idx, img_path in enumerate(image_paths):
        filename = img_path.split("/")[-1]  # Get basename from relative path
        page = Page(
            project_id=project.id,
            filename=filename,
            page_number=idx + 1,
            image_path=img_path,
            status="pending",
        )
        db.add(page)

    # Update project status
    project.status = "ready"
    await db.flush()

    logger.info(f"Project '{name}': {len(image_paths)} pages registered")

    # 4. Re-query with relationships loaded for the response
    result = await db.execute(
        select(Project)
        .where(Project.id == project.id)
        .options(
            selectinload(Project.pages).selectinload(Page.text_blocks)
        )
    )
    project_full = result.scalar_one()

    return project_full


# ── GET / — List All Projects ─────────────────────────────────────────
@router.get("/", response_model=list[ProjectListItem])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """Return all projects, newest first, with page counts."""

    # Subquery for page count
    page_count_subq = (
        select(
            Page.project_id,
            func.count(Page.id).label("page_count"),
        )
        .group_by(Page.project_id)
        .subquery()
    )

    result = await db.execute(
        select(
            Project,
            func.coalesce(page_count_subq.c.page_count, 0).label("page_count"),
        )
        .outerjoin(page_count_subq, Project.id == page_count_subq.c.project_id)
        .order_by(Project.created_at.desc())
    )

    items = []
    for row in result.all():
        project = row[0]
        count = row[1]
        item = ProjectListItem.model_validate(project)
        item.page_count = count
        items.append(item)

    return items


# ── GET /{project_id} — Project Detail ────────────────────────────────
@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """
    Return a single project with all its pages and text blocks.
    Uses selectinload to eagerly load relationships (avoids N+1).
    """
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.pages).selectinload(Page.text_blocks)
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    return project


# ── PATCH /{project_id}/blocks/{block_id} — Update Text Block ─────────
@router.patch(
    "/{project_id}/blocks/{block_id}",
    response_model=TextBlockResponse,
)
async def update_text_block(
    project_id: str,
    block_id: str,
    payload: TextBlockUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Partially update a text block's fields.
    Only the fields sent in the request body will be updated.
    Always marks the block as `is_edited = True`.
    """
    # Verify block exists and belongs to this project
    result = await db.execute(
        select(TextBlock)
        .join(Page, TextBlock.page_id == Page.id)
        .where(Page.project_id == project_id, TextBlock.id == block_id)
    )
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(
            status_code=404,
            detail=f"TextBlock '{block_id}' not found in project '{project_id}'.",
        )

    # Apply only the fields the user sent
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(block, field, value)

    # Always mark as edited
    block.is_edited = True
    await db.flush()

    logger.info(f"TextBlock {block_id} updated: {list(update_data.keys())}")

    return block
