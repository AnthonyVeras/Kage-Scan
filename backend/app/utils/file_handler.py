"""
Kage Scan — File Upload & Extraction Handler
Handles ZIP extraction, image filtering, and natural-sort ordering.
"""

import asyncio
import os
import re
import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import UploadFile
from loguru import logger

from app.config import settings

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def _natural_sort_key(text: str) -> list:
    """
    Natural sort: 'page2' < 'page10' instead of lexicographic order.
    Splits text into numeric and non-numeric chunks for proper comparison.
    """
    return [
        int(chunk) if chunk.isdigit() else chunk.lower()
        for chunk in re.split(r"(\d+)", text)
    ]


def _is_image(filename: str) -> bool:
    """Check if file has a supported image extension."""
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def _get_project_dir(project_id: str) -> Path:
    """Return the project's storage directory, creating it if needed."""
    project_dir = settings.DATA_DIR / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


async def _save_upload(file: UploadFile, dest: Path) -> None:
    """Stream an UploadFile to disk asynchronously."""
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1024 * 64):  # 64 KB chunks
            await f.write(chunk)


def _extract_zip_sync(zip_path: Path, extract_to: Path) -> None:
    """Synchronous ZIP extraction — runs inside a thread pool."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            # Skip directories and hidden/system files
            basename = os.path.basename(member)
            if not basename or basename.startswith(".") or basename.startswith("__"):
                continue
            if _is_image(basename):
                # Extract flat (ignore internal folder structure)
                source = zf.open(member)
                target_path = extract_to / basename
                with open(target_path, "wb") as target:
                    shutil.copyfileobj(source, target)
                source.close()


def _collect_images(directory: Path) -> list[str]:
    """
    Collect all image files in a directory and return their
    relative paths (relative to DATA_DIR), naturally sorted.
    """
    images = []
    for entry in directory.iterdir():
        if entry.is_file() and _is_image(entry.name):
            # Store path relative to DATA_DIR for portability
            relative = entry.relative_to(settings.DATA_DIR)
            images.append(str(relative))

    # Natural sort by filename
    images.sort(key=lambda p: _natural_sort_key(os.path.basename(p)))
    return images


async def process_upload(file: UploadFile, project_id: str) -> list[str]:
    """
    Process an uploaded file (ZIP or single image).

    Returns:
        Naturally-sorted list of image paths (relative to DATA_DIR).

    Raises:
        ValueError: If no valid images are found.
        zipfile.BadZipFile: If the ZIP archive is corrupted.
    """
    project_dir = _get_project_dir(project_id)
    filename = file.filename or f"upload_{uuid4().hex[:8]}"

    logger.info(f"Processing upload '{filename}' for project {project_id}")

    if filename.lower().endswith(".zip"):
        # ── ZIP upload ─────────────────────────────────────────────
        zip_path = project_dir / filename
        await _save_upload(file, zip_path)

        # Extract in thread pool (zipfile is synchronous)
        await asyncio.to_thread(_extract_zip_sync, zip_path, project_dir)

        # Clean up the ZIP file after extraction
        zip_path.unlink(missing_ok=True)
        logger.info(f"ZIP extracted and deleted: {filename}")

    elif _is_image(filename):
        # ── Single image upload ────────────────────────────────────
        dest = project_dir / filename
        await _save_upload(file, dest)
        logger.info(f"Single image saved: {filename}")

    else:
        raise ValueError(f"Unsupported file type: {filename}")

    # Collect and sort all images in the project directory
    images = _collect_images(project_dir)

    if not images:
        raise ValueError("No valid images found after processing the upload.")

    logger.info(f"Found {len(images)} images for project {project_id}")
    return images
