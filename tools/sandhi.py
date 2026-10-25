"""Pāṇinian sandhi joiner, used to check a padapāṭha: join its pieces again by the rules of the
sandhi-prakaraṇa and see whether the original word comes back.

Works in SLP1. join(a, b) gives every result the rules allow for a+b (optional rules give several),
each with the sūtras applied. Sūtra numbers/texts verified against ashtadhyayi.com data (tools/verify_sutras.py).

  ac-sandhi   6.1.101 अकः सवर्णे दीर्घः · 6.1.87 आद्गुणः (+1.1.51 उरण् रपरः) · 6.1.88 वृद्धिरेचि · 6.1.77 इको यणचि ·
              6.1.78 एचोऽयवायावः · 8.3.19 लोपः शाकल्यस्य · 6.1.109 एङः पदान्तादति · 6.1.73 छे च · 6.1.75 दीर्घात् · 6.1.76 पदान्ताद्वा
  hal-sandhi  8.2.39 झलां जशोऽन्ते · 8.4.55 खरि च · 8.4.45 यरोऽनुनासिकेऽनुनासिको वा · 8.4.40 स्तोः श्चुना श्चुः ·
              8.4.41 ष्टुना ष्टुः · 8.4.63 शश्छोऽटि · 8.4.62 झयो होऽन्यतरस्याम् · 8.4.60 तोर्लि · 8.3.32 ङमो ह्रस्वादचि ङमुण्नित्यम् ·
              8.3.23 मोऽनुस्वारः · 8.4.59 वा पदान्तस्य · 8.3.7 नश्छव्यप्रशान्
  visarga     8.2.66 ससजुषो रुः · 8.3.15 खरवसानयोर्विसर्जनीयः · 8.3.34 विसर्जनीयस्य सः · 8.3.36 वा शरि · 6.1.113 अतो रोरप्लुतादप्लुते ·
              6.1.114 हशि च · 8.3.17 भोभगोअघोअपूर्वस्य योऽशि · 8.3.22 हलि सर्वेषाम् · 8.3.14 रो रि · 6.3.111 ढ्रलोपे पूर्वस्य दीर्घोऽणः ·
              6.1.132 एतत्तदोः सुलोपोऽकोरनञ्समासे हलि
"""
from indic_transliteration import sanscript

VOWELS = set("aAiIuUfFxXeEoO")
SHORT = set("aiufx")
LONG = {"a": "A", "i": "I", "u": "U", "f": "F", "x": "X"}
VOICED = set("gGjJqQdDbBNYRnmyrlvh") | VOWELS
KHAR = set("kKcCwWtTpPSzs")
NASAL_OF = {"k": "N", "g": "N", "c": "Y", "j": "Y", "w": "R", "q": "R", "t": "n", "d": "n", "p": "m", "b": "m"}
JAS = {"k": "g", "c": "j", "w": "q", "t": "d", "p": "b", "g": "g", "j": "j", "q": "q", "d": "d", "b": "b"}
CAR = {v: k for k, v in JAS.items() if k != v} | {"k": "k", "c": "c", "w": "w", "t": "t", "p": "p"}
CLASS = {**dict.fromkeys("kKgGN", "k"), **dict.fromkeys("cCjJY", "c"), **dict.fromkeys("wWqQR", "w"),
         **dict.fromkeys("tTdDn", "t"), **dict.fromkeys("pPbBm", "p")}


def slp(deva):
    return sanscript.transliterate(deva, sanscript.DEVANAGARI, sanscript.SLP1)


def deva(s):
    return sanscript.transliterate(s, sanscript.SLP1, sanscript.DEVANAGARI)


def norm(s):
    """Spellings that are the same word: avagraha, ZWJ/ZWNJ, anusvāra vs the class nasal (8.4.58/8.4.59)."""
    s = s.replace("'", "").replace("‍", "").replace("‌", "").replace("~", "")
    out = []
    for i, ch in enumerate(s):
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if ch in "NYRnm" and nxt in CLASS and NASAL_OF.get(CLASS[nxt]) == ch:
            out.append("M")
        else:
            out.append(ch)
    s = "".join(out)
    return s[:-1] + "m" if s.endswith("M") else s


