"""Padapāṭha (sandhi-vivaraṇa) for a single word, in Harsha's format:
sandhi junctions become spaces, compound members are joined by hyphens (समास-अवयवाः).

Order of authority: Harsha's own pairs (अध्ययन-सहकारी) → ByT5-Sanskrit model output → none.
"""
import difflib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDCH = "ऀ-ॣ॰-ॿ‌‍"  # Devanagari letters and signs; not । ॥ or digits
PUNCT = re.compile(f"([^{WORDCH}]+)")
DEVA = re.compile(f"[{WORDCH}]")
EDGES = re.compile(f"^[^{WORDCH}]+|[^{WORDCH}]+$")
SUFFIX_LEMMAS = {"tā", "tva", "tara", "tama", "vat", "mat", "maya", "tas", "kṛta"}


def fullness(p):
    return p.count("-") + p.count(" ")


class Pada:
    def __init__(self):
        self.src = {}
        pairs = {}
        for f in ["build/harsha-lane-pairs.json", "build/harsha-bhashya-pairs.json"]:
            path = ROOT / f
            if path.exists():
                for s, cands in json.loads(path.read_text(encoding="utf-8")).items():
                    pairs.setdefault(s, Counter()).update(cands)
        # A pair whose sandhi form carries punctuation also serves the bare word.
        for s, c in list(pairs.items()):
            bare = EDGES.sub("", s)
            if bare != s and bare and not PUNCT.search(bare):
                for p, k in c.items():
                    pairs.setdefault(bare, Counter())[EDGES.sub("", p)] += k
        # Where Harsha analysed the same word two ways, keep the fuller analysis.
        self.harsha = {s: max(c, key=lambda p: (fullness(p), c[p])) for s, c in pairs.items()}
        self.model = {}
        mo = ROOT / "build/model-out.jsonl"
        if mo.exists():
            from indic_transliteration import sanscript  # noqa: F401  (only for model output)
            for line in mo.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                p = model_pada(r)
                if p:
                    self.model[r["w"]] = p
        self.stats = Counter()

    def word(self, w):
        if w in self.harsha:
            self.stats["harsha"] += 1
            return self.harsha[w], "h"
        if w in self.model:
            p = self.model[w]
            if p == w:
                self.stats["same"] += 1
                return None, None
            self.stats["model"] += 1
            return p, "m"
        self.stats["none"] += 1
        return None, None

    def items(self, text):
        """Split plain text into items: text, or [sandhi, pada] (+ "m" when the pada is machine-made)."""
        out = []
        for part in PUNCT.split(text):
            if not part:
                continue
            if not DEVA.search(part) or PUNCT.fullmatch(part):
                out.append(part)
                continue
            p, how = self.word(part)
            if p and p != part:
                out.append([part, p] if how == "h" else [part, p, "m"])
            else:
                out.append(part)
        merged = []
        for it in out:
            if isinstance(it, str) and merged and isinstance(merged[-1], str):
                merged[-1] += it
            else:
                merged.append(it)
        return merged


def to_deva(s):
    from indic_transliteration import sanscript
    return sanscript.transliterate(s, sanscript.IAST, sanscript.DEVANAGARI)


def model_pada(r):
    w = r["w"]
    segs = [x for x in r["s"].split("_") if x]
    tri = []
    for item in r["slm"].split(" "):
        parts = item.split("_")
        if len(parts) == 3 and parts[0] and parts[2] != "U":
            tri.append(parts)
        else:
            tri = None
            break
    if tri and segs and [t[0] for t in tri] == segs:
        forms, tags, lemmas = segs, [t[2] for t in tri], [t[1] for t in tri]
    elif tri:
        forms, tags, lemmas = [t[0] for t in tri], [t[2] for t in tri], [t[1] for t in tri]
    else:
        return None  # no reliable compound information
    out = ""
    for i, (f, tag, lem) in enumerate(zip(forms, tags, lemmas)):
        if i:
            if lem in SUFFIX_LEMMAS and tags[i - 1] == "Cp":
                sep = ""
            else:
                sep = "-" if tags[i - 1] == "Cp" else " "
            out += sep
        out += f
    p = to_deva(out)
    bare = lambda s: re.sub(r"[\s\-‌‍]", "", s)
    if difflib.SequenceMatcher(None, bare(w), bare(p)).ratio() < 0.7:
        return None
    # A one-letter piece is a broken split (इतः → इ तः), unless it is a particle or the negative prefix अ-.
    pieces = re.split(r"(\s|-)", p)
    for i in range(0, len(pieces), 2):
        piece, sep = pieces[i], pieces[i + 1] if i + 1 < len(pieces) else ""
        if len(piece) == 1 and piece not in SHORT_OK and not (piece in "अन" and sep == "-"):
            return None
    # A word-final consonant stays as written (वाक् is not to be shown as वाच्).
    if w.endswith("्") and p.endswith("्") and len(w) >= 2 and len(p) >= 2 and w[-2] != p[-2]:
        p = p[:-2] + w[-2:]
    return p


SHORT_OK = {"च", "न", "उ", "ह", "स"}
