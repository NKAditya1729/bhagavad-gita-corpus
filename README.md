# श्रीमद्भगवद्गीता — भाष्यव्याख्यासङ्ग्रहः (Bhagavad Gītā Corpus)

A personal study reader for the Gītā, in the design of the Vedāntic Archive's Maitreyī and Madhu pages
(which follow Advaita Sharada). One verse per page; the site lives in `docs/` (GitHub Pages).

**Live:** https://nkaditya1729.github.io/bhagavad-gita-corpus/

## What it shows

- **भाष्यम्** (choose one, shown below the mūla): शाङ्करभाष्यम् · श्रीधरी · नीलकण्ठी · मधुसूदनी.
- With **शाङ्करभाष्यम्**, the **व्याख्याः** on the bhāṣya can be added (any combination):
  आनन्दगिरिटीका · भाष्यार्कप्रकाशः · भाष्योत्कर्षदीपिका. They open under the bhāṣya, or beside it with **पार्श्वे**.
  The ṭīkā on Śaṅkara's avataraṇikā sits beside the avataraṇikā.
- With श्रीधरी / नीलकण्ठी / मधुसूदनी, **पार्श्वे** puts the mūla on the left and the commentary on the right.
- **पदच्छेदः** switches the whole page — mūla, bhāṣya and every commentary — between the sandhi text and the
  padapāṭha in Harsha's format: sandhi junctions open as spaces, compound members are joined by hyphens
  (देहात्मनोरविवेकादस्यैवं → देह-आत्मनोः अविवेकात् अस्य एवम्).
- Script switcher (देवनागरी, IAST, ಕನ್ನಡ, తెలుగు, தமிழ், മലയാളം), font size, ← → keys for the previous/next verse.

## Sources

| Layer | Source |
|---|---|
| मूलम्, शाङ्करभाष्यम् (with avataraṇikās, upodghāta, colophons) | Advaita Sharada, `advaitasharada.sringeri.net/read/bhagavadgita-bhashya/<n>/` — kept character for character (only its soft hyphens are dropped) |
| आनन्दगिरिटीका, भाष्यार्कप्रकाशः, भाष्योत्कर्षदीपिका, श्रीधरी, नीलकण्ठी, मधुसूदनी | Harsha's अध्ययन-सहकारी, `constrainedrandomvar.github.io/adhyayana-sahakari/reading-gita-<n>.html` and its `lane-gita-<n>-<side>.json` files — taken as they are; OCR problems are not corrected yet |
| padapāṭha of the mūla, and of every word Harsha analysed | Harsha's own sandhi/pada pairs |
| padapāṭha of the remaining words | ByT5-Sanskrit (`chronbmm/sanskrit5-multitask`, mode SLM), compound members from its `Cpd` tags, then **checked against the Aṣṭādhyāyī** (`tools/review.py`: sandhi rejoin by sūtra, real padas, nañ, member forms, names) — see [`review/2026-10-25-pada-review.md`](review/2026-10-25-pada-review.md). Shown with a dotted underline in पद mode |

## Rebuild

```
python3 tools/extract_as.py          # raw/as/bg-<n>.html        → build/as/
python3 tools/extract_harsha.py      # raw/harsha/*               → build/harsha/
~/sanskrit-tools/.venv/bin/python tools/run_byt5.py   # words without a padapāṭha → build/model-out.jsonl
python3 tools/build_site.py          # → docs/data/
~/sanskrit-tools/.venv/bin/python tools/review.py     # Aṣṭādhyāyī check of the machine padapāṭha → build/review*.json
python3 tools/build_site.py          # again, applying the review
```

`raw/` and `build/` are not committed. Download the sources again with the curl loops in `tools/fetch.sh`.
