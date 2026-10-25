"""Review every machine-made padapāṭha on the site against the rules of the Aṣṭādhyāyī.

For each [word, pada] pair marked "m" in docs/data:
  1. sandhi   — the pieces must join back into the printed word by the sandhi rules (tools/sandhi.py).
  2. padas    — every piece must be a real word (a pada, 1.4.14 सुप्तिङन्तं पदम्) or, before a hyphen, a real
                stem; the nañ prefix अ-/अन्- only before a real word (2.2.6 नञ्, 6.3.73 नलोपो नञः, 6.3.74 तस्मान्नुडचि).
  3. members  — a compound member stands in its pada form: final न् dropped (8.2.7 नलोपः प्रातिपदिकान्तस्य),
                च्/ज्/श् → क् (8.2.30 चोः कुः, 8.2.62 क्विन्प्रत्ययस्य कुः), ष् → ट्, aspirates de-aspirated (8.2.39, 8.4.56).
  4. names    — a proper name or saṃjñā (प्रजापति, जनार्दन, धृतराष्ट्र …) is one word and is not broken.
A pair that fails is repaired (member forms; merging a broken piece back; names) and checked again.
If no repair passes, the machine pada is withdrawn and the word is shown as printed.

Run with ~/sanskrit-tools/.venv/bin/python (it has Vidyut). Writes build/review.json and build/review-report.md.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandhi  # noqa: E402
from sandhi import slp, deva  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KOSHA_DIR = Path.home() / "sanskrit-tools/vidyut-data/kosha"

INDECL = set("""ca na tu hi vA iti eva api iva yaTA taTA yadi tadA yatra tatra atra iha kim kaTam kutaH tataH ataH yataH
punaH punar aTa Kalu nu nanu saha vinA prati anyatra sadA sarvadA kadAcit kadAcana evam itTam cet nAma kila alam Izat
uta vE ha sma tAvat yAvat prAk paScAt antaH antar bahiH sAkzAt svayam sakft asakft muhuH SanEH sahasA atIva ativa
kevalam param punaHpunaH sarvaTA anyaTA ekadA tarhi yarhi idAnIm adya Svas hyaH ciram nityam nUnam KalU hanta aho
BoH re are kva sarvatra ubhayaTA mA mA_sma naiva no nEva ca_eva tat yat etat idam adaH sa saH yaH kaH ayam iyam esaH ezaH""".split())
FRAGMENTS = {"taH", "ti", "ta", "tAH", "yA", "ya", "ra", "ma", "Ta", "Da", "Sa", "za", "ha", "ka", "ga", "ja", "va", "pa"}
NAMES_DEVA = """
वासुदेव नारायण जनार्दन मधुसूदन केशव हृषीकेश गोविन्द माधव अच्युत वार्ष्णेय यादव अरिसूदन केशिनिषूदन जगन्निवास
विष्णु कृष्ण मुकुन्द दामोदर पद्मनाभ देवकीनन्दन गोपाल धनञ्जय गुडाकेश कौन्तेय पार्थ परन्तप सव्यसाचिन् किरीटिन्
धृतराष्ट्र दुर्योधन सुयोधन युधिष्ठिर भीमसेन वृकोदर धृष्टद्युम्न धृष्टकेतु चेकितान काशिराज पुरुजित् कुन्तिभोज शैब्य
युधामन्यु उत्तमौजस् सौभद्र द्रौपदेय अश्वत्थामन् सौमदत्ति जयद्रथ विकर्ण भीष्म द्रोण विराट द्रुपद शिखण्डिन् सात्यकि
अभिमन्यु नकुल सहदेव पाण्डु कुन्ती सञ्जय अर्जुन युयुधान पाञ्चजन्य देवदत्त पौण्ड्र अनन्तविजय सुघोष मणिपुष्पक
प्रजापति हिरण्यगर्भ बृहस्पति स्कन्द ऐरावत उच्चैःश्रवस्   वासुकि वरुण अर्यमन् प्रह्लाद वैनतेय जाह्नवी
चित्ररथ कपिल नारद असित देवल व्यास उशनस् भृगु मरीचि विवस्वत् इक्ष्वाकु  दाशरथि रघुनाथ रामचन्द्र हनूमत्
याज्ञवल्क्य वसिष्ठ विश्वामित्र पतञ्जलि जैमिनि बादरायण कणाद शबर कुमारिल प्रभाकर शङ्कराचार्य शङ्करभगवत्पाद
आनन्दगिरि श्रीधर नीलकण्ठ धनपति सुरेश्वर वाचस्पति गौडपाद आपस्तम्ब बौधायन मैत्रेयी उद्दालक श्वेतकेतु नचिकेतस्
 जनक दुर्वासस् वृत्र पुरन्दर शचीपति सुरपति त्रिविक्रम नृसिंह वामन परशुराम बलराम सङ्कर्षण प्रद्युम्न अनिरुद्ध
