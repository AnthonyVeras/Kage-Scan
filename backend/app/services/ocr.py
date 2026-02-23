"""
Kage Scan — OCR Service
Wraps manga-ocr (Japanese) with lazy singleton + asyncio.to_thread.
Supports EasyOCR fallback for Korean, Chinese, and English.
Falls back to pytesseract or placeholder when AI packages unavailable.
"""

import asyncio

from PIL import Image
from loguru import logger


class OcrEngine:
    """
    Extracts text from cropped manga panels.
    - Japanese: manga-ocr (specialized, higher accuracy)
    - Korean/Chinese/English: EasyOCR
    - Fallback: pytesseract or placeholder text
    Models are loaded lazily on first use (singleton pattern).
    """

    _instance: "OcrEngine | None" = None
    _manga_ocr = None
    _easyocr_readers: dict = {}
    _tesseract_available: bool | None = None
    _backend: str | None = None

    def __new__(cls) -> "OcrEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── Model Loaders ─────────────────────────────────────────────

    def _detect_backend(self) -> str:
        """Detect which OCR backend is available."""
        if self._backend is not None:
            return self._backend

        # Try manga-ocr first (best for Japanese manga)
        try:
            from manga_ocr import MangaOcr
            self._backend = "manga_ocr"
            logger.info("✅ OCR backend: manga-ocr available")
            return self._backend
        except ImportError:
            pass

        # Try EasyOCR
        try:
            import easyocr
            self._backend = "easyocr"
            logger.info("✅ OCR backend: EasyOCR available")
            return self._backend
        except ImportError:
            pass

        # Try pytesseract
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._backend = "tesseract"
            logger.info("✅ OCR backend: pytesseract available")
            return self._backend
        except Exception:
            pass

        # Placeholder fallback
        self._backend = "placeholder"
        logger.warning(
            "⚠️ No OCR engine available (manga-ocr, easyocr, pytesseract). "
            "Text blocks will have placeholder text. Install one of the OCR packages."
        )
        return self._backend

    def _load_manga_ocr(self) -> None:
        """Lazy-load manga-ocr model."""
        if self._manga_ocr is not None:
            return

        logger.info("⏳ Loading manga-ocr model (first run)...")
        from manga_ocr import MangaOcr
        self._manga_ocr = MangaOcr()
        logger.info("✅ manga-ocr loaded")

    def _load_easyocr(self, lang: str) -> None:
        """Lazy-load EasyOCR reader for a specific language."""
        if lang in self._easyocr_readers:
            return

        logger.info(f"⏳ Loading EasyOCR reader for '{lang}'...")
        import easyocr

        lang_map = {
            "ko": ["ko", "en"],
            "zh": ["ch_sim", "en"],
            "en": ["en"],
            "ja": ["ja", "en"],
        }
        ocr_langs = lang_map.get(lang, ["en"])

        self._easyocr_readers[lang] = easyocr.Reader(
            ocr_langs,
            gpu=False,
        )
        logger.info(f"✅ EasyOCR loaded for: {ocr_langs}")

    # ── Crop Helper ───────────────────────────────────────────────

    @staticmethod
    def _crop_bbox(image_path: str, bbox: dict) -> Image.Image:
        """Crop a bounding box region from an image."""
        img = Image.open(image_path).convert("RGB")
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]

        img_w, img_h = img.size
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)

        return img.crop((x1, y1, x2, y2))

    # ── OCR Runners ───────────────────────────────────────────────

    def _ocr_japanese_sync(self, image_path: str, bbox: dict) -> str:
        """Run manga-ocr on a cropped region."""
        self._load_manga_ocr()
        crop = self._crop_bbox(image_path, bbox)
        text = self._manga_ocr(crop)
        return text.strip()

    def _ocr_easyocr_sync(self, image_path: str, bbox: dict, lang: str) -> str:
        """Run EasyOCR on a cropped region."""
        self._load_easyocr(lang)
        import numpy as np
        crop = self._crop_bbox(image_path, bbox)
        crop_np = np.array(crop)

        reader = self._easyocr_readers[lang]
        results = reader.readtext(crop_np, detail=0, paragraph=True)
        text = " ".join(results) if results else ""
        return text.strip()

    def _ocr_tesseract_sync(self, image_path: str, bbox: dict, lang: str) -> str:
        """Run pytesseract on a cropped region."""
        import pytesseract
        crop = self._crop_bbox(image_path, bbox)

        lang_map = {
            "ja": "jpn",
            "ko": "kor",
            "zh": "chi_sim",
            "en": "eng",
        }
        tess_lang = lang_map.get(lang, "eng")

        try:
            text = pytesseract.image_to_string(crop, lang=tess_lang)
        except Exception:
            # If language data not available, try eng fallback
            text = pytesseract.image_to_string(crop, lang="eng")

        return text.strip()

    def _ocr_placeholder_sync(self, image_path: str, bbox: dict) -> str:
        """Placeholder when no OCR engine is available."""
        return f"[テキスト {bbox['x']},{bbox['y']}]"

    # ── Public Async API ──────────────────────────────────────────

    async def extract_text(
        self,
        image_path: str,
        bbox: dict,
        source_lang: str = "ja",
    ) -> str:
        """
        Async OCR extraction from a bounding box region.
        Automatically selects the best available backend.
        """
        try:
            backend = self._detect_backend()

            if backend == "manga_ocr" and source_lang == "ja":
                text = await asyncio.to_thread(
                    self._ocr_japanese_sync, image_path, bbox,
                )
            elif backend == "easyocr":
                text = await asyncio.to_thread(
                    self._ocr_easyocr_sync, image_path, bbox, source_lang,
                )
            elif backend == "tesseract":
                text = await asyncio.to_thread(
                    self._ocr_tesseract_sync, image_path, bbox, source_lang,
                )
            elif backend == "manga_ocr" and source_lang != "ja":
                # manga-ocr only supports Japanese, try easyocr for others
                try:
                    text = await asyncio.to_thread(
                        self._ocr_easyocr_sync, image_path, bbox, source_lang,
                    )
                except Exception:
                    text = await asyncio.to_thread(
                        self._ocr_placeholder_sync, image_path, bbox,
                    )
            else:
                # Placeholder fallback
                text = await asyncio.to_thread(
                    self._ocr_placeholder_sync, image_path, bbox,
                )

            if text:
                logger.debug(
                    f"OCR [{source_lang}/{backend}] at ({bbox['x']},{bbox['y']}): "
                    f"'{text[:50]}{'...' if len(text) > 50 else ''}'"
                )
            else:
                logger.debug(f"OCR returned empty at ({bbox['x']},{bbox['y']})")

            return text

        except Exception as e:
            logger.error(f"OCR failed at ({bbox['x']},{bbox['y']}): {e}")
            # Return placeholder so block still gets created
            return f"[テキスト {bbox['x']},{bbox['y']}]"
