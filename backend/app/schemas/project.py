"""
Kage Scan — Pydantic Schemas (Input / Output Validation)
Follows the Create / Update / Response pattern for each entity.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
#  TextBlock Schemas
# ═══════════════════════════════════════════════════════════════════════

class TextBlockCreate(BaseModel):
    """Used when the pipeline creates a detected text block."""
    page_id: str
    box_x: float = 0.0
    box_y: float = 0.0
    box_width: float = 0.0
    box_height: float = 0.0
    text_original: str | None = None
    text_translated: str | None = None
    font_size: int = 18


class TextBlockUpdate(BaseModel):
    """Used when the user edits a text block in the review UI."""
    text_original: str | None = None
    text_translated: str | None = None
    box_x: float | None = None
    box_y: float | None = None
    box_width: float | None = None
    box_height: float | None = None
    font_size: int | None = None
    font_family: str | None = None
    text_color: str | None = None
    text_alignment: str | None = None
    is_edited: bool | None = None


class TextBlockResponse(BaseModel):
    """Returned to the frontend with full block data."""
    model_config = {"from_attributes": True}

    id: str
    page_id: str
    box_x: float
    box_y: float
    box_width: float
    box_height: float
    text_original: str | None = None
    text_translated: str | None = None
    font_size: int
    font_family: str
    text_color: str
    text_alignment: str
    is_edited: bool


# ═══════════════════════════════════════════════════════════════════════
#  Page Schemas
# ═══════════════════════════════════════════════════════════════════════

class PageCreate(BaseModel):
    """Used internally when extracting pages from a ZIP upload."""
    project_id: str
    filename: str
    page_number: int = 0
    image_path: str


class PageResponse(BaseModel):
    """Returned to the frontend — includes nested text blocks."""
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    filename: str
    page_number: int
    image_path: str
    status: str
    text_blocks: list[TextBlockResponse] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
#  Project Schemas
# ═══════════════════════════════════════════════════════════════════════

class ProjectCreate(BaseModel):
    """Sent by the user when starting a new project."""
    name: str = Field(..., min_length=1, max_length=255)
    source_language: str = Field(default="ja", pattern=r"^(ja|ko|zh|en)$")
    target_language: str = Field(default="pt-br")


class ProjectResponse(BaseModel):
    """Full project view — includes nested pages (which include text blocks)."""
    model_config = {"from_attributes": True}

    id: str
    name: str
    source_language: str
    target_language: str
    status: str
    created_at: datetime
    updated_at: datetime
    pages: list[PageResponse] = Field(default_factory=list)


class ProjectListItem(BaseModel):
    """Lightweight version for listing projects (without nested data)."""
    model_config = {"from_attributes": True}

    id: str
    name: str
    source_language: str
    target_language: str
    status: str
    created_at: datetime
    page_count: int = 0
