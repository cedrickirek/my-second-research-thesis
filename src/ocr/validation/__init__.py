"""OCR output validation against manually corrected ground truth.

Public surface:
    from src.ocr.validation.compare import build_report
    from src.ocr.validation import metrics
"""

from . import metrics

__all__ = ["metrics"]
