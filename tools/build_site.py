"""Build the site's data files from build/as (mūla + Śāṅkarabhāṣya) and build/harsha (commentaries).

docs/data/index.json             chapter list (number, heading, yoga name, verse count, has-intro)
docs/data/ch-<nn>.json           mūla, padapāṭha and Śāṅkarabhāṣya of one chapter
docs/data/ch-<nn>-<side>.json    one commentary for one chapter, keyed by verse ("0" = upodghāta)

A paragraph is a list of runs [cls, item, …]; an item is text or [sandhi, pada] (+ "m" when machine-made).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pada import Pada  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/data"
SIDES = ["tika", "bhashyarka", "dhanapati", "sridhara", "nilakantha", "madhusudana"]
DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
# The customary names of the chapters (Advaita Sharada prints the name only in the colophon of chapter 1).
YOGA = ["अर्जुनविषादयोगः", "साङ्ख्ययोगः", "कर्मयोगः", "ज्ञानकर्मसंन्यासयोगः", "कर्मसंन्यासयोगः",
        "आत्मसंयमयोगः", "ज्ञानविज्ञानयोगः", "अक्षरब्रह्मयोगः", "राजविद्याराजगुह्ययोगः", "विभूतियोगः",
        "विश्वरूपदर्शनयोगः", "भक्तियोगः", "क्षेत्रक्षेत्रज्ञविभागयोगः", "गुणत्रयविभागयोगः", "पुरुषोत्तमयोगः",
        "दैवासुरसम्पद्विभागयोगः", "श्रद्धात्रयविभागयोगः", "मोक्षसंन्यासयोगः"]


def as_paras(text_items, pada, cls=""):
    """Advaita Sharada unit text → paragraphs (split at line breaks) of runs."""
    paras = [[]]
    for it in text_items:
        if isinstance(it, dict):
            paras[-1].append(it)
            continue
        for i, chunk in enumerate(it.split("\n")):
            if i:
                paras.append([])
            paras[-1].extend(pada.items(chunk))
    out = []
    for items in paras:
        runs = []
        for x in items:
            if isinstance(x, dict):
                runs.append(["R", x["r"]])
            elif runs and runs[-1][0] == cls:
                if isinstance(x, str) and isinstance(runs[-1][-1], str):
                    runs[-1][-1] += x
                else:
                    runs[-1].append(x)
            else:
                runs.append([cls, x])
        if any(isinstance(x, list) or x.strip() for r in runs for x in r[1:]):
            out.append(runs)
    return out


def lane_paras(paras, pada):
    out = []
    for p in paras:
        runs = []
        for run in p:
            new = [run[0]]
            for it in run[1:]:
                if isinstance(it, list):
                    new.append(pada.pair(*it))
                else:
                    for x in pada.items(it):
                        if isinstance(x, str) and isinstance(new[-1], str) and len(new) > 1:
                            new[-1] += x
                        else:
                            new.append(x)
            runs.append(new)
        out.append(runs)
    return out


def chapter(n, pada):
    units = json.loads((ROOT / f"build/as/ch-{n:02d}.json").read_text(encoding="utf-8"))
    harsha = json.loads((ROOT / f"build/harsha/ch-{n:02d}.json").read_text(encoding="utf-8"))
    verses = {}
    order = []

    def get(v):
        if v not in verses:
            verses[v] = {"v": v, "uvaca": "", "lines": [], "pada": [], "pre": [], "bh": []}
            order.append(v)
        return verses[v]

    last = 0
    colophon = None
    for u in units:
        m = re.match(r"BG_C\d+_V(\d+)", u["id"])
        if u["kind"] == "colophon":
            colophon = as_paras(u["text"], pada)
            continue
        if m:
            v = int(m.group(1))
            last = v
            rec = get(v)
            if u["kind"] == "verse":
                rec["uvaca"] = u["uvaca"]
                rec["lines"] = u["lines"]
                hm = harsha["mula"].get(f"{n}.{v}")
                rec["pada"] = hm["pada"] if hm else []
            elif u["kind"] == "avatarika":
                rec["pre"] += as_paras(u["text"], pada)
            else:
                rec["bh"] += as_paras(u["text"], pada)
        else:
            # chapter prose: before the first verse it is an upodghāta, after a verse it continues that verse's bhāṣya
            get(last)["bh"] += as_paras(u["text"], pada)
    # commentaries may have an upodghāta even where Śaṅkara has none
    if f"{n}.0" in harsha["comm"]:
        get(0)
    order.sort()
    head = re.search(r'<p class="chapter-head[^"]*"[^>]*>(.*?)</p>',
                     (ROOT / f"raw/as/bg-{n}.html").read_text(encoding="utf-8")).group(1)
    data = {"ch": n, "head": head, "name": YOGA[n - 1],
            "verses": [verses[v] for v in order], "colophon": colophon or []}
    comm = {}
    for side in SIDES:
        c = {}
        for key, sides in harsha["comm"].items():
            if side not in sides:
                continue
            v = key.split(".")[1]
            c[v] = [{"zone": b["zone"], "paras": lane_paras(b["paras"], pada)} for b in sides[side]]
        comm[side] = c
    return data, comm


REVIEW = ROOT / "build/review.json"
NAMES = ROOT / "build/review-names.json"


def apply_review(data, comm, review, names):
    """Apply tools/review.py: a machine pada that passed stays, a repaired one is replaced, a withdrawn one goes;
    a proper name in Harsha's padapāṭha or the mūla is joined back into one word."""
    def fix(paras):
        for p in paras:
            for run in p:
                for i, it in enumerate(run[1:], 1):
                    if not isinstance(it, list):
                        continue
                    key = it[0] + "\t" + it[1]
                    if len(it) > 2 and key in review:
                        verdict, new, _ = review[key]
                        if new is None or verdict in ("withdrawn", "merged-whole"):
                            run[i] = it[0]
                        else:
                            run[i] = [it[0], new, "m"]
                    elif key in names["harsha"]:
                        new = names["harsha"][key]
                        run[i] = it[0] if new is None else [it[0], new]
            # neighbouring plain strings merge again
            for run in p:
                k = 1
                while k < len(run) - 1:
                    if isinstance(run[k], str) and isinstance(run[k + 1], str):
                        run[k] += run.pop(k + 1)
                    else:
                        k += 1
    for v in data["verses"]:
        fix(v["pre"])
        fix(v["bh"])
        v["pada"] = [names["mula"].get(line, line) for line in v["pada"]]
    for c in comm.values():
        for blocks in c.values():
            for b in blocks:
                fix(b["paras"])


def main():
    pada = Pada()
    review = json.loads(REVIEW.read_text(encoding="utf-8")) if REVIEW.exists() else {}
    names = json.loads(NAMES.read_text(encoding="utf-8")) if NAMES.exists() else {"harsha": {}, "mula": {}}
    print("model readings:", dict(pada.how))
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for n in range(1, 19):
        data, comm = chapter(n, pada)
        if review:
            apply_review(data, comm, review, names)
        (OUT / f"ch-{n:02d}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        for side, c in comm.items():
            (OUT / f"ch-{n:02d}-{side}.json").write_text(json.dumps(c, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        index.append({"ch": n, "head": data["head"], "name": data["name"],
                      "verses": [v["v"] for v in data["verses"]],
                      "sides": {s: sorted(int(k) for k in comm[s]) for s in SIDES}})
        print(n, data["head"], data["name"], len(data["verses"]))
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(dict(pada.stats))


if __name__ == "__main__":
    main()
