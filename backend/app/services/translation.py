"""
Kage Scan — Translation Service
Wraps litellm for async LLM calls with a manga-specialized system prompt.
Supports BYOK (Bring Your Own Key) for any provider.
"""

from loguru import logger

from app.config import settings


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


class Translator:
    """
    Async LLM-based translator using litellm.
    Supports any provider configured via BYOK (OpenAI, Anthropic, Gemini, Ollama, etc.).
    """

    _instance: "Translator | None" = None

    def __new__(cls) -> "Translator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self.model = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY

    async def translate_text(
        self,
        text: str,
        source_lang: str = "ja",
        target_lang: str = "pt-br",
    ) -> str:
        """
        Translate a text block from source to target language using an LLM.

        Args:
            text: Original text extracted by OCR.
            source_lang: Source language code (ja, ko, zh, en).
            target_lang: Target language code (default: pt-br).

        Returns:
            Translated text string.
        """
        if not text or not text.strip():
            return ""

        # Build language context for the user prompt
        lang_names = {
            "ja": "japonês",
            "ko": "coreano",
            "zh": "chinês",
            "en": "inglês",
            "pt-br": "português brasileiro",
        }
        src_name = lang_names.get(source_lang, source_lang)
        tgt_name = lang_names.get(target_lang, target_lang)

        user_prompt = (
            f"Traduza o seguinte texto de {src_name} para {tgt_name}:\n\n"
            f"{text}"
        )

        try:
            import litellm

            # Configure API key if available
            if self.api_key:
                litellm.api_key = self.api_key

            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": MANGA_TRANSLATOR_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Low temp for consistent translations
                max_tokens=500,
            )

            translated = response.choices[0].message.content.strip()

            logger.debug(
                f"Translated [{source_lang}→{target_lang}]: "
                f"'{text[:30]}...' → '{translated[:30]}...'"
            )
            return translated

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Return original text as fallback so user can manually translate
            return f"[ERRO] {text}"

    async def translate_batch(
        self,
        texts: list[str],
        source_lang: str = "ja",
        target_lang: str = "pt-br",
    ) -> list[str]:
        """
        Translate multiple text blocks. Sends them in a single prompt
        to reduce API calls and improve contextual translation.
        """
        if not texts:
            return []

        # For small batches, translate individually for accuracy
        if len(texts) <= 2:
            results = []
            for t in texts:
                translated = await self.translate_text(t, source_lang, target_lang)
                results.append(translated)
            return results

        # ── Batch: combine texts with delimiters for context ──────
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
            import litellm

            if self.api_key:
                litellm.api_key = self.api_key

            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": MANGA_TRANSLATOR_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )

            raw = response.choices[0].message.content.strip()

            # Parse numbered lines: "[1] translated text"
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
