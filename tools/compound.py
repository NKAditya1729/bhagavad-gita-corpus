"""Two last resorts for compounds the model leaves whole (used by pada.py, in IAST).

align_stems — the model gave only the member stems ("__vikṣepaka_U __karman_U …"): line them up with the word
              and take the last member's inflected form from the word itself.
split_lemma — the model read a compound as one dictionary word (mūlāvidyā, yajñāṅga, brahmarandhra): split it
              where both halves are stems the model itself uses as compound members, undoing vowel sandhi at
              the joint (ā = a+a, e = a+i, o = a+u, y = i+…, v = u+…).
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPASARGA = {"pra", "parā", "apa", "sam", "saṃ", "anu", "ava", "nis", "nir", "dus", "dur", "vi", "ā", "ni", "adhi",
            "api", "ati", "su", "ut", "ud", "abhi", "prati", "pari", "upa", "sa", "a", "an", "pratī", "upā"}
PRONOUN = {"tad", "yad", "etad", "idam", "kim", "adas", "asmad", "yuṣmad", "mad", "tvad", "sarva", "iti", "ca",
           "eva", "api", "na", "tu", "hi", "vā", "iva"}
VOWELS = "aāiīuūṛṝeoḷ"
# readings that look like members but are not (सम्-आरम्भ is not सम-आरम्भ; ममता-वान्; विनश्वर)
NOT_LEFT = {"sama", "mama", "vinaś"}
NOT_RIGHT = {"vara", "tāvat"}
# taddhita/kṛt endings are never compound members of their own
SUFFIXES = {"ana", "tva", "tā", "tara", "tama", "maya", "vat", "mat", "ka", "ika", "iya", "īya", "ya", "tṛ", "tavya",
            "anīya", "in", "vin", "mant", "vant", "atman", "ātva", "tvā", "ita", "ta", "na", "tya"}


def stem_form(lemma):
    """The form a lemma takes as a compound member: karman → karma, ātman → ātma, yogin → yogi."""
    for end, rep in (("an", "a"), ("in", "i"), ("ant", "at")):
        if lemma.endswith(end) and len(lemma) > len(end) + 2:
            return lemma[: -len(end)] + rep
    return lemma


def fix_final(s):
    """The pausal form of a word's last member as it stands before another word (विषयो → विषयः)."""
    if s.endswith("o") and not s.endswith("au"):
        return s[:-1] + "aḥ"
    if s.endswith("ṃ"):
        return s[:-1] + "m"
    return s


def align_stems(w, lemmas):
    if len(lemmas) < 2 or lemmas[0] in PRONOUN:
        return None
    members = [stem_form(l) for l in lemmas[:-1]]
    pos = 0
    for m in members:  # each member's core must appear in order in the word
        core = m[1:-1] if m[0] in VOWELS and len(m) > 3 else (m[:-1] if len(m) > 2 else m)
        i = w.find(core, max(0, pos - 1))
        if i < 0:
            return None
        pos = i + len(core)
    last = lemmas[-1]
    key = last[1:3] if last[0] in VOWELS else last[:2]
    i = w.rfind(key)
    if i < pos - 2 or i < 0:
        return None
    tail = (last[0] if last[0] in VOWELS else "") + w[i:]
    return "-".join(members) + "-" + fix_final(tail)


class Splitter:
    def __init__(self, slm_records):
        cp, anyl = Counter(), Counter()
        for x in slm_records:
            for item in x.split(" "):
                parts = item.split("_")
                if len(parts) == 3 and parts[1]:
                    (cp if parts[2].endswith("Cp") else anyl)[parts[1]] += 1
        self.count = cp + anyl
        self.cp = cp
        self.members = {l for l, c in cp.items() if c >= 2 and len(l) >= 3 and l not in UPASARGA | SUFFIXES}
        self.heads = (self.members | {l for l, c in anyl.items() if c >= 2 and len(l) >= 3}) - SUFFIXES

    def junctions(self, L):
        """(left, right, index in L where the right part's own letters begin) for every reading of each joint."""
        for i in range(3, len(L) - 2):
            ch = L[i]
            yield L[:i], L[i:], i
            if ch in "āeoīū" or L[i:i + 2] in ("ai", "au"):
                two = L[i:i + 2] in ("ai", "au")
                rest = L[i + (2 if two else 1):]
                for lv, rv in {"ā": [("a", "a"), ("a", "ā"), ("ā", "a"), ("ā", "ā")], "e": [("a", "i"), ("a", "ī")],
                               "o": [("a", "u"), ("a", "ū")], "ī": [("i", "i"), ("ī", "i")], "ū": [("u", "u")],
                               "ai": [("a", "e"), ("a", "ai")], "au": [("a", "o"), ("a", "au")]}[L[i:i + 2] if two else ch]:
                    yield L[:i] + lv, rv + rest, i + (2 if two else 1)
            if ch in "yv" and i + 1 < len(L) and L[i + 1] in VOWELS and L[i - 1] not in VOWELS:
                yield L[:i] + ("i" if ch == "y" else "u"), L[i + 1:], i + 1

    def split_word(self, w, lemma):
        """w (IAST, inflected) whose single lemma is a two-member compound → 'left-right…' with w's own ending.
        Strict: both members ≥4 letters and used often by the model (as a compound member / as a word), the word
        spelt exactly as the lemma up to the joint, and only one way to read the joint."""
        if len(lemma) < 8:
            return None
        found = []
        for left, right, j in self.junctions(lemma):
            if len(left) < 4 or len(right) < 4 or left in UPASARGA | NOT_LEFT or right in SUFFIXES | NOT_RIGHT:
                continue
            if self.cp[left] >= 5 and self.count[right] >= 5 and w[:j] == lemma[:j]:
                found.append((left, right, j))
        if len(found) != 1:
            return None
        left, right, j = found[0]
        vowel_joint = lemma[j - 1] in VOWELS and right[0] in VOWELS and not lemma[j:].startswith(right)
        tail = (right[0] if vowel_joint else "") + w[j:]
        return stem_form(left) + "-" + fix_final(tail)


def load_records():
    recs = []
    for line in (ROOT / "build/model-out.jsonl").read_text(encoding="utf-8").splitlines():
        recs.append(json.loads(line)["slm"])
    return recs
