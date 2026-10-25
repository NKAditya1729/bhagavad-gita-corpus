"""List what the पद view would still show as an unbroken long word, across the whole built site.

A piece is a space-separated word of the pada text (or a plain word that has no pada). It is a leftover when it
has no hyphen and is at least MIN letters long. Writes build/need-model-2.json (pieces the model has not seen)
and prints a report.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 9
WORD = re.compile("[ऀ-ॣ॰-ॿ‌‍]+")


def pieces(item):
    if isinstance(item, str):
        return WORD.findall(item)
    return [w for part in item[1].split() for w in WORD.findall(part) if "-" not in part]


def walk_paras(paras, out, where):
    for p in paras:
        for run in p:
            for it in run[1:]:
                for w in pieces(it):
                    if len(w) >= MIN:
                        out[w] += 1
                        where.setdefault(w, set()).add(where_now[0])


where_now = [""]
out, where = Counter(), {}
for f in sorted((ROOT / "docs/data").glob("ch-*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    side = f.stem[6:] or "bhashya"
    where_now[0] = side
    if isinstance(d, dict) and "verses" in d:
        for v in d["verses"]:
            walk_paras(v["pre"] + v["bh"], out, where)
    else:
        for blocks in d.values():
            for b in blocks:
                walk_paras(b["paras"], out, where)
seen = set()
mo = ROOT / "build/model-out.jsonl"
if mo.exists():
    seen = {json.loads(l)["w"] for l in mo.read_text(encoding="utf-8").splitlines()}
new = sorted((w for w in out if w not in seen), key=len)
(ROOT / "build/need-model-2.json").write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
by_side = Counter()
for w, c in out.items():
    for s in where[w]:
        by_side[s] += c
print(f"leftover pieces ≥{MIN} letters: {len(out)} distinct, {sum(out.values())} occurrences; not yet modelled: {len(new)}")
print("by text:", dict(by_side))
print("longest:", sorted(out, key=len)[-15:])