महाभारत रामायण भगवद्गीता बृहदारण्यक छान्दोग्य तैत्तिरीय श्वेताश्वतर कौषीतकि ऐतरेय मुण्डक माण्डूक्य
गीताभाष्य शारीरकभाष्य  पञ्चदशी योगवासिष्ठ विष्णुपुराण भागवत हरिवंश मनुस्मृति याज्ञवल्क्यस्मृति
""".split()
# not listed: words that are names only sometimes — सत्यकाम (सत्यकामत्वम्), ब्रह्मसूत्र (13.4: ब्रह्मसूचकानि वाक्यानि),
# कामधुक् (3.10 इष्टकामधुक्)
NAMES = {slp(n) for n in NAMES_DEVA}
SUFFIXED = [re.compile(p + "$") for p in (
    r"tv(a[Hm]?|At|Ad|ena|Aya|asya|e|ayoH|AnAm|ezu|AByAm|Ani|o)",
    r"t(A|Am|ayA|AyAH|AyAm|AyE|AH|a)",
    r"[vm](An|at|ad|atA|ate|ataH|ati|antam|antaH|antO|atAm|atsu|atI|atIm|atyAH|atyA|adBiH|adByaH|atvam|attvam|attvAt)",
    r"may(aH|am|ena|At|Ad|asya|e|AH|Ani|o|a|I|Im|yA|yAH|yAm)",
    r"(?<=[aA])k(aH|am|ena|At|Ad|asya|e|AH|An|Ani|A|o|a|AyAH|Am)",
    r"(in|I|inam|inA|ine|inaH|ini|inO|inAm|izu|iBiH|iByaH|itvam|itvAt|itvena|itve|itA)",
    r"taH",  # 5.3.7 पञ्चम्यास्तसिल् (also 5.4.44): -तः
    r"(sT|j|g|d|p|jY|Bft|kft|vid)(a[Hm]?|At|Ad|ena|asya|e|AH|An|Ani|A|o|a|ayA|AyAH|Ena|AnAm|ezu|tvam|tvAt)")]  # upapada finals
# member finals in their pada form
MEMBER_FINAL = {"c": "k", "j": "k", "S": "k", "z": "w", "D": "t", "B": "p", "G": "k", "Q": "w", "h": "k", "T": "t",
                "P": "p", "K": "k", "C": "k", "J": "k", "W": "w"}


class Reviewer:
    def __init__(self):
        from vidyut.kosha import Kosha
        self.kosha = Kosha(str(KOSHA_DIR))
        self.cache = {}
        self.attested = Counter()  # pieces of Harsha's own padapāṭha
        self.forms = Counter()  # forms the model gives with a case/verb tag
        self.members = Counter()  # forms the model gives as compound members
        for line in (ROOT / "build/model-out.jsonl").read_text(encoding="utf-8").splitlines():
            for it in json.loads(line)["slm"].split(" "):
                p = it.split("_")
                if len(p) == 3 and p[0]:
                    x = slp(sandhi.sanscript.transliterate(p[0], sandhi.sanscript.IAST, sandhi.sanscript.DEVANAGARI))
                    (self.members if p[2].endswith("Cp") else self.forms)[x] += 1

    def in_kosha(self, x):
        if x not in self.cache:
            key = x[:-1] + "s" if x.endswith("H") else (x[:-1] + "m" if x.endswith("M") else x)
            key = key[:-1] + {"d": "t", "g": "k", "q": "w", "b": "p"}[key[-1]] if key[-1:] in "dgqb" else key
            try:
                self.cache[x] = bool(self.kosha.get(key)) or (key != x and bool(self.kosha.get(x)))
            except Exception:
                self.cache[x] = False
        return self.cache[x]

    def valid(self, x, member, nxt=""):
        """Is piece x (SLP1) a real word (or, if member, a real stem)?"""
        if not x or x in FRAGMENTS:
            return False
        if re.fullmatch(r"[^aAiIuUfFxXeEoO]+", x):  # a bare consonant (च्, म्, र्) is no pada
            return False
        if x == "a":  # nañ before a consonant (6.3.73)
            return member and bool(nxt) and nxt[0] not in sandhi.VOWELS and len(nxt) >= 3 and self.valid(nxt, False)
        if x == "an":  # before a vowel (6.3.74)
            return member and bool(nxt) and nxt[0] in sandhi.VOWELS and self.valid(nxt, False)
        if x in INDECL or x in NAMES:
            return True
        if self.attested[deva(x)] >= 2:
            return True
        if len(x) <= 2:
            return x in ("su", "sa", "du", "nir", "dur", "pra", "vi")
        if self.in_kosha(x):
            return True
        if x[0] == "a" and len(x) >= 5 and (self.valid(x[1:], member) or (x[1] == "n" and self.valid(x[2:], member))):
            return True  # nañ-tatpuruṣa (2.2.6 नञ्): a-/an- + a real word
        if member and x[-1] in "ai" and self.in_kosha(x + "n"):
            return True  # an in-/an-stem member after 8.2.7 नलोपः प्रातिपदिकान्तस्य (छत्रि-, आत्म-)
        for pat in SUFFIXED:  # a taddhita derivative (-tva, -tā, -vat/-mat, -maya, -ka) of a real stem
            m = pat.search(x)
            if m and m.start() >= 2 and self.valid(x[:m.start()], True):
                return True
        if member:
            return self.members[x] >= 3 or self.forms[x] >= 3
        return self.forms[x] >= 3

    def pieces_ok(self, parts):
        """parts = [p0, sep, p1, …] in SLP1."""
        bad = []
        for i in range(0, len(parts), 2):
            member = i + 1 < len(parts) and parts[i + 1] == "-"
            nxt = parts[i + 2] if i + 2 < len(parts) else ""
            if not self.valid(parts[i], member, nxt):
                bad.append(i)
        return bad


def split_parts(p):
    return [x for x in re.split(r"([ \-])", slp(p)) if x]


def unsplit(parts):
    return deva("".join(parts))


def member_forms(parts):
    """Compound members (and word-final consonants) in their pada form; returns (parts, sūtras) or None."""
    out, changed = list(parts), []
    for i in range(0, len(out), 2):
        x = out[i]
        member = i + 1 < len(out) and out[i + 1] == "-"
        if member and x.endswith("n") and len(x) > 3 and x[-2] in "aiu" and x not in ("an",):
            out[i] = x[:-1]
            changed.append("8.2.7")
        elif x and x[-1] in MEMBER_FINAL and (member or i == len(out) - 1 or out[i + 1] == " "):
            if x[-1] == "j" and re.search(r"(rAj|BrAj|yaj|sfj|mfj)$", x):
                out[i], why = x[:-1] + "w", "8.2.36 8.2.39 8.4.56"
            elif x[-1] == "S" and not re.search(r"(diS|dfS)$", x):
                out[i], why = x[:-1] + "w", "8.2.36 8.2.39 8.4.56"
            else:
                out[i] = x[:-1] + MEMBER_FINAL[x[-1]]
                why = {"c": "8.2.30", "j": "8.2.30", "S": "8.2.62", "z": "8.2.39"}.get(x[-1], "8.2.39 8.4.56")
            changed.append(why)
    return (out, changed) if changed else None


CASE_ENDINGS = {  # sup endings after the stem's last vowel (in pausal form), by stem class
    "a": {"a", "aH", "am", "ena", "Aya", "At", "Ad", "asya", "e", "O", "AByAm", "AByAm", "EH", "eByaH", "AnAm", "ezu",
          "AH", "An", "A", "o", "ayoH", "AnAm", "AByAm"},
    "A": {"A", "Am", "ayA", "AyE", "AyAH", "AyAm", "e", "AH", "AByAm", "ABiH", "AByaH", "AnAm", "Asu", "ayoH"},
    "i": {"i", "iH", "im", "inA", "aye", "eH", "O", "ayaH", "In", "iBiH", "iByaH", "InAm", "izu", "e", "yoH", "yA", "yE",
          "yAH", "yAm", "aya"},
    "I": {"I", "Im", "yA", "yE", "yAH", "yAm", "yO", "yaH", "IBiH", "IByaH", "InAm", "Izu", "i"},
    "u": {"u", "uH", "um", "unA", "ave", "oH", "O", "avaH", "Un", "uBiH", "uByaH", "UnAm", "uzu", "o", "voH", "vA"},
}


def _name_form(joined, n):
    """joined is an inflected form of name n (प्रजापति → प्रजापतीन्, प्रजापतेः; not देवल → देवलोकम्)."""
    if n[-1] in CASE_ENDINGS:
        stem = n[:-1]
        return joined.startswith(stem) and joined[len(stem):] in CASE_ENDINGS[n[-1]]
    return joined.startswith(n) and len(joined) - len(n) <= 3  # consonant stems: a short ending


def merge_names(parts):
    """Join the members of a proper name back into one word (प्रजा-पतीन् → प्रजापतीन्)."""
    out, changed = list(parts), False
    i = 0
    while i < len(out):
        best = None
        for j in range(len(out) - 1, i + 1, -2):
            if any(out[k] != "-" for k in range(i + 1, j, 2)):
                continue
            joined = out[i]
            for k in range(i + 2, j + 1, 2):
                joined = sorted(sandhi.join(joined, out[k], internal=True))[0][0]
            last = j == len(out) - 1 or out[j + 1] == " "
            head = len(joined) - len(out[j])  # where the last piece of the span begins (roughly)
            if any(len(n) > len(out[i]) + 1 and len(n) > head and
                   (joined == n or (last and _name_form(joined, n))) for n in NAMES):
                best = (j, joined)
                break
        if best:
            out[i: best[0] + 1] = [best[1]]
            changed = True
        i += 2
    return out if changed else None


def merge_bad(parts, bad, word, rev):
    """Merge each invalid piece with a neighbour (अ-तः → अतः) if the result is valid and still joins back."""
    for i in bad:
        for lo, hi in ((i - 2, i), (i, i + 2)):
            if lo < 0 or hi >= len(parts):
                continue
            cand = parts[:lo] + [sorted(sandhi.join(parts[lo], parts[hi], internal=parts[lo + 1] == "-"))[0][0]] + parts[hi + 1:]
            ok, _ = sandhi.check(word, deva("".join(cand)))
            if ok and not rev.pieces_ok(cand):
                return cand
    return None


def attach_nan(p):
    """Keep the nañ prefix with its word, as Harsha does (अ-शोच्याः → अशोच्याः, अन्-अन्तम् → अनन्तम्)."""
    if not p:
        return p
    parts = split_parts(p)
    out = []
    i = 0
    while i < len(parts):
        if parts[i] in ("a", "an") and i + 2 < len(parts) and parts[i + 1] == "-":
            if parts[i] == "an":  # अन् + उक्त → अनुक्त (6.3.74 तस्मान्नुडचि; no doubling: 8.3.32 is for a pada-final nasal)
                parts[i + 2] = "an" + parts[i + 2]
            else:  # अ + छेद्य → अच्छेद्य (6.1.73 छे च)
                parts[i + 2] = sorted(sandhi.join("a", parts[i + 2], internal=True))[0][0]
            i += 2
            continue
        out.append(parts[i])
        i += 1
    return deva("".join(out))


def review(word, pada, rev):
    """→ (verdict, new pada or None, note)."""
    v, new, note = _review(word, pada, rev)
    if new:
        new = attach_nan(new)
        if new == word:
            return v, None, note
    return v, new, note


def _review(word, pada, rev):
    parts = split_parts(pada)
    names = merge_names(parts)
    if names is not None:
        if len(names) == 1:
            return "name", None, "proper name / saṃjñā kept whole"
        parts = names
    ok, rules = sandhi.check(word, deva("".join(parts)))
    bad = rev.pieces_ok(parts)
    if ok and not bad:
        return ("name" if names else "ok"), (deva("".join(parts)) if names else pada), rules
    # repair 1: pada forms of members
    mf = member_forms(parts)
    if mf:
        cand, why = mf
        ok2, rules2 = sandhi.check(word, deva("".join(cand)))
        if ok2 and not rev.pieces_ok(cand):
            return "member-form", deva("".join(cand)), " ".join(why) + " | " + rules2
    # repair 2: merge broken pieces
    if bad:
        cand = merge_bad(parts, bad, word, rev)
        if cand is not None:
            if len(cand) == 1:
                return "merged-whole", None, "a broken piece merged back; the word is one pada"
            return "merged", deva("".join(cand)), "broken piece merged back"
    reason = ("does not join back by the sandhi rules" if not ok else "") + \
             ("; " if not ok and bad else "") + \
             (("not a word: " + ", ".join(deva(parts[i]) for i in bad)) if bad else "")
    return "withdrawn", None, reason


def main():
    sys.path.insert(0, str(ROOT / "tools"))
    import review_pairs
    rev = Reviewer()
    for (s, p), n in review_pairs.pairs("harsha").items():
        for x in re.split(r"[ \-]", p):
            rev.attested[x] += n
    # names inside Harsha's own padapāṭha and the mūla (प्रजा-पतेः → प्रजापतेः)
    hnames = {}
    for (s, p), n in review_pairs.pairs("harsha").items():
        m = merge_names(split_parts(p))
        if m is not None:
            hnames[s + "\t" + p] = None if len(m) == 1 else deva("".join(m))
    mula = {}
    for f in sorted((ROOT / "docs/data").glob("ch-??.json")):
        for v in json.loads(f.read_text(encoding="utf-8"))["verses"]:
            for line in v["pada"]:
                m = merge_names(split_parts(line))
                if m is not None:
                    mula[line] = deva("".join(m))
    (ROOT / "build/review-names.json").write_text(json.dumps({"harsha": hnames, "mula": mula}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"names kept whole: {len(hnames)} of Harsha's pairs, {len(mula)} mūla lines")
    pairs = review_pairs.pairs("machine")
    out, tally, examples = {}, Counter(), defaultdict(list)
    for (s, p), n in pairs.items():
        verdict, new, note = review(s, p, rev)
        out[s + "\t" + p] = [verdict, new, note]
        tally[verdict] += n
        if len(examples[verdict]) < 400:
            examples[verdict].append((n, s, p, new, note))
    (ROOT / "build/review.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    (ROOT / "build/review-examples.json").write_text(json.dumps(examples, ensure_ascii=False, indent=0), encoding="utf-8")
    tot = sum(tally.values())
    print(f"{len(pairs)} distinct machine pairs, {tot} occurrences")
    for k, v in tally.most_common():
        print(f"  {k:13s} {v:7d}  {100 * v / tot:5.1f}%")


if __name__ == "__main__":
    main()