def _vowel(x, y, internal):
    """x = last vowel of a, y = first vowel of b."""
    out = []
    if x in SHORT | set(LONG.values()) and y in VOWELS:
        base = {"A": "a", "I": "i", "U": "u", "F": "f", "X": "x"}.get(x, x)
        ybase = {"A": "a", "I": "i", "U": "u", "F": "f", "X": "x"}.get(y, y)
        if base == ybase and base in "aiufx":
            out.append((LONG[base], "6.1.101"))
        elif base == "a":
            if y in "iI":
                out.append(("e", "6.1.87"))
            elif y in "uU":
                out.append(("o", "6.1.87"))
            elif y in "fF":
                out.append(("ar", "6.1.87 1.1.51"))
            elif y in "xX":
                out.append(("al", "6.1.87 1.1.51"))
            elif y in "eE":
                out.append(("E", "6.1.88"))
            elif y in "oO":
                out.append(("O", "6.1.88"))
        elif base in "iuf":
            out.append(({"i": "y", "u": "v", "f": "r"}[base] + y, "6.1.77"))
    return out


def join(a, b, internal=False):
    """All results for a + b, as {(result, rules)}. a, b in SLP1."""
    if not a:
        return {(b, "")}
    if not b:
        return {(a, "")}
    x, y = a[-1], b[0]
    res = set()
    # ---- visarga (and final s / r, which become ru by 8.2.66) ----
    if x in "Hs" or (x == "r" and y not in VOWELS and y not in VOICED):
        pre = a[:-1]
        v = pre[-1] if pre else ""
        if y in "cC":
            res.add((pre + "S" + b, "8.2.66 8.3.34 8.4.40"))
        elif y in "wW":
            res.add((pre + "z" + b, "8.2.66 8.3.34 8.4.41"))
        elif y in "tT":
            res.add((pre + "s" + b, "8.2.66 8.3.34"))
        elif y in "kKpP":
            res.add((pre + "H" + b, "8.2.66 8.3.15"))
            res.add((pre + "s" + b, "8.3.34 (कस्कादि)"))
        elif y in "Szs":
            res.add((pre + "H" + b, "8.2.66 8.3.15 8.3.36"))
            res.add((pre + y + b, "8.2.66 8.3.34 8.3.36"))
        elif v == "a" and (len(pre) < 2 or pre[-2] != "a" or True):
            if pre in ("sa", "eza") and y not in VOWELS:
                res.add((pre + b, "6.1.132"))
            if y == "a":
                res.add((pre[:-1] + "o'" + b[1:], "8.2.66 6.1.113 6.1.87 6.1.109"))
            elif y in VOWELS:
                res.add((pre + b, "8.2.66 8.3.17 8.3.19"))
                res.add((pre + "y" + b, "8.2.66 8.3.17"))
            elif y in VOICED:
                res.add((pre[:-1] + "o" + b, "8.2.66 6.1.114 6.1.87"))
        elif v == "A":
            if y in VOICED:
                res.add((pre + b, "8.2.66 8.3.17 8.3.22"))
        elif v:
            if y == "r":
                res.add((pre[:-1] + LONG.get(v, v) + b, "8.2.66 8.3.14 6.3.111"))
            elif y in VOICED:
                res.add((pre + "r" + b, "8.2.66"))
        return res or {(a + b, "")}
    if x == "r":  # r before a vowel or voiced sound stays (punar api → punarapi)
        if y == "r":
            v = a[-2] if len(a) > 1 else ""
            return {(a[:-2] + LONG.get(v, v) + b, "8.3.14 6.3.111")}
        return {(a + b, "")}
    # ---- m ----
    if x == "m":
        if y in VOWELS:
            return {(a + b, "")}
        return {(a[:-1] + "M" + b, "8.3.23"), (a[:-1] + NASAL_OF.get(CLASS.get(y, ""), "M") + b, "8.3.23 8.4.59")}
    # ---- n ----
    if x == "n":
        pre = a[:-1]
        if y in VOWELS:
            if pre and pre[-1] in SHORT:
                res.add((a + "n" + b, "8.3.32"))
            res.add((a + b, ""))
            return res
        if y in "cC":
            return {(pre + "MS" + b, "8.3.7 8.3.34 8.4.40"), (pre + "Y" + b, "8.4.40")}
        if y in "tT":
            return {(pre + "Ms" + b, "8.3.7 8.3.34"), (a + b, "")}
        if y in "wW":
            return {(pre + "Mz" + b, "8.3.7 8.3.34 8.4.41")}
        if y == "S":
            return {(pre + "Y" + b, "8.4.40"), (pre + "YC" + b[1:], "8.4.40 8.4.63"), (a + b, "")}
        if y in "jJ":
            return {(pre + "Y" + b, "8.4.40")}
        if y in "qQ":
            return {(pre + "R" + b, "8.4.41")}
        if y == "l":  # न् + ल् → ँल्ल् / ंल्ल् (8.4.60 तोर्लि, with the nasal kept as anunāsika or anusvāra)
            return {(pre + "~l" + b, "8.4.60"), (pre + "Ml" + b, "8.4.60"), (a + b, "")}
        return {(a + b, "")}
    # ---- stops (jhal) ----
    if x in JAS:
        pre = a[:-1]
        cls = CLASS[x]
        if y in VOWELS or y in "yrvgGjJqQdDbBh":
            j = JAS[x]
            if cls == "t" and y in "jJ":
                res.add((pre + "j" + b, "8.2.39 8.4.40"))
            elif cls == "t" and y in "qQ":
                res.add((pre + "q" + b, "8.2.39 8.4.41"))
            else:
                res.add((pre + j + b, "8.2.39"))
            if y == "h":
                asp = {"g": "G", "j": "J", "q": "Q", "d": "D", "b": "B"}[j]
                res.add((pre + j + asp + b[1:], "8.2.39 8.4.62"))
            return res
        if y in "NYRnm":
            return {(pre + NASAL_OF[x] + b, "8.4.45"), (pre + JAS[x] + b, "8.2.39 (8.4.45 वा)")}
        if y == "l":
            return {(pre + ("l" if cls == "t" else JAS[x]) + b, "8.2.39 8.4.60")}
        car = CAR.get(x, x)
        if cls == "t" and y in "cC":
            return {(pre + "c" + b, "8.4.55 8.4.40")}
        if cls == "t" and y in "wW":
            return {(pre + "w" + b, "8.4.55 8.4.41")}
        if cls == "t" and y == "S":
            return {(pre + "cC" + b[1:], "8.4.55 8.4.40 8.4.63"), (pre + "cS" + b[1:], "8.4.55 8.4.40 (8.4.63 वा)")}
        return {(pre + car + b, "8.4.55")}
    # ---- vowels ----
    if x in VOWELS:
        if y in VOWELS:
            if x in "eo":
                if y == "a" and not internal:
                    res.add((a + "'" + b[1:], "6.1.109"))
                res.add((a[:-1] + "a" + b, "6.1.78 8.3.19"))
                res.add((a[:-1] + ("ay" if x == "e" else "av") + b, "6.1.78"))
                return res
            if x in "EO":
                res.add((a[:-1] + "A" + b, "6.1.78 8.3.19"))
                res.add((a[:-1] + ("Ay" if x == "E" else "Av") + b, "6.1.78"))
                return res
            out = _vowel(x, y, internal)
            for r, s in out:
                res.add((a[:-1] + r + b[1:], s))
            return res or {(a + b, "")}
        if y == "C":
            if x in SHORT:
                return {(a + "c" + b, "6.1.73 8.4.40")}
            return {(a + "c" + b, "6.1.75 8.4.40"), (a + b, "6.1.76")}
        return {(a + b, "")}
    return {(a + b, "")}


