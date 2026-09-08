from pathlib import Path
import re

import fitz

FONT_MAP = {
    "helvetica": "helv", "arial": "helv", "calibri": "helv",
    "helvetica-bold": "hebo", "arial-bold": "hebo", "calibri-bold": "hebo",
    "helvetica-oblique": "heit", "arial-italic": "heit",
    "helvetica-boldoblique": "hebi", "arial-bolditalic": "hebi",
    "times": "tiro", "timesnewroman": "tiro", "timesnewromanpsmt": "tiro",
    "times-bold": "tibo", "timesnewroman-bold": "tibo", "timesnewromanps-boldmt": "tibo",
    "times-italic": "tiit", "timesnewroman-italic": "tiit", "timesnewromanps-italicmt": "tiit",
    "times-bolditalic": "tibi",
    "courier": "cour", "couriernew": "cour",
    "courier-bold": "cobo", "couriernew-bold": "cobo",
    "garamond": "tiro", "georgia": "tiro", "palatino": "tiro",
    "cambria": "tiro", "bookantiqua": "tiro",
}


def map_font(pdf_font_name: str) -> str:
    """Map a PDF font name to the closest base-14 font PyMuPDF can write with."""
    if not pdf_font_name:
        return "helv"
    name = re.sub(r"^[A-Z]{6}\+", "", pdf_font_name)
    key = name.lower().replace(" ", "").replace("-", "")

    if key in FONT_MAP:
        return FONT_MAP[key]
    for map_key, base14 in FONT_MAP.items():
        if map_key in key or key in map_key:
            return base14

    base14_names = {"helv", "hebo", "heit", "hebi", "tiro", "tibo", "tiit", "tibi",
                    "cour", "cobo", "coob", "cobi", "symb", "zadb"}
    if pdf_font_name.lower() in base14_names:
        return pdf_font_name
    return "helv"


def color_int_to_tuple(c: int) -> tuple[float, float, float]:
    """Convert integer RGB color from PDF text span to (r, g, b) float tuple."""
    return (((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0, (c & 0xFF) / 255.0)


class SpanStyle:
    """Style properties for one type of text element."""
    __slots__ = ("font_raw", "font", "font_obj", "size", "color", "x", "flags")

    def __init__(self, font_raw: str, font_name: str, font_obj: fitz.Font, size: float, color: int, x: float, flags: int = 0):
        self.font_raw = font_raw
        self.font = font_name
        self.font_obj = font_obj
        self.size = size
        self.color = color_int_to_tuple(color)
        self.x = x
        self.flags = flags

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & (1 << 4)) or "bold" in self.font_raw.lower()


def setup_page_fonts(doc, page) -> dict[str, tuple[str, fitz.Font]]:
    """Extract and register embedded fonts from the PDF page so PyMuPDF writes with true fonts."""
    font_registry: dict[str, tuple[str, fitz.Font]] = {}
    if not doc:
        return font_registry

    try:
        page_fonts = page.get_fonts()
        for idx, f_info in enumerate(page_fonts):
            xref = f_info[0]
            basefont = f_info[3]
            clean_name = re.sub(r"^[A-Z]{6}\+", "", basefont)

            try:
                fname, ext, ftype, buffer = doc.extract_font(xref)
                if buffer and len(buffer) > 0:
                    reg_name = f"emb_{xref}_{idx}"
                    try:
                        font_obj = fitz.Font(fontname=reg_name, fontbuffer=buffer)
                        page.insert_font(fontname=reg_name, fontbuffer=buffer)

                        val = (reg_name, font_obj)
                        font_registry[basefont] = val
                        font_registry[clean_name] = val
                        font_registry[clean_name.lower()] = val
                        font_registry[clean_name.lower().replace("-", "").replace(" ", "")] = val
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

    return font_registry


def resolve_font(
    font_registry: dict[str, tuple[str, fitz.Font]],
    font_raw: str,
    is_bold: bool = False,
) -> tuple[str, fitz.Font]:
    """Resolve font name to registered embedded font, system font, or closest base-14 font."""
    clean = re.sub(r"^[A-Z]{6}\+", "", font_raw)
    key = clean.lower().replace("-", "").replace(" ", "")

    # 1. Direct match in embedded font registry
    for candidate in (font_raw, clean, clean.lower(), key):
        if candidate in font_registry:
            return font_registry[candidate]

    # 2. Partial match in embedded registry
    for reg_key, val in font_registry.items():
        if key in reg_key or reg_key in key:
            if is_bold and ("bold" in reg_key or "bd" in reg_key):
                return val
            elif not is_bold and "bold" not in reg_key:
                return val
    if font_registry:
        for reg_key, val in font_registry.items():
            if key in reg_key or reg_key in key:
                return val

    # 3. System fonts fallback (Windows)
    win_fonts = Path("C:/Windows/Fonts")
    if win_fonts.exists():
        candidates = []
        if is_bold:
            candidates.extend([f"{key}bd.ttf", f"{key}b.ttf", f"{key}-bold.ttf", f"{key}bold.ttf"])
        candidates.extend([f"{key}.ttf", f"{key}.otf", f"{clean.lower()}.ttf"])
        for cand in candidates:
            p = win_fonts / cand
            if p.exists():
                try:
                    buf = p.read_bytes()
                    reg = f"sys_{key}_{'b' if is_bold else 'r'}"
                    font_obj = fitz.Font(fontname=reg, fontbuffer=buf)
                    return (reg, font_obj)
                except Exception:
                    pass

    # 4. Standard base-14 fallback
    b14 = map_font(font_raw)
    if is_bold and b14 == "helv":
        b14 = "hebo"
    elif is_bold and b14 == "tiro":
        b14 = "tibo"
    return (b14, fitz.Font(b14))


def wrap_to_pixel_width(
    text: str,
    font_obj: fitz.Font,
    font_size: float,
    max_w: float,
) -> list[str]:
    """Wrap words to fill line width up to max_w points using real glyph metrics."""
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    curr: list[str] = []
    for w in words:
        trial = " ".join(curr + [w])
        try:
            width = font_obj.text_length(trial, fontsize=font_size)
        except Exception:
            width = len(trial) * font_size * 0.50
        if width <= max_w:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
                curr = [w]
            else:
                lines.append(w)
                curr = []
    if curr:
        lines.append(" ".join(curr))
    return lines
