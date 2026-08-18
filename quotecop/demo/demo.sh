#!/usr/bin/env bash
# CITECOP demo — the anti-hallucination button against a real document.
# Real source: Abraham Lincoln, Gettysburg Address (Bliss copy, 1864), public domain.
# Run:  bash demo/demo.sh
cd "$(dirname "$0")/.." || exit 2
PY=python3
DOC=demo/gettysburg_address.txt

echo "════════════════════════════════════════════════════════════════════"
echo "  CITECOP · the anti-hallucination button — demo run"
echo "  source: $DOC  (Lincoln, Gettysburg Address — Bliss copy, 1864)"
echo "════════════════════════════════════════════════════════════════════"
echo
echo ">>> 4 real quotes + 2 fabricated quotes checked against the same source"
echo
$PY quotecop.py --file "$DOC" \
  --quote "Four score and seven years ago" \
  --quote "government of the  people,   by the people, for the people" \
  --quote "we can not dedicate – we can not consecrate – we can not hallow – this ground" \
  --quote "Government of the People, by the People, for the People" \
  --quote "we hold these truths to be self-evident" \
  --quote "Four score and seven years ago our forefathers brought forth"
echo "exit code: $?"
echo
echo ">>> all quotes real — the gate should go GREEN (exit 0)"
echo
$PY quotecop.py --file "$DOC" \
  --quote "Four score and seven years ago" \
  --quote "government of the people, by the people, for the people" \
  --quote "shall not perish from the earth"
echo "exit code: $?"