# pada-final forms a word may take before the next word, outside this token (pausal form → as printed)
FINAL = [("as", "o", "6.1.114 6.1.87"), ("as", "aH", "8.3.15"), ("s", "H", "8.3.15"), ("r", "H", "8.3.15"),
         ("aH", "o", "6.1.114 6.1.87"), ("aH", "a", "8.3.17 8.3.19"), ("AH", "A", "8.3.17 8.3.22"),
         ("H", "r", "8.2.66"), ("H", "S", "8.3.34 8.4.40"), ("H", "s", "8.3.34"), ("H", "z", "8.3.34 8.4.41"),
         ("t", "d", "8.2.39"), ("t", "n", "8.4.45"), ("t", "c", "8.4.40"), ("t", "j", "8.4.40"), ("t", "l", "8.4.60"),
         ("k", "g", "8.2.39"), ("k", "N", "8.4.45"), ("w", "q", "8.2.39"), ("p", "b", "8.2.39"),
         ("e", "a", "6.1.78 8.3.19"), ("e", "ay", "6.1.78"), ("o", "av", "6.1.78"), ("E", "A", "6.1.78 8.3.19"),
         ("E", "Ay", "6.1.78"), ("O", "Av", "6.1.78"), ("i", "y", "6.1.77"), ("I", "y", "6.1.77"), ("u", "v", "6.1.77"),
         ("U", "v", "6.1.77"), ("n", "MS", "8.3.7"), ("n", "Ms", "8.3.7"), ("n", "Y", "8.4.40"), ("n", "nn", "8.3.32"),
         ("a", "A", "6.1.101"), ("A", "A", "6.1.101")]


