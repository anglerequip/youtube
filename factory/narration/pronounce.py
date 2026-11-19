"""Text normalisation and pronunciation: turns written script text into speakable text.

Provider-neutral: the output is plain words every TTS reads the same way. Order matters:
dictionary terms -> numbers with units -> plain numbers -> acronyms.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml
from num2words import num2words

from ..configuration import settings

DICT_PATH = settings.root / "content" / "pronunciation.yaml"


@lru_cache(maxsize=4)
def load_dictionary(path: str | None = None) -> dict:
    p = Path(path) if path else DICT_PATH
    if not p.exists():
        return {"terms": {}, "units": {}, "acronyms": {"say_as_word": [], "expand": {}}}
    return yaml.safe_load(p.read_text(encoding="utf-8"))


_NUM = r"(?P<num>-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)"


def say_number(s: str) -> str:
    s = s.replace(",", "")
    if re.fullmatch(r"(1[5-9]|20)\d\d", s):        # 1850, 2026: read as a year
        return num2words(int(s), to="year")
    val = float(s) if "." in s else int(s)
    return num2words(val).replace("-", " ")


_DECADES = {"00": "hundreds", "10": "tens", "20": "twenties", "30": "thirties", "40": "forties",
             "50": "fifties", "60": "sixties", "70": "seventies", "80": "eighties", "90": "nineties"}


def _decade(two: str) -> str:
    return _DECADES[two]


def _units_regex(units: dict) -> re.Pattern:
    # Longest symbols first so "m/s²" wins over "m".
    syms = sorted(units, key=len, reverse=True)
    alt = "|".join(re.escape(u) for u in syms)
    return re.compile(_NUM + r"\s?(?P<unit>" + alt + r")(?![A-Za-z0-9])")


def normalise(text: str, dictionary: dict | None = None) -> str:
    d = dictionary or load_dictionary()
    out = text

    # Dictionary respellings are swapped for placeholders so later steps (acronyms) leave them alone.
    protected: list[str] = []

    def protect(spoken: str) -> str:
        protected.append(spoken)
        return chr(0xE000 + len(protected) - 1)   # private-use char: untouched by later passes

    for term, spoken in sorted((d.get("terms") or {}).items(), key=lambda kv: -len(kv[0])):
        if re.match(r"\w", term):
            out = re.sub(rf"(?<!\w){re.escape(term)}(?!\w)", lambda _m, s=spoken: protect(s), out)
        else:
            out = out.replace(term, f" {protect(spoken)} ")

    # decades: "the 1990s" -> "the nineteen nineties"
    out = re.sub(r"\b(1[5-9]|20)(\d)0s\b",
                 lambda m: num2words(int(m.group(0)[:-1]), to="year").rsplit(" ", 1)[0] + " "
                 + _decade(m.group(0)[2:4]), out)

    units = d.get("units") or {}
    if units:
        def unit_sub(m):
            n = m.group("num")
            sing, plur = units[m.group("unit")]
            one = n.replace(",", "") in ("1", "1.0", "-1")
            return f"{say_number(n)} {sing if one else plur}"
        out = _units_regex(units).sub(unit_sub, out)

    out = re.sub(_NUM, lambda m: say_number(m.group("num")), out)

    acr = d.get("acronyms") or {}
    keep = set(acr.get("say_as_word") or [])
    expand = acr.get("expand") or {}

    def acronym_sub(m):
        w = m.group(0)
        if w in keep:
            return w.capitalize()
        return expand.get(w, " ".join(w))
    out = re.sub(r"\b[A-Z]{2,6}\b", acronym_sub, out)

    out = re.sub("[\ue000-\uf8ff]", lambda m: protected[ord(m.group(0)) - 0xE000], out)
    return re.sub(r"\s{2,}", " ", out).strip()
