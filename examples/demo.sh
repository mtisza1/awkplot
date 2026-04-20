#!/usr/bin/env bash
# awkplot demo — uses synthetic data so it runs without any real files.
# Run from the repo root: bash examples/demo.sh

set -euo pipefail

AWKPLOT="$(dirname "$0")/../awkplot"

echo "=== 1. Histogram of random integers ==="
awk 'BEGIN { srand(42); for (i=1;i<=200;i++) print int(rand()*50) }' \
  | "$AWKPLOT" -p hist -t "Random ints 0-49"

echo
echo "=== 2. Bar chart: letter frequencies in this script ==="
grep -o '[a-z]' "$0" \
  | sort | uniq -c | sort -rn | head -10 \
  | awk '{print $2, $1}' \
  | "$AWKPLOT" -p bar -t "Top 10 letters" -H

echo
echo "=== 3. Scatter: y = x^2 + noise ==="
awk 'BEGIN { srand(7); for (x=1;x<=60;x++) print x, x*x + (rand()-0.5)*80 }' \
  | "$AWKPLOT" -p scatter -s 20:60 -c cyan -t "y = x^2 + noise"

echo
echo "=== 4. Line: simple sine wave ==="
awk 'BEGIN { pi=3.14159265; for (i=0;i<=100;i++) printf "%.4f\n", sin(i*pi/50) }' \
  | "$AWKPLOT" -p line -t "sin(x)" -s 15:60

echo
echo "=== 5. dry-run preview ==="
"$AWKPLOT" --dry-run -F, -H -p scatter -c red -s 20:60 '{print $2,$5}' data.csv