# words whose final visarga stands for r, not s (punar, antar, prātar, svar)
R_FINAL = {"punaH": "punar", "antaH": "antar", "prAtaH": "prAtar", "svaH": "svar", "BUyaH": "BUyaH"}


def rejoin(pieces_with_seps):
    """pieces_with_seps: [p0, sep, p1, sep, …] (SLP1; sep ' ' or '-'). Returns {(joined, rules)} (capped)."""
    pieces_with_seps = [R_FINAL.get(x, x) if i % 2 == 0 and i + 1 < len(pieces_with_seps) else x
                        for i, x in enumerate(pieces_with_seps)]
    cands = {(pieces_with_seps[0], "")}
    for i in range(1, len(pieces_with_seps), 2):
        sep, nxt = pieces_with_seps[i], pieces_with_seps[i + 1]
        new = set()
        for c, r in cands:
            for j, rr in join(c, nxt, internal=(sep == "-")):
                new.add((j, (r + " " + rr).strip()))
        cands = set(sorted(new, key=lambda t: len(t[1]))[:64])
    return cands


def check(word, pada):
    """Does the padapāṭha `pada` (Devanagari) join back into `word` by the sandhi rules?
    Returns (ok, rules used or reason)."""
    import re
    w = norm(slp(word))
    parts = re.split(r"([ \-])", slp(pada))
    parts = [p for p in parts if p != ""]
    if not parts:
        return False, "empty"
    # a leading avagraha in the printed word stands for an elided initial अ (6.1.109)
    lead_a = w.startswith("'") or slp(word).startswith("'")
    cands = rejoin(parts)
    for joined, rules in cands:
        j = norm(joined)
        if j == w:
            return True, rules
        if lead_a and j.startswith("a") and j[1:] == w:
            return True, rules + " 6.1.109"
        for pf, sf, r in FINAL:  # the word's own last sound may already be in sandhi with the next word
            if j.endswith(pf) and norm(j[: -len(pf)] + sf) == w:
                return True, (rules + " " + r).strip()
            if lead_a and j.startswith("a") and j.endswith(pf) and norm(j[1: -len(pf)] + sf) == w:
                return True, (rules + " " + r + " 6.1.109").strip()
        # retroflexion across members (8.4.1–8.4.3 णत्वम्, 8.3.59 षत्वम्) is not modelled: allow ण/न, ष/स
        if j.replace("R", "n").replace("z", "s") == w.replace("R", "n").replace("z", "s"):
            return True, (rules + " 8.4.1/8.3.59").strip()
    # the print ran two words together without sandhi (an OCR or typing slip, e.g. संजयःअर्जुनो): the pieces simply abut
    plain = norm("".join(x for x in parts if x not in " -"))
    if plain == w or any(plain.endswith(pf) and norm(plain[: -len(pf)] + sf) == w for pf, sf, _ in FINAL):
        return True, "printed run-together (no sandhi)"
    return False, "no rule joins it back"
