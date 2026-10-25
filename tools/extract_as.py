"""Extract the mūla and Śāṅkarabhāṣya of the Gītā from saved Advaita Sharada pages.

Input : raw/as/bg-<n>.html  (https://advaitasharada.sringeri.net/read/bhagavadgita-bhashya/<n>/)
Output: build/as/ch-<nn>.json — the units in page order, text kept character for character
        (only the soft hyphens that Advaita Sharada inserts for line breaking are removed).
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHY = "­"


def inline_items(fragment):
    """Turn a unit's inner HTML into a list of items: plain text, or {"r": citation}."""
    items = []
    pos = 0
    for m in re.finditer(r'<span class="ullekha-ref"[^>]*>(.*?)</span>', fragment, re.S):
        items.append(fragment[pos:m.start()])
        items.append({"r": re.sub(r"<[^>]+>", "", m.group(1))})
        pos = m.end()
    items.append(fragment[pos:])
    out = []
    for it in items:
        if isinstance(it, str):
            t = re.sub(r"<br\s*/?>", "\n", it)
            t = html.unescape(re.sub(r"<[^>]+>", "", t)).replace(SHY, "")
            if t:
                out.append(t)
        else:
            it["r"] = html.unescape(it["r"]).replace(SHY, "")
            out.append(it)
    return out


def extract(n):
    s = (ROOT / f"raw/as/bg-{n}.html").read_text(encoding="utf-8")
    units = []
    pat = re.compile(
        r'<p class="unit ([^"]*)" id="([^"]+)"[^>]*>(.*?)</p>'
        r'|<div class="unit verse" id="([^"]+)"[^>]*>(.*?)<span class="verse-no"', re.S)
    for m in pat.finditer(s):
        if m.group(4):
            uid, body = m.group(4), m.group(5)
            uv = re.search(r'<p class="uvaca"[^>]*>(.*?)</p>', body, re.S)
            vt = re.search(r'<p class="verse-text"[^>]*>(.*?)</p>', body, re.S)
            lines = [html.unescape(re.sub(r"<[^>]+>", "", l)).replace(SHY, "").strip()
                     for l in re.split(r"<br\s*/?>", vt.group(1))]
            units.append({"id": uid, "kind": "verse",
                          "uvaca": html.unescape(re.sub(r"<[^>]+>", "", uv.group(1))).strip() if uv else "",
                          "lines": lines})
        else:
            kind = m.group(1).split("kind-")[-1] if "kind-" in m.group(1) else m.group(1).split()[-1]
            units.append({"id": m.group(2), "kind": kind, "text": inline_items(m.group(3))})
    return units


def main():
    out = ROOT / "build/as"
    out.mkdir(parents=True, exist_ok=True)
    for n in range(1, 19):
        units = extract(n)
        (out / f"ch-{n:02d}.json").write_text(json.dumps(units, ensure_ascii=False, indent=0), encoding="utf-8")
        kinds = {}
        for u in units:
            kinds[u["kind"]] = kinds.get(u["kind"], 0) + 1
        print(n, kinds)


if __name__ == "__main__":
    main()
