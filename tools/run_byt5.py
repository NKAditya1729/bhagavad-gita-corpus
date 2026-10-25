"""Run the ByT5-Sanskrit model (chronbmm/sanskrit5-multitask, mode SLM) on every word that has no
padapāṭha yet. Resumable: appends one JSON line per word to build/model-out.jsonl.

Run with ~/sanskrit-tools/.venv/bin/python (it has torch, transformers and the model).
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path.home() / "sanskrit-tools"))
from analyze import Analyzer, to_iast  # noqa: E402

NEED = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "build/need-model.json")
MODE = sys.argv[2] if len(sys.argv) > 2 else "SLM"  # SLM: segments+lemmas+tags; S: segmentation only; CTX: SLM after "iti"
OUT = ROOT / ("build/model-s.jsonl" if MODE == "S" else "build/model-out.jsonl")
BATCH = 96


def main():
    words = json.loads(NEED.read_text(encoding="utf-8"))
    done = set()
    if OUT.exists() and MODE != "CTX":
        for line in OUT.read_text(encoding="utf-8").splitlines():
            done.add(json.loads(line)["w"])
    todo = [w for w in words if w not in done]
    print(f"{len(done)} done, {len(todo)} to go", flush=True)
    a = Analyzer()
    t0 = time.time()
    with OUT.open("a", encoding="utf-8") as f:
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            iast = [to_iast(w) for w in chunk]
            if MODE == "CTX":
                # Alone, some long compounds come back as bare stems ("__sajātīya_U …"); after a word they do not.
                res = [r.split(" ", 1)[1] if r.startswith("iti_iti_") and " " in r else r
                       for r in a.run("SLM", ["iti " + x for x in iast])]
            else:
                res = a.run(MODE, iast)
            for w, x in zip(chunk, res):
                rec = {"w": w, "s": x} if MODE == "S" else {"w": w, "slm": x, "s": ""}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if (i // BATCH) % 20 == 0:
                el = time.time() - t0
                print(f"{i + len(chunk)}/{len(todo)}  {el:.0f}s  eta {el / (i + len(chunk)) * (len(todo) - i - len(chunk)) / 60:.0f} min", flush=True)


if __name__ == "__main__":
    main()
