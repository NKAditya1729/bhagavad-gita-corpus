"""Extract the six commentaries (and the mūla padapāṭha) from Harsha's अध्ययन-सहकारी Gītā pages.

Input : raw/harsha/reading-gita-<n>.html and raw/harsha/lane-gita-<n>-<side>.json
        (https://constrainedrandomvar.github.io/adhyayana-sahakari/)
Output: build/harsha/ch-<nn>.json
  mula[v]  = {speaker, lines (sandhi), pada (padapāṭha lines)}
  comm[v][side] = [ {zone, label, paras} ]   v = "<ch>.<verse>", or "<ch>.0" for an upodghāta
  A para is a list of runs [cls, item, …]; an item is plain text or [sandhi, pada].
  cls: "" vyākhyā · "P" pratīka · "A" avataraṇikā · "M" maṅgala · "R" citation
"""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw/harsha"
SIDES = ["tika", "bhashyarka", "dhanapati", "sridhara", "nilakantha", "madhusudana"]
VOID = {"br", "img", "hr", "meta", "link", "input", "wbr"}


class Node:
    __slots__ = ("tag", "attrs", "kids", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.kids, self.parent = tag, dict(attrs), [], parent

    @property
    def cls(self):
        return (self.attrs.get("class") or "").split()

    def text(self):
        return "".join(k if isinstance(k, str) else k.text() for k in self.kids)

    def iter(self):
        for k in self.kids:
            if isinstance(k, Node):
                yield k
                yield from k.iter()

    def find_all(self, pred):
        return [n for n in self.iter() if pred(n)]


class Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.kids.append(data)


def parse(s):
    b = Builder()
    b.feed(s)
    return b.root


def ancestors(n):
    while n.parent is not None:
        n = n.parent
        yield n


# ---------- commentary text → paragraphs of runs ----------

CLASS_CODE = {"tk-prat": "P", "tk-ava": "A", "tk-mng": "M", "tk-vy": "", "cite": "R"}


def word_item(w):
    """A .w span: [sandhi, pada] if it carries both forms, else its text."""
    sj = [k for k in w.kids if isinstance(k, Node) and "bhsj" in k.cls]
    sp = [k for k in w.kids if isinstance(k, Node) and "bhsp" in k.cls]
    if sj and sp:
        return [sj[0].text(), sp[0].text()]
    return None


def block_paras(node):
    paras = [[]]

    def emit(code, item):
        para = paras[-1]
        if para and para[-1][0] == code:
            run = para[-1]
            if isinstance(item, str) and isinstance(run[-1], str):
                run[-1] += item
            else:
                run.append(item)
        else:
            para.append([code, item])

    def walk(n, code):
        for k in n.kids:
            if isinstance(k, str):
                if k:
                    emit(code, k)
                continue
            c = k.cls
            if "tk-pb" in c or k.tag == "br":
                if paras[-1]:
                    paras.append([])
                continue
            if k.tag == "div" and "tk" in c and paras[-1]:
                paras.append([])
            if "w" in c:
                wi = word_item(k)
                if wi:
                    emit(code, wi)
                    continue
            ncode = code
            for cc, v in CLASS_CODE.items():
                if cc in c:
                    ncode = v
            walk(k, ncode)

    walk(node, "")
    return [p for p in paras if any(isinstance(i, list) or i.strip() for r in p for i in r[1:])]


def lane_block(h):
    tree = parse(h)
    sz = tree.find_all(lambda n: "side-zone" in n.cls)
    if not sz:
        return None
    sz = sz[0]
    label = sz.find_all(lambda n: "zlabel" in n.cls)
    body = sz.find_all(lambda n: "tika" in n.cls)
    return {"label": label[0].text().strip() if label else "", "paras": block_paras(body[0] if body else sz)}


# ---------- page: mūla and placeholder positions ----------

def extract(n):
    page = parse((RAW / f"reading-gita-{n}.html").read_text(encoding="utf-8"))
    lanes = {}
    for side in SIDES:
        f = RAW / f"lane-gita-{n}-{side}.json"
        lanes[side] = json.loads(f.read_text(encoding="utf-8"))["h"] if f.exists() else []
    mula, comm = {}, {}
    for sec in page.find_all(lambda x: x.tag == "section" and x.attrs.get("id", "").startswith("v-")):
        sid = sec.attrs["id"][2:]
        key = f"{n}.0" if sid == "intro" else sid
        sp = sec.find_all(lambda x: "speaker" in x.cls)
        vj = sec.find_all(lambda x: "vjoin" in x.cls)
        vp = sec.find_all(lambda x: "vpada" in x.cls)
        if vj:
            lines = [l.text().strip() for l in vj[0].find_all(lambda x: "jl" in x.cls)]
            pada, cur = [], []
            for k in vp[0].kids if vp else []:
                if isinstance(k, Node) and "dnd" in k.cls:
                    pada.append(" ".join(cur) + " " + k.text().strip())
                    cur = []
                elif isinstance(k, Node) and "w" in k.cls:
                    cur.append(k.text().strip())
            if cur:
                pada.append(" ".join(cur))
            mula[key] = {"speaker": sp[0].text().strip() if sp else "", "lines": lines, "pada": pada}
        for ph in sec.find_all(lambda x: "lzl" in x.cls):
            side, idx = ph.attrs["data-lz"].split(":")
            h = lanes[side][int(idx)] if int(idx) < len(lanes[side]) else None
            if not h or not h.lstrip().startswith('<div class="side-zone"'):
                continue
            blk = lane_block(h)
            if not blk or not blk["paras"]:
                continue
            zone = "pre" if any("pre-zone" in a.cls for a in ancestors(ph)) else "main"
            blk["zone"] = zone
            comm.setdefault(key, {}).setdefault(side, []).append(blk)
    return {"mula": mula, "comm": comm}


def main():
    out = ROOT / "build/harsha"
    out.mkdir(parents=True, exist_ok=True)
    for n in range(1, 19):
        d = extract(n)
        (out / f"ch-{n:02d}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        cnt = {s: sum(1 for v in d["comm"].values() if s in v) for s in SIDES}
        print(n, "mula", len(d["mula"]), "verses-with:", cnt)


if __name__ == "__main__":
    main()
