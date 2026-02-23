"""
Kage Scan — Settings Model (Singleton)
Stores the user's AI provider configuration.
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Provider: 'openrouter' | 'copilot' | 'none'
    provider: Mapped[str] = mapped_column(String, default="none")

    # OpenRouter
    openrouter_key: Mapped[str | None] = mapped_column(String, nullable=True)
    openrouter_model: Mapped[str] = mapped_column(
        String, default="anthropic/claude-3.5-sonnet"
    )

    # GitHub Copilot
    copilot_access_token: Mapped[str | None] = mapped_column(String, nullable=True)
    copilot_token: Mapped[str | None] = mapped_column(String, nullable=True)
    copilot_token_expires: Mapped[int | None] = mapped_column(Integer, nullable=True)
    copilot_model: Mapped[str] = mapped_column(String, default="gpt-4o")

    def __repr__(self) -> str:
        return f"<Settings provider={self.provider}>"
