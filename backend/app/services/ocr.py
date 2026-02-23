"""
Kage Scan — OCR Service
Wraps manga-ocr (Japanese) with lazy singleton + asyncio.to_thread.
Supports EasyOCR fallback for Korean, Chinese, and English.
"""

import asyncio

from PIL import Image
from loguru import logger


class OcrEngine:
    """
    Extracts text from cropped manga panels.
    - Japanese: manga-ocr (specialized, higher accuracy)
    - Korean/Chinese/English: EasyOCR
    Models are loaded lazily on first use (singleton pattern).
    """

    _instance: "OcrEngine | None" = None
    _manga_ocr = None
    _easyocr_readers: dict = {}

    def __new__(cls) -> "OcrEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── Model Loaders ─────────────────────────────────────────────

    def _load_manga_ocr(self) -> None:
        """Lazy-load manga-ocr model."""
        if self._manga_ocr is not None:
            return

        logger.info("⏳ Loading manga-ocr model (first run)...")
        try:
            from manga_ocr import MangaOcr
            self._manga_ocr = MangaOcr()
            logger.info("✅ manga-ocr loaded")
        except ImportError:
            logger.error("manga-ocr not installed. pip install manga-ocr")
            raise

    def _load_easyocr(self, lang: str) -> None:
        """Lazy-load EasyOCR reader for a specific language."""
        if lang in self._easyocr_readers:
            return

        logger.info(f"⏳ Loading EasyOCR reader for '{lang}'...")
        try:
            import easyocr

            # Map our language codes to EasyOCR codes
            lang_map = {
                "ko": ["ko", "en"],
                "zh": ["ch_sim", "en"],
                "en": ["en"],
            }
            ocr_langs = lang_map.get(lang, ["en"])

            self._easyocr_readers[lang] = easyocr.Reader(
                ocr_langs,
                gpu=False,  # Set True if CUDA available
            )
            logger.info(f"✅ EasyOCR loaded for: {ocr_langs}")
        except ImportError:
            logger.error("easyocr not installed. pip install easyocr")
            raise

    # ── Crop Helper ───────────────────────────────────────────────

    @staticmethod
    def _crop_bbox(image_path: str, bbox: dict) -> Image.Image:
        """
        Crop a bounding box region from an image.
        bbox format: {"x": int, "y": int, "w": int, "h": int}
        """
        img = Image.open(image_path).convert("RGB")
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]

        # Clamp coordinates to image bounds
        img_w, img_h = img.size
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)

        crop = img.crop((x1, y1, x2, y2))
        return crop

    # ── OCR Runners ───────────────────────────────────────────────

    def _ocr_japanese_sync(self, image_path: str, bbox: dict) -> str:
        """Run manga-ocr on a cropped region (synchronous)."""
        self._load_manga_ocr()
        crop = self._crop_bbox(image_path, bbox)
        text = self._manga_ocr(crop)  # manga-ocr accepts PIL Image
        return text.strip()

    def _ocr_easyocr_sync(self, image_path: str, bbox: dict, lang: str) -> str:
        """Run EasyOCR on a cropped region (synchronous)."""
        self._load_easyocr(lang)

        import numpy as np
        crop = self._crop_bbox(image_path, bbox)
        crop_np = np.array(crop)

        reader = self._easyocr_readers[lang]
        results = reader.readtext(crop_np, detail=0, paragraph=True)
        text = " ".join(results) if results else ""
        return text.strip()

    # ── Public Async API ──────────────────────────────────────────

    async def extract_text(
        self,
        image_path: str,
        bbox: dict,
        source_lang: str = "ja",
    ) -> str:
        """
        Async OCR extraction from a bounding box region.

        Args:
            image_path: Absolute path to the full page image.
            bbox: Bounding box dict {"x", "y", "w", "h"}.
            source_lang: Source language code ("ja", "ko", "zh", "en").

        Returns:
            Extracted text string (may be empty if OCR fails).
        """
        try:
            if source_lang == "ja":
                text = await asyncio.to_thread(
                    self._ocr_japanese_sync, image_path, bbox,
                )
            else:
                text = await asyncio.to_thread(
                    self._ocr_easyocr_sync, image_path, bbox, source_lang,
                )

            if text:
                logger.debug(
                    f"OCR [{source_lang}] at ({bbox['x']},{bbox['y']}): "
                    f"'{text[:50]}{'...' if len(text) > 50 else ''}'"
                )
            else:
                logger.debug(f"OCR returned empty at ({bbox['x']},{bbox['y']})")

            return text

        except Exception as e:
            logger.error(f"OCR failed at ({bbox['x']},{bbox['y']}): {e}")
            return ""
