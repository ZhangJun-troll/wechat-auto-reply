"""OCR模块 - PaddleOCR优先，自动降级Tesseract"""
import io
from typing import List, Dict, Optional
from PIL import Image
from config import cfg

_ocr_backend = None  # 'paddle' or 'tesseract'


def _init_ocr():
    global _ocr_backend
    if _ocr_backend is not None:
        return _ocr_backend

    # 先试PaddleOCR
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(lang="ch")
        _ocr_backend = "paddle"
        cfg.log("OCR引擎: PaddleOCR")
        return _ocr_backend
    except Exception as e:
        cfg.log(f"PaddleOCR不可用({e})，降级到Tesseract", "WARN")

    # 降级Tesseract
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        _ocr_backend = "tesseract"
        cfg.log("OCR引擎: Tesseract")
        return _ocr_backend
    except Exception as e:
        cfg.log(f"Tesseract也不可用: {e}", "ERROR")
        _ocr_backend = None
        return None


def ocr_image(image: Image.Image) -> List[Dict]:
    """统一OCR接口，返回 [{"text": str, "x": float, "y": float, "w": float, "h": float}]"""
    backend = _init_ocr()
    if backend == "paddle":
        return _ocr_paddle(image)
    elif backend == "tesseract":
        return _ocr_tesseract(image)
    return []


def _ocr_paddle(image: Image.Image) -> List[Dict]:
    import numpy as np
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(lang="ch")
    result = ocr.ocr(np.array(image), cls=True)
    boxes = []
    if result and result[0]:
        for line in result[0]:
            coords = line[0]
            text, conf = line[1]
            xs = [p[0] for p in coords]
            ys = [p[1] for p in coords]
            boxes.append({
                "text": text.strip(),
                "x": sum(xs)/4, "y": sum(ys)/4,
                "w": max(xs)-min(xs), "h": max(ys)-min(ys),
                "conf": conf
            })
    boxes.sort(key=lambda b: b["y"])
    return boxes


def _ocr_tesseract(image: Image.Image) -> List[Dict]:
    import pytesseract
    data = pytesseract.image_to_data(image, lang="chi_sim+eng", output_type=pytesseract.Output.DICT)
    boxes = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        conf = int(data["conf"][i])
        if not text or conf < 30:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        boxes.append({"text": text, "x": x+w/2, "y": y+h/2, "w": w, "h": h, "conf": conf/100})
    boxes.sort(key=lambda b: b["y"])
    return boxes


# 保持向后兼容
FILTER_PATTERNS = [
    r"^\d{1,2}:\d{2}$", r"^\d{4}[/\-]\d{1,2}[/\-]\d{1,2}",
    r"^(今天|昨天|星期[一二三四五六日天])$", r"^\[.+\]$",
    r"^你已添加了", r"^以上是打招呼的内容",
    r"^\[小程序\]", r"^\[语音\]", r"^\[视频\]", r"^\[文件\]", r"^\[位置\]",
    r"^对方已读", r"^消息已发出", r"^-+$", r"^\d+条新消息$",
    r"^(拍了拍|撤回了一条消息)",
]

import re
FILTER_RE = [re.compile(p) for p in FILTER_PATTERNS]


class OCREngine:
    def __init__(self):
        self._last_messages: List[Dict] = []

    def parse_chat(self, image: Image.Image) -> List[Dict]:
        width, height = image.size
        boxes = ocr_image(image)
        # 过滤
        filtered = [b for b in boxes if b["text"] and not any(p.search(b["text"]) for p in FILTER_RE)]
        # 分组
        center_x = width / 2
        messages = []
        GROUP_THRESHOLD = 25
        current_group = [filtered[0]] if filtered else []
        for b in filtered[1:]:
            if b["y"] - current_group[-1]["y"] < GROUP_THRESHOLD:
                current_group.append(b)
            else:
                messages.append(current_group)
                current_group = [b]
        if current_group:
            messages.append(current_group)

        result = []
        for group in messages:
            group.sort(key=lambda b: b["y"])
            full_text = " ".join(b["text"] for b in group)
            avg_x = sum(b["x"] for b in group) / len(group)
            sender = "me" if avg_x > center_x else "other"
            result.append({"text": full_text, "sender": sender, "y_pos": group[0]["y"], "x_pos": avg_x})

        self._last_messages = result
        cfg.log(f"OCR解析: {len(boxes)}文字框 → {len(result)}条消息 (引擎: {_ocr_backend})")
        return result

    def get_context(self, max_rounds: int = 8) -> str:
        if not self._last_messages:
            return "（未检测到聊天消息）"
        recent = self._last_messages[-max_rounds*2:]
        return "\n".join(f"{'【我方消息】' if m['sender']=='me' else '【对方消息】'}{m['text']}" for m in recent)

    def get_latest_sender(self) -> Optional[str]:
        return self._last_messages[-1]["sender"] if self._last_messages else None

    def get_last_message_hash(self) -> str:
        if self._last_messages:
            last = self._last_messages[-1]
            return f"{last['sender']}:{last['text'][:50]}"
        return ""


ocr_engine = OCREngine()
