"""Audit the पद view of the whole built site: every unbroken piece (no hyphen) of 7+ letters is classed as
single   — the model read it as one word (or a word with a taddhita suffix such as -त्व, -ता)
missed   — the model split it, but the split was rejected by the checks in pada.py
unseen   — the model never saw it
Writes build/audit-pada.json with all missed/unseen pieces and their counts."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pada  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORD = re.compile("[ऀ-ॣ॰-ॿ‌‍]+")
slm = {}
for l in (ROOT / "build/model-out.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(l)
    slm[r["w"]] = r["slm"]
seg = {}
for l in (ROOT / "build/model-s.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(l)
    seg[r["w"]] = r["s"]


def nsegs(w):
    if w in slm and "_U" not in slm[w]:
        items = slm[w].split(" ")
        return sum(1 for i in items if i.split("_")[1] not in pada.SUFFIX_LEMMAS) if all(len(i.split("_")) == 3 for i in items) else 2
    if w in seg and seg[w].strip("_"):
        return len([x for x in seg[w].split("_") if x and not re.match(r"^t(v|ā)", x)])
    if w in slm:
        return 2  # the model's output was empty: not resolved
    return None


def pieces(item):
    if isinstance(item, str):
        return WORD.findall(item)
    return [w for part in item[1].split() if "-" not in part for w in WORD.findall(part)]


cls, ex = Counter(), {"missed": Counter(), "unseen": Counter()}
for f in sorted((ROOT / "docs/data").glob("ch-*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    paras = [p for v in d["verses"] for p in v["pre"] + v["bh"]] if "verses" in d else \
        [p for bl in d.values() for b in bl for p in b["paras"]]
    for p in paras:
        for run in p:
            for it in run[1:]:
                for w in pieces(it):
                    if len(w) < 7:
                        continue
                    n = nsegs(w)
                    k = "unseen" if n is None else ("single" if n <= 1 else "missed")
                    cls[k] += 1
                    if k in ex:
                        ex[k][w] += 1
print(dict(cls))
(ROOT / "build/audit-pada.json").write_text(json.dumps({k: c.most_common() for k, c in ex.items()}, ensure_ascii=False, indent=0), encoding="utf-8")
for k, c in ex.items():
    print(k, len(c), "distinct; top:", [w for w, _ in c.most_common(25)])
