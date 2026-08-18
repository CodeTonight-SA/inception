# dj — Decision Journal: prove what you decided

A personal CLI where you log consequential decisions — what / why / when /
falsification-condition — and each entry is sealed into an append-only,
content-addressed chain. A journal cannot lie about itself: change one byte and
verification fails. Built for the GRIP/GRASP proof layer (signed decision
records, "don't trust it — witness it").

Zero dependencies (Python stdlib only). Sealing is honest about which primitive
is used: ed25519 asymmetric signatures when the cryptography package is
installed, otherwise a pure-stdlib hmac-sha256 symmetric MAC (the same key
seals and verifies — keep seal.key private).

## Commands

    dj init [--name X] [--path P]              create a journal
    dj log WHAT [--why W] [--when D] [--falsify F]   seal a decision (append-only)
    dj ls                                      list entries
    dj proof [ID]                              shareable proof line (head + id + digest)
    dj verify                                  verify whole chain + ASCII receipt card
    dj bundle [--out F]                        portable witness bundle (public key only)
    dj check FILE                              verify a received bundle
    dj info                                    journal details

    Global: --path P (default ./.djournal) · --no-color · --version

## Witness flow

    # owner shares ONE file:
    dj bundle --out my-journal.bundle.json
    # witness, any machine with python3:
    dj check my-journal.bundle.json     # prints the receipt card; exit 0 = verified

## Demo

    bash demo.sh > demo-transcript.txt 2>&1   # 4 decisions, proof, verify,
                                              # one-byte tamper caught, bundle re-check
