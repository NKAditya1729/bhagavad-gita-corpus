"""Review Harsha's own padapāṭha (the pairs not marked "m") by the same Aṣṭādhyāyī checks as tools/review.py.

Harsha's splits are trusted where they join back by the sandhi rules; only a clear structural fault (a lone अन्/अ,
a one-letter piece) is acted on there. Where a split does not join back, it is repaired:
  ending — the pada lacks the word's ending (द्वन्द्वशब्देन → "द्वन्द्व-शब्द"): the ending is restored from the word
  member — a member is in dictionary form (ऋच्-, सामन्-, षष्-): put in pada form (8.2.30, 8.2.7, 8.2.39 …)
  spacing — " - " around a hyphen
If nothing passes, the word goes to the model (tools/run_byt5.py CTX) and that split is reviewed like any machine split
(build/review.json). A pada whose only difference from the word is a corrected spelling (Harsha's emendation of the OCR)
is kept and listed.

Run with ~/sanskrit-tools/.venv/bin/python. Writes build/review-harsha.json and build/need-harsha-model.json.
"""
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review as R  # noqa: E402
import review_pairs  # noqa: E402
import sandhi  # noqa: E402
from sandhi import deva, slp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POSTFIX = {"o": "aH"}


def restore_ending(word, parts):
    """The pada stops at a stem: give its last piece the word's own ending."""
    w = sandhi.norm(slp(word))
    for joined, _ in sorted(sandhi.rejoin(parts), key=lambda t: len(t[1])):
        j = sandhi.norm(joined)
        for cut in (0, 1, 2):  # the stem's last sound may change before the ending (त्व + आत् → त्वात्; आत्मन् + आ → आत्मना)
            stem = j[: len(j) - cut]
            if not (cut < len(parts[-1]) and w.startswith(stem) and 0 < len(w) - len(stem) <= 8 and len(w) > len(j) - cut):
                continue
            rest = w[len(stem):]
            last = parts[-1][: len(parts[-1]) - cut] + rest
            cand = _finish(word, parts, last)
            if cand:
                return cand
    return None


def _finish(word, parts, last):
    """Put the restored last piece in pausal form and check the whole pada again."""
    if last.endswith("o"):
        last = last[:-1] + "aH"
    elif last.endswith("M"):
        last = last[:-1] + "m"
    cand = parts[:-1] + [last]
    ok, rules = sandhi.check(word, deva("".join(cand)))
    return (cand, rules) if ok else None


def structural_faults(parts):
    bad = []
    for i in range(0, len(parts), 2):
        x = parts[i]
        nxt_sep = parts[i + 1] if i + 1 < len(parts) else ""
        if x in ("an", "a") and nxt_sep == " ":
            bad.append(i)  # nañ standing as a word (अन् अवलोकयन्)
        elif re.fullmatch(r"[^aAiIuUfFxXeEoO]+", x):
            bad.append(i)
        elif len(x) == 1 and x not in ("a", "A", "u", "I", "U") and x not in R.INDECL and nxt_sep != "-":
            bad.append(i)
        elif x in ("e", "E", "O"):  # (आ- is a member in its own right: 2.1.13 आङ् मर्यादाभिविध्योः, 2.2.18 कुगतिप्रादयः)
            bad.append(i)
    return bad


def review_one(word, pada, rev):
    pada2 = re.sub(r"\s*-\s*", "-", pada).strip()
    parts = R.split_parts(pada2)
    ok, rules = sandhi.check(word, pada2)
    if ok:
        bad = structural_faults(parts)
        if not bad:
            return ("ok" if pada2 == pada else "spacing"), pada2, rules
        cand = R.merge_bad(parts, bad, word, rev)
        if cand is not None:
            new = R.attach_nan(deva("".join(cand)))
            return "merged", (None if new == word else new), "broken piece joined back"
        return "model", None, "piece is not a pada: " + ", ".join(deva(parts[i]) for i in bad)
    # repairs
    tries = [parts]
    mf = R.member_forms(parts)
    if mf:
        tries.append(mf[0])
    for t in tries:
        ok, rules = sandhi.check(word, deva("".join(t)))
        if ok and t is not parts:
            return "member-form", deva("".join(t)), " ".join(mf[1]) + " | " + rules
        e = restore_ending(word, t)
        if e:
            why = ("ending restored; " + " ".join(mf[1]) if t is not parts else "ending restored")
            return ("ending" if t is parts else "ending+member"), deva("".join(e[0])), why + " | " + e[1]
    # Harsha's emendation of a misprint: the pada differs from the word only in a letter or two
    j = min((sandhi.norm(x) for x, _ in sandhi.rejoin(tries[-1])), key=lambda x: abs(len(x) - len(slp(word))))
    w = sandhi.norm(slp(word))
    if abs(len(j) - len(w)) <= 1 and not (j.startswith(w) or w.startswith(j)) and SequenceMatcher(None, j, w).ratio() >= 0.85:
        return "emended", pada2, "Harsha's emended reading of the printed word"
    return "model", None, "does not join back by the sandhi rules"


def main():
    rev = R.Reviewer()
    pairs = review_pairs.pairs("harsha")
    for (s, p), n in pairs.items():
        for x in re.split(r"[ \-]", p):
            rev.attested[x] += n
    out, tally = {}, Counter()
    for (s, p), n in pairs.items():
        verdict, new, note = review_one(s, p, rev)
        if verdict != "ok":
            out[s + "\t" + p] = [verdict, new, note]
        tally[verdict] += n
    (ROOT / "build/review-harsha.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    need = sorted({k.split("\t")[0] for k, v in out.items() if v[0] == "model"}, key=len)
    (ROOT / "build/need-harsha-model.json").write_text(json.dumps(need, ensure_ascii=False), encoding="utf-8")
    tot = sum(tally.values())
    print(f"{len(pairs)} distinct Harsha pairs, {tot} occurrences")
    for k, v in tally.most_common():
        print(f"  {k:14s} {v:7d}  {100 * v / tot:5.2f}%")
    print("to the model:", len(need))


if __name__ == "__main__":
    main()
