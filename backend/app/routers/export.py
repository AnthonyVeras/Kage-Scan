"""
Kage Scan — Export Router
Renders final images (inpaint + typeset) and serves them as a downloadable ZIP.
"""

import os
import shutil
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.project import Page, Project, TextBlock
from app.services.inpainting import Inpainter
from app.services.typesetting import Typesetter

router = APIRouter(prefix="/export", tags=["Export"])

# ── Singleton service instances ───────────────────────────────────────
inpainter = Inpainter()
typesetter = Typesetter()


@router.get("/projects/{project_id}/export")
async def export_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Render final translated images and return them as a ZIP download.

    Pipeline per page:
    1. Inpaint (erase original text using masks from bboxes)
    2. Typeset (draw translated text onto cleaned image)
    3. Package all rendered pages into a ZIP

    Returns:
        FileResponse with the ZIP archive.
    """
    # ── 1. Load project with pages + text blocks ──────────────────
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.pages).selectinload(Page.text_blocks)
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if not project.pages:
        raise HTTPException(status_code=400, detail="Project has no pages to export.")

    logger.info(f"📦 Starting export for '{project.name}' ({len(project.pages)} pages)")

    # ── 2. Create export directory ────────────────────────────────
    export_dir = settings.DATA_DIR / "exports" / project_id
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    # ── 3. Process each page ──────────────────────────────────────
    sorted_pages = sorted(project.pages, key=lambda p: p.page_number)

    for page in sorted_pages:
        try:
            await _render_page(page, export_dir)
        except Exception as e:
            logger.error(f"Export failed for page {page.filename}: {e}")
            # Continue with other pages — don't fail the entire export
            continue

    # ── 4. Verify we have rendered images ─────────────────────────
    rendered_files = sorted(
        [f for f in export_dir.iterdir() if f.is_file()],
        key=lambda f: f.name,
    )

    if not rendered_files:
        raise HTTPException(
            status_code=500,
            detail="Export produced no rendered images.",
        )

    # ── 5. Create ZIP ─────────────────────────────────────────────
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in project.name)
    zip_filename = f"{safe_name}_translated.zip"
    zip_path = settings.DATA_DIR / "exports" / zip_filename

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rendered_file in rendered_files:
            zf.write(rendered_file, arcname=rendered_file.name)

    logger.info(f"✅ Export ZIP created: {zip_filename} ({len(rendered_files)} pages)")

    # ── 6. Update project status ──────────────────────────────────
    project.status = "exported"
    await db.flush()

    # ── 7. Return the ZIP ─────────────────────────────────────────
    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=zip_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
        },
    )


async def _render_page(page: Page, export_dir: Path) -> None:
    """Render a single page: inpaint → typeset → save to export dir."""

    image_full_path = str(settings.DATA_DIR / page.image_path)

    # Collect bboxes and text blocks for this page
    bboxes = []
    block_dicts = []

    for block in page.text_blocks:
        bbox = {
            "x": block.box_x,
            "y": block.box_y,
            "w": block.box_width,
            "h": block.box_height,
        }
        bboxes.append(bbox)

        block_dicts.append({
            "text_translated": block.text_translated or "",
            "box_x": block.box_x,
            "box_y": block.box_y,
            "box_width": block.box_width,
            "box_height": block.box_height,
            "font_size": block.font_size,
            "font_family": block.font_family,
            "text_color": block.text_color,
            "text_alignment": block.text_alignment,
        })

    # ── Step A: Inpainting (erase original text) ──────────────────
    cleaned_path = await inpainter.clean_image(image_full_path, bboxes)

    # ── Step B: Typesetting (draw translated text) ────────────────
    # Output file keeps the page number in the name for ordering
    output_name = f"{page.page_number:04d}_{page.filename}"
    output_path = str(export_dir / output_name)

    if block_dicts:
        await typesetter.render_text(cleaned_path, block_dicts, output_path)
    else:
        # No text blocks — just copy the cleaned image
        shutil.copy2(cleaned_path, output_path)

    # ── Cleanup: remove intermediate cleaned image ────────────────
    if cleaned_path != image_full_path and os.path.exists(cleaned_path):
        os.remove(cleaned_path)

    logger.info(f"  📄 Page {page.page_number} rendered → {output_name}")
