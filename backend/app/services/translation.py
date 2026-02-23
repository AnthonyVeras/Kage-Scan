"""
Kage Scan — Translation Service
Dynamic LLM provider: reads config from SQLite (OpenRouter or GitHub Copilot).
Falls back to .env config if no DB settings exist.
"""

import time

import httpx
from loguru import logger

from app.config import settings as app_settings
from app.database import async_session


# ── System Prompt ─────────────────────────────────────────────────────
MANGA_TRANSLATOR_PROMPT = """\
Você é um tradutor profissional especializado em mangás, manhwas e webtoons.

## Regras obrigatórias:
1. Traduza APENAS o texto fornecido — NÃO adicione explicações, notas ou comentários.
2. Mantenha o TOM e a EMOÇÃO do original (humor, raiva, medo, tensão, etc.).
3. Adapte gírias, expressões idiomáticas e onomatopeias ao português brasileiro natural.
4. Use linguagem coloquial brasileira quando apropriado (contrações, gírias atuais).
5. Mantenha honoríficos japoneses/coreanos quando fizerem sentido cultural \
(ex: -san, -kun, -senpai, hyung, sunbae).
6. Para onomatopeias sem tradução direta, adapte ao som mais próximo em PT-BR.
7. Se o texto for uma interjeição ou efeito sonoro (SFX), traduza de forma curta e impactante.
8. NÃO traduza nomes próprios de personagens.
9. Retorne SOMENTE o texto traduzido, sem aspas, sem formatação extra.
"""


async def _get_provider_config() -> dict:
    """
    Load AI provider configuration from the database.
    Returns dict with keys: provider, api_key, model, api_base
    """
    from sqlalchemy import select
    from app.models.settings import Settings

    async with async_session() as db:
        result = await db.execute(select(Settings).where(Settings.id == 1))
        s = result.scalar_one_or_none()

    if not s or s.provider == "none":
        # Fallback to .env config
        return {
            "provider": "env",
            "api_key": app_settings.LLM_API_KEY,
            "model": app_settings.LLM_MODEL,
            "api_base": None,
        }

    if s.provider == "openrouter":
        return {
            "provider": "openrouter",
            "api_key": s.openrouter_key,
            "model": f"openrouter/{s.openrouter_model}",
            "api_base": "https://openrouter.ai/api/v1",
        }

    if s.provider == "copilot":
        # Check if inference token is expired
        token = s.copilot_token
        if not token or (s.copilot_token_expires and s.copilot_token_expires < int(time.time())):
            # Refresh the inference token
            token = await _refresh_copilot_token(s.copilot_access_token, db=None)

        return {
            "provider": "copilot",
            "api_key": token,
            "model": s.copilot_model,
            "api_base": "https://api.githubcopilot.com",
        }

    return {
        "provider": "none",
        "api_key": None,
        "model": "gpt-4o",
        "api_base": None,
    }


async def _refresh_copilot_token(access_token: str, db=None) -> str | None:
    """Refresh the Copilot inference token using the stored access token."""
    if not access_token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/copilot_internal/v2/token",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/json",
                },
            )

        if resp.status_code != 200:
            logger.error(f"Copilot token refresh failed: {resp.status_code}")
            return None

        data = resp.json()
        new_token = data.get("token")
        expires_at = data.get("expires_at", 0)

        # Update DB with new token
        from sqlalchemy import select, update
        from app.models.settings import Settings

        async with async_session() as session:
            await session.execute(
                update(Settings)
                .where(Settings.id == 1)
                .values(copilot_token=new_token, copilot_token_expires=expires_at)
            )
            await session.commit()

        logger.info("Copilot inference token refreshed successfully")
        return new_token

    except Exception as e:
        logger.error(f"Copilot token refresh error: {e}")
        return None


async def _call_llm(messages: list[dict], max_tokens: int = 500) -> str:
    """Make an LLM call using the configured provider."""
    config = await _get_provider_config()

    if not config["api_key"]:
        raise ValueError("No AI provider configured. Go to Settings to set up OpenRouter or Copilot.")

    try:
        import litellm

        kwargs = {
            "model": config["model"],
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }

        if config["api_key"]:
            kwargs["api_key"] = config["api_key"]
        if config["api_base"]:
            kwargs["api_base"] = config["api_base"]

        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"LLM call failed (provider={config['provider']}): {e}")
        raise


class Translator:
    """Async LLM-based translator with dynamic provider loading."""

    _instance: "Translator | None" = None

    def __new__(cls) -> "Translator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def translate_text(
        self,
        text: str,
        source_lang: str = "ja",
        target_lang: str = "pt-br",
    ) -> str:
        """Translate a single text block."""
        if not text or not text.strip():
            return ""

        lang_names = {
            "ja": "japonês", "ko": "coreano",
            "zh": "chinês", "en": "inglês",
            "pt-br": "português brasileiro",
        }
        src_name = lang_names.get(source_lang, source_lang)
        tgt_name = lang_names.get(target_lang, target_lang)

        user_prompt = (
            f"Traduza o seguinte texto de {src_name} para {tgt_name}:\n\n"
            f"{text}"
        )

        try:
            translated = await _call_llm([
                {"role": "system", "content": MANGA_TRANSLATOR_PROMPT},
                {"role": "user", "content": user_prompt},
            ])
            logger.debug(
                f"Translated [{source_lang}→{target_lang}]: "
                f"'{text[:30]}...' → '{translated[:30]}...'"
            )
            return translated
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return f"[ERRO] {text}"

    async def translate_batch(
        self,
        texts: list[str],
        source_lang: str = "ja",
        target_lang: str = "pt-br",
    ) -> list[str]:
        """Translate multiple text blocks in a single batched prompt."""
        if not texts:
            return []

        if len(texts) <= 2:
            return [
                await self.translate_text(t, source_lang, target_lang)
                for t in texts
            ]

        lang_names = {
            "ja": "japonês", "ko": "coreano",
            "zh": "chinês", "en": "inglês",
            "pt-br": "português brasileiro",
        }
        src_name = lang_names.get(source_lang, source_lang)
        tgt_name = lang_names.get(target_lang, target_lang)

        numbered = "\n".join(f"[{i+1}] {t}" for i, t in enumerate(texts))
        user_prompt = (
            f"Traduza os {len(texts)} trechos abaixo de {src_name} para {tgt_name}. "
            f"São falas de balões de um mangá/manhwa — mantenha a mesma numeração na resposta.\n"
            f"Retorne APENAS as traduções numeradas, uma por linha.\n\n"
            f"{numbered}"
        )

        try:
            raw = await _call_llm(
                [
                    {"role": "system", "content": MANGA_TRANSLATOR_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1500,
            )

            import re
            translations = []
            for i in range(len(texts)):
                pattern = rf"\[{i+1}\]\s*(.+)"
                match = re.search(pattern, raw)
                if match:
                    translations.append(match.group(1).strip())
                else:
                    translations.append(f"[ERRO] {texts[i]}")

            logger.info(f"Batch translated {len(translations)} blocks")
            return translations

        except Exception as e:
            logger.error(f"Batch translation failed: {e}")
            return [f"[ERRO] {t}" for t in texts]
