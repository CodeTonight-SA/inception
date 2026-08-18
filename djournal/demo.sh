#!/usr/bin/env bash
# dj demo — reproducible. Run: bash demo.sh > demo-transcript.txt 2>&1
set -u
cd "$(dirname "$0")"
J=demo/.djournal
rm -rf demo
mkdir -p demo

say() { echo; echo "$ $*"; }
run() { say "$@"; "$@"; }

run python3 dj.py --version
run python3 dj.py --path "$J" init --name "Founder Decision Journal"
run python3 dj.py --path "$J" log "Ship GRASP as the open-source wedge product, not a paid API first" --why "Proof-layer trust is a network effect: free adoption builds the verifier ecosystem the paid tier rides on." --when 2026-01-12 --falsify "If the first 500 installs retain fewer than 5% for a second logged decision, the wedge thesis is wrong."
run python3 dj.py --path "$J" log "Anchor Merkle roots on Bitcoin via OpenTimestamps instead of running our own chain" --why "Outsourced, censorship-resistant timestamping beats bootstrapping consensus - the maths does the witnessing, not our uptime." --when 2026-01-19 --falsify "If OTS calendar uptime falls below 99.5% in a quarter or median anchor latency exceeds 6h, reconsider self-hosting."
run python3 dj.py --path "$J" log "Cut multi-provider HAL integration from v1 scope" --why "The deterministic provenance floor (cite.verify) is the moat; provider breadth is a convenience layer that can land later without breaking trust." --when 2026-02-02 --falsify "If any design-partner deal is lost specifically for lack of Gemini or Groq support in v1."
run python3 dj.py --path "$J" log "Adopt a permissive licence with a contributor CLA" --why "Permissive licensing maximises fork-and-integrate adoption for a trust layer; the CLA keeps re-licensing optional." --when 2026-02-10 --falsify "If a major enterprise buyer blocks procurement on licence-purity concerns we misjudged."
run python3 dj.py --path "$J" ls
run python3 dj.py --path "$J" proof D-0003
run python3 dj.py --path "$J" verify
run python3 dj.py --path "$J" bundle --out demo/founder-journal.bundle.json
run python3 dj.py check demo/founder-journal.bundle.json
echo
echo "# the witness bundle verifies - TRUE."
echo
echo "# now one byte of the owner journal is tampered (D-0002):"
run python3 demo_tamper.py "$J/journal.jsonl"
run python3 dj.py --path "$J" verify
echo
echo "# the witness bundle is a frozen snapshot - re-check it, still TRUE:"
run python3 dj.py check demo/founder-journal.bundle.json
echo
echo "# done. journal at $J"
