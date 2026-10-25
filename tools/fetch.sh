#!/bin/zsh
# Download the source pages into raw/ (run from the repository root).
set -e
mkdir -p raw/as raw/harsha
H=https://constrainedrandomvar.github.io/adhyayana-sahakari
for n in $(seq 1 18); do
  curl -sfL -o raw/as/bg-$n.html https://advaitasharada.sringeri.net/read/bhagavadgita-bhashya/$n/
  curl -sfL -o raw/harsha/reading-gita-$n.html $H/reading-gita-$n.html
  for s in tika bhashyarka dhanapati sridhara nilakantha madhusudana; do
    curl -sfL -o raw/harsha/lane-gita-$n-$s.json $H/lane-gita-$n-$s.json
  done
  sleep 1
done
