"""Padapāṭha (sandhi-vivaraṇa) for a single word, in Harsha's format:
sandhi junctions become spaces, compound members are joined by hyphens (समास-अवयवाः).

Order of authority: Harsha's own pairs (अध्ययन-सहकारी) → ByT5-Sanskrit model output → none.
A piece of Harsha's padapāṭha that is still an unbroken compound (उपायोपेयभूतम्) is broken further by the model.
"""
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import compound

ROOT = Path(__file__).resolve().parent.parent
WORDCH = "ऀ-ॣ॰-ॿ‌‍"  # Devanagari letters and signs; not । ॥ or digits
PUNCT = re.compile(f"([^{WORDCH}]+)")
DEVA = re.compile(f"[{WORDCH}]")
EDGES = re.compile(f"^[^{WORDCH}]+|[^{WORDCH}]+$")
CONSONANT = re.compile("[क-हक़-य़]")
SUFFIX_LEMMAS = {"tā", "tva", "tara", "tama", "vat", "mat", "maya", "tas"}
SHORT_OK = {"च", "न", "उ", "ह", "स"}
# words that end a pada even without a case ending (used when only the plain segmentation is known)
INDECLINABLES = set("च न तु हि वा इति एव अपि इव यथा तथा यदि तदा यत्र तत्र अत्र इह किम् कथम् कुतः ततः अतः यतः "
                    "पुनः पुनर् अथ खलु नु ननु सह विना प्रति अन्यत्र सदा सर्वदा कदाचित् कदाचन एवम् इत्थम् "
                    "चेत् नाम किल अलम् ईषत् उत अपि वै".split())


def fullness(p):
    return p.count("-") + p.count(" ")


# sandhi voices/unvoices stops and assimilates nasals; compare consonants up to those changes
VOICE = str.maketrans("गघजझडढदधबभङञणनमखछठथफ", "ककचचटटततपपनननननकचटतप")


def skeleton(s):
    # य व र स can come from vowels or visarga in sandhi (इति+अर्थः → इत्यर्थः, हेतोः → हेतोर्), so leave them out
    return re.sub("[यवरसशष]", "", "".join(CONSONANT.findall(s.replace("ं", "न"))).translate(VOICE))


def plausible(w, p):
    """The split keeps the word's consonants (sandhi changes vowels, visarga, voicing and finals, little else)."""
    # undo the commonest consonant assimilations in the joined word (यच्छब्दः ← यत्+शब्दः, तन्मते ← तत्+मते)
    w2 = w
    for joined, apart in (("च्छ", "त्श"), ("च्च", "त्च"), ("ज्ज", "द्ज"), ("न्न", "त्न"), ("न्म", "त्म"), ("ल्ल", "त्ल"), ("द्ध", "द्ह"), ("ग्घ", "क्ह")):
        w2 = w2.replace(joined, apart)
    b = skeleton(p)
    return any(not a or SequenceMatcher(None, a, b).ratio() >= 0.75 for a in {skeleton(w), skeleton(w2)})


def tidy(w, p):
    """Reject broken one-letter pieces; keep a word-final consonant as written (वाक् not वाच्)."""
    pieces = re.split(r"(\s|-)", p)
    for i in range(0, len(pieces), 2):
        piece, sep = pieces[i], pieces[i + 1] if i + 1 < len(pieces) else ""
        joined = sep == "-" or (i and pieces[i - 1] == "-")
        if len(piece) == 1 and piece not in SHORT_OK and not (joined and piece not in "आइईउऊ"):
            return None
    # a pada never ends in स् in pausa: ततस् → ततः (a compound member such as मनस्- keeps it)
    p = re.sub("स्(?=\\s|$)", "ः", p)
    if w.endswith("्") and p.endswith("्") and len(w) >= 2 and len(p) >= 2 and w[-2] != p[-2]:
        p = p[:-2] + w[-2:]
    return p if plausible(w, p) else None


def to_iast(s):
    from indic_transliteration import sanscript
    return sanscript.transliterate(s, sanscript.DEVANAGARI, sanscript.IAST)


def to_deva(s):
    from indic_transliteration import sanscript
    return sanscript.transliterate(s, sanscript.IAST, sanscript.DEVANAGARI)


