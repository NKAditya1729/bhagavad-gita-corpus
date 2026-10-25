"""Collect every [sandhi, pada] pair shown on the site and check each one with tools/sandhi.py.
Usage: python3 tools/review_pairs.py [machine|harsha] [sample-size]"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandhi  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def pairs(kind):
    c = Counter()
    for f in sorted((ROOT / "docs/data").glob("ch-*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        paras = [p for v in d["verses"] for p in v["pre"] + v["bh"]] if "verses" in d else \
            [p for bl in d.values() for b in bl for p in b["paras"]]
        for p in paras:
            for run in p:
                for it in run[1:]:
                    if isinstance(it, list) and ((len(it) > 2) == (kind == "machine")):
                        c[(it[0], it[1])] += 1
    return c


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "machine"
    c = pairs(kind)
    ok = Counter()
    bad = []
    for (s, p), n in c.items():
        good, why = sandhi.check(s, p)
        ok[good] += n
        if not good:
            bad.append((n, s, p))
    tot = sum(c.values())
    print(f"{kind}: {len(c)} distinct pairs, {tot} occurrences; joins back: {ok[True]} ({100 * ok[True] / tot:.1f}%)")
    random.seed(7)
    for n, s, p in random.sample(bad, min(int(sys.argv[2]) if len(sys.argv) > 2 else 40, len(bad))):
        print(f"  {s} → {p}")
    (ROOT / f"build/review-{kind}-fail.json").write_text(json.dumps(sorted(bad, reverse=True), ensure_ascii=False, indent=0), encoding="utf-8")
