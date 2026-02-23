"""
Kage Scan — SQLAlchemy ORM Models
Hierarchy:  Project  →(1:N)→  Page  →(1:N)→  TextBlock
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    """Generate a new UUID4 string for primary keys."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Project ────────────────────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_language: Mapped[str] = mapped_column(String(10), default="ja")  # ja, ko, zh, en
    target_language: Mapped[str] = mapped_column(String(10), default="pt-br")
    status: Mapped[str] = mapped_column(String(20), default="processing")  # processing | ready | exported
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    pages: Mapped[list["Page"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Page.page_number",
    )

    def __repr__(self) -> str:
        return f"<Project {self.name!r} [{self.status}]>"


# ── Page ───────────────────────────────────────────────────────────────
class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Relative path on disk
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | ocr_done | translated | done

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="pages")
    text_blocks: Mapped[list["TextBlock"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Page #{self.page_number} '{self.filename}' [{self.status}]>"


# ── TextBlock ──────────────────────────────────────────────────────────
class TextBlock(Base):
    __tablename__ = "text_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)

    # Bounding box coordinates (top-left origin)
    box_x: Mapped[float] = mapped_column(Float, default=0.0)
    box_y: Mapped[float] = mapped_column(Float, default=0.0)
    box_width: Mapped[float] = mapped_column(Float, default=0.0)
    box_height: Mapped[float] = mapped_column(Float, default=0.0)

    # Text content
    text_original: Mapped[str | None] = mapped_column(Text, nullable=True)   # OCR result
    text_translated: Mapped[str | None] = mapped_column(Text, nullable=True)  # LLM translation

    # Typesetting
    font_size: Mapped[int] = mapped_column(Integer, default=18)
    font_family: Mapped[str] = mapped_column(String(100), default="Arial")
    text_color: Mapped[str] = mapped_column(String(20), default="#000000")
    text_alignment: Mapped[str] = mapped_column(String(10), default="center")  # left | center | right

    # Flags
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    page: Mapped["Page"] = relationship(back_populates="text_blocks")

    def __repr__(self) -> str:
        preview = (self.text_original or "")[:30]
        return f"<TextBlock ({self.box_x},{self.box_y}) '{preview}...'>"