def compose(forms, cps, lemmas=None):
    out = ""
    for i, f in enumerate(forms):
        if i:
            suffix = (lemmas[i] in SUFFIX_LEMMAS) if lemmas else re.match(r"^tv(a|ā|e|ena|āt|asya|ena|ayoḥ)?[mḥ]?$|^tā(yāḥ|yām|m)?$|^tayā$", f)
            out += "" if suffix and cps[i - 1] else ("-" if cps[i - 1] else " ")
        out += f
    return to_deva(out)


def slm_pada(w, slm):
    tri = []
    for item in slm.split(" "):
        parts = item.split("_")
        if len(parts) != 3 or not parts[0] or parts[2] == "U":
            return None  # the tagging pass broke down
        tri.append(parts)
    forms, lemmas, tags = [t[0] for t in tri], [t[1] for t in tri], [t[2] for t in tri]
    # the negative prefix a-/an- is a compound member (अ-द्वितीयस्य), whatever tag it gets
    cps = [t.endswith("Cp") or (lem in ("a", "an") and i + 1 < len(forms)) for i, (t, lem) in enumerate(zip(tags, lemmas))]
    return tidy(w, compose(forms, cps, lemmas))


def s_pada(w, seg):
    """Plain segmentation: a piece that ends in a case or verb ending, or is an indeclinable, ends a pada;
    a bare stem (no ending) is a compound member."""
    forms = [x for x in seg.split("_") if x]
    if not forms:
        return None
    deva = [to_deva(f) for f in forms]
    cps = []
    for i, d in enumerate(deva):
        last = i == len(deva) - 1
        ends = d in INDECLINABLES or d.endswith(("ः", "म्", "ं"))
        cps.append(not last and not ends)
    return tidy(w, compose(forms, cps))


class Pada:
    def __init__(self):
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
        seg = {}
        sf = ROOT / "build/model-s.jsonl"
        if sf.exists():
            for line in sf.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                seg[r["w"]] = r["s"]
        hist = {}
        mo = ROOT / "build/model-out.jsonl"
        if mo.exists():
            for line in mo.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                hist.setdefault(r["w"], []).append(r["slm"])  # a later run (e.g. with context) supersedes an earlier one
        splitter = compound.Splitter([x for xs in hist.values() for x in xs])
        self.how = Counter()
        for w, xs in hist.items():
            p, how = slm_pada(w, xs[-1]), "slm"
            if p is None and w in seg:
                p, how = s_pada(w, seg[w]), "seg"
            if p is None:  # only the member stems came back: line them up with the word
                for x in xs:
                    lemmas = [i.split("_")[2] for i in x.split(" ") if i.startswith("__") and len(i.split("_")) == 4]
                    if lemmas and len(lemmas) == len(x.split(" ")):
                        q = compound.align_stems(to_iast(w), lemmas)
                        p, how = (tidy(w, to_deva(q)) if q else None), "stems"
                        break
            if p == w:  # read as one dictionary word: is it a two-member compound?
                one = xs[-1].split(" ")
                parts = one[0].split("_") if len(one) == 1 else []
                if len(parts) == 3 and parts[0]:
                    q = splitter.split_word(parts[0], parts[1])
                    q = tidy(w, to_deva(q)) if q else None
                    if q:
                        p, how = q, "lexicon"
            if p:
                self.model[w] = p
                self.how[how] += 1
        self.stats = Counter()

    def refine(self, p):
        """Break any still-unbroken compound piece of a padapāṭha with the model's analysis of that piece."""
        out, changed = [], False
        for piece in p.split(" "):
            core = EDGES.sub("", piece)
            if "-" not in piece and core in self.model and self.model[core] != core:
                out.append(piece.replace(core, self.model[core]))
                changed = True
            else:
                out.append(piece)
        return " ".join(out), changed

    def word(self, w):
        if w in self.harsha:
            p, changed = self.refine(self.harsha[w])
            self.stats["harsha+model" if changed else "harsha"] += 1
            return p, "m" if changed else "h"
        if w in self.model:
            p = self.model[w]
            if p == w:
                self.stats["same"] += 1
                return None, None
            self.stats["model"] += 1
            return self.refine(p)[0], "m"
        self.stats["none"] += 1
        return None, None

    def pair(self, s, p):
        """An existing [sandhi, pada] pair from Harsha's pages, with its unbroken compounds broken."""
        p2, changed = self.refine(p)
        return [s, p2, "m"] if changed else [s, p]

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
