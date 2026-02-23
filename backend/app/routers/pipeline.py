"""
Kage Scan — Pipeline Router
Orchestrates the Detect → OCR → Translate flow as a background task.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session, get_db
from app.models.project import Page, Project, TextBlock
from app.services.detection import TextDetector
from app.services.ocr import OcrEngine
from app.services.translation import Translator
from app.config import settings

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

# ── Singleton service instances ───────────────────────────────────────
detector = TextDetector()
ocr_engine = OcrEngine()
translator = Translator()


# ── Background Task ───────────────────────────────────────────────────
async def process_project_task(project_id: str) -> None:
    """
    Full pipeline: Detection → OCR → Translation for every page of a project.
    Runs as a background task — uses its own DB session.
    """
    async with async_session() as db:
        try:
            # ── 1. Load project with pages ────────────────────────
            result = await db.execute(
                select(Project)
                .where(Project.id == project_id)
                .options(selectinload(Project.pages))
            )
            project = result.scalar_one_or_none()

            if not project:
                logger.error(f"Pipeline: Project {project_id} not found")
                return

            project.status = "processing"
            await db.commit()

            logger.info(
                f"🔄 Pipeline started for '{project.name}' "
                f"({len(project.pages)} pages, {project.source_language}→{project.target_language})"
            )

            # ── 2. Process each page ──────────────────────────────
            for page in sorted(project.pages, key=lambda p: p.page_number):
                await _process_page(
                    db=db,
                    page=page,
                    source_lang=project.source_language,
                    target_lang=project.target_language,
                )

            # ── 3. Mark project as ready ──────────────────────────
            project.status = "ready"
            await db.commit()

            logger.info(f"✅ Pipeline complete for '{project.name}'")

        except Exception as e:
            logger.error(f"❌ Pipeline failed for project {project_id}: {e}")
            # Try to mark as error state
            try:
                project.status = "error"
                await db.commit()
            except Exception:
                await db.rollback()


async def _process_page(
    db: AsyncSession,
    page: Page,
    source_lang: str,
    target_lang: str,
) -> None:
    """Process a single page: detect → OCR → translate all text blocks."""

    image_full_path = str(settings.DATA_DIR / page.image_path)
    logger.info(f"  📄 Processing page {page.page_number}: {page.filename}")

    page.status = "processing"
    await db.commit()

    # ── Step A: Text Detection ────────────────────────────────────
    try:
        bboxes = await detector.detect(image_full_path)
    except Exception as e:
        logger.error(f"  Detection failed for {page.filename}: {e}")
        bboxes = []

    if not bboxes:
        logger.warning(f"  No text regions found in {page.filename}")
        page.status = "done"
        await db.commit()
        return

    logger.info(f"  Found {len(bboxes)} text regions")

    # ── Step B: OCR each region ───────────────────────────────────
    ocr_results: list[tuple[dict, str]] = []
    for bbox in bboxes:
        text = await ocr_engine.extract_text(
            image_path=image_full_path,
            bbox=bbox,
            source_lang=source_lang,
        )
        if text:  # Only keep blocks that yielded text
            ocr_results.append((bbox, text))

    if not ocr_results:
        logger.warning(f"  OCR returned no text for {page.filename}")
        page.status = "done"
        await db.commit()
        return

    logger.info(f"  OCR extracted text from {len(ocr_results)} regions")
    page.status = "ocr_done"
    await db.commit()

    # ── Step C: Translate ─────────────────────────────────────────
    original_texts = [text for _, text in ocr_results]

    try:
        translated_texts = await translator.translate_batch(
            texts=original_texts,
            source_lang=source_lang,
            target_lang=target_lang,
        )
    except Exception as e:
        logger.error(f"  Translation failed for {page.filename}: {e}")
        translated_texts = [f"[ERRO] {t}" for t in original_texts]

    # ── Step D: Save TextBlock records ────────────────────────────
    for (bbox, original), translated in zip(ocr_results, translated_texts):
        block = TextBlock(
            page_id=page.id,
            box_x=bbox["x"],
            box_y=bbox["y"],
            box_width=bbox["w"],
            box_height=bbox["h"],
            text_original=original,
            text_translated=translated,
        )
        db.add(block)

    page.status = "translated"
    await db.commit()

    logger.info(
        f"  ✅ Page {page.page_number} done: "
        f"{len(ocr_results)} blocks saved"
    )


# ── Routes ────────────────────────────────────────────────────────────

@router.post("/{project_id}/start", status_code=202)
async def start_pipeline(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Kick off the full Detect → OCR → Translate pipeline for a project.
    Returns immediately with 202 Accepted — work runs in background.
    """
    # Validate project exists
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project.status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Pipeline is already running for this project.",
        )

    # Queue background task
    background_tasks.add_task(process_project_task, project_id)

    logger.info(f"Pipeline queued for project '{project.name}'")
    return {
        "status": "accepted",
        "project_id": project_id,
        "message": f"Pipeline started for '{project.name}'.",
    }


@router.get("/{project_id}/status")
async def pipeline_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check the current status of a project's pipeline processing."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.pages))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    page_statuses = {}
    for page in project.pages:
        status = page.status
        page_statuses[status] = page_statuses.get(status, 0) + 1

    return {
        "project_id": project.id,
        "project_status": project.status,
        "total_pages": len(project.pages),
        "page_statuses": page_statuses,
    }

