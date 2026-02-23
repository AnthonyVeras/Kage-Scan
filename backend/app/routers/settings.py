"""
Kage Scan — Settings Router
CRUD for AI provider configuration + GitHub Copilot Device Flow OAuth.
"""

import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.settings import Settings

router = APIRouter(prefix="/settings", tags=["Settings"])

# GitHub Copilot OAuth constants (public Client ID from VS Code extension)
COPILOT_CLIENT_ID = "01ab8ac9400c4e429b23"
GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"


# ═══════════════════════════════════════════════════════════════════════
#  Schemas
# ═══════════════════════════════════════════════════════════════════════

class SettingsResponse(BaseModel):
    model_config = {"from_attributes": True}
    provider: str
    openrouter_key: str | None = None
    openrouter_model: str
    copilot_model: str
    copilot_authenticated: bool = False


class SettingsUpdate(BaseModel):
    provider: str | None = None
    openrouter_key: str | None = None
    openrouter_model: str | None = None
    copilot_model: str | None = None


class DeviceCodeResponse(BaseModel):
    user_code: str
    verification_uri: str
    device_code: str
    expires_in: int
    interval: int


class PollRequest(BaseModel):
    device_code: str


class PollResponse(BaseModel):
    status: str  # 'pending' | 'authenticated' | 'error'
    message: str | None = None


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

async def _get_or_create_settings(db: AsyncSession) -> Settings:
    """Get the singleton Settings row, creating it if it doesn't exist."""
    result = await db.execute(select(Settings).where(Settings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = Settings(id=1)
        db.add(settings)
        await db.flush()
    return settings


# ═══════════════════════════════════════════════════════════════════════
#  Routes
# ═══════════════════════════════════════════════════════════════════════

@router.get("/", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Return the current AI provider configuration."""
    settings = await _get_or_create_settings(db)

    # Mask the API key for security (only show last 4 chars)
    masked_key = None
    if settings.openrouter_key:
        masked_key = "•" * 12 + settings.openrouter_key[-4:]

    return SettingsResponse(
        provider=settings.provider,
        openrouter_key=masked_key,
        openrouter_model=settings.openrouter_model,
        copilot_model=settings.copilot_model,
        copilot_authenticated=bool(settings.copilot_access_token),
    )


@router.patch("/", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update AI provider settings."""
    settings = await _get_or_create_settings(db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.flush()
    logger.info(f"Settings updated: {list(update_data.keys())}")

    masked_key = None
    if settings.openrouter_key:
        masked_key = "•" * 12 + settings.openrouter_key[-4:]

    return SettingsResponse(
        provider=settings.provider,
        openrouter_key=masked_key,
        openrouter_model=settings.openrouter_model,
        copilot_model=settings.copilot_model,
        copilot_authenticated=bool(settings.copilot_access_token),
    )


# ── GitHub Copilot Device Flow ────────────────────────────────────────

@router.post("/copilot/device-code", response_model=DeviceCodeResponse)
async def start_copilot_auth():
    """
    Step 1: Request a device code from GitHub.
    Returns user_code + verification_uri for the user to authorize in their browser.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_DEVICE_CODE_URL,
            data={"client_id": COPILOT_CLIENT_ID, "scope": "copilot"},
            headers={"Accept": "application/json"},
        )

    if resp.status_code != 200:
        logger.error(f"GitHub device code request failed: {resp.text}")
        raise HTTPException(
            status_code=502,
            detail="Failed to get device code from GitHub.",
        )

    data = resp.json()
    logger.info(f"Copilot device flow started — user_code: {data.get('user_code')}")

    return DeviceCodeResponse(
        user_code=data["user_code"],
        verification_uri=data["verification_uri"],
        device_code=data["device_code"],
        expires_in=data["expires_in"],
        interval=data.get("interval", 5),
    )


@router.post("/copilot/poll", response_model=PollResponse)
async def poll_copilot_auth(
    payload: PollRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Poll GitHub for the user's authorization.
    Once the user authorizes, exchanges the code for an access token,
    then fetches the Copilot inference token and stores both in the DB.
    """
    # Poll GitHub for auth status
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": COPILOT_CLIENT_ID,
                "device_code": payload.device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )

    if resp.status_code != 200:
        return PollResponse(status="error", message="GitHub token request failed.")

    data = resp.json()

    # Still waiting for user to authorize
    if "error" in data:
        error = data["error"]
        if error == "authorization_pending":
            return PollResponse(status="pending", message="Waiting for authorization...")
        elif error == "slow_down":
            return PollResponse(status="pending", message="Slow down, try again later.")
        elif error == "expired_token":
            return PollResponse(status="error", message="Device code expired. Start over.")
        elif error == "access_denied":
            return PollResponse(status="error", message="Access denied by user.")
        else:
            return PollResponse(status="error", message=f"GitHub error: {error}")

    # Got the access token
    access_token = data.get("access_token")
    if not access_token:
        return PollResponse(status="error", message="No access token in response.")

    logger.info("Copilot OAuth: access token received, fetching inference token...")

    # Step 3: Exchange access token for Copilot inference token
    async with httpx.AsyncClient() as client:
        copilot_resp = await client.get(
            COPILOT_TOKEN_URL,
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/json",
                "User-Agent": "GitHubCopilotChat/0.22.2",
                "Editor-Version": "vscode/1.96.0",
                "Editor-Plugin-Version": "copilot-chat/0.22.2",
            },
        )

    if copilot_resp.status_code != 200:
        logger.error(f"Copilot token exchange failed: {copilot_resp.text}")
        # Store access token anyway — can retry inference token later
        settings = await _get_or_create_settings(db)
        settings.copilot_access_token = access_token
        settings.provider = "copilot"
        await db.flush()
        return PollResponse(
            status="authenticated",
            message="Authenticated, but inference token fetch failed. Will retry on translation.",
        )

    copilot_data = copilot_resp.json()
    inference_token = copilot_data.get("token")
    expires_at = copilot_data.get("expires_at", 0)

    # Save everything to DB
    settings = await _get_or_create_settings(db)
    settings.copilot_access_token = access_token
    settings.copilot_token = inference_token
    settings.copilot_token_expires = expires_at
    settings.provider = "copilot"
    await db.flush()

    logger.info("Copilot fully authenticated and token stored!")
    return PollResponse(status="authenticated", message="Copilot connected successfully!")
