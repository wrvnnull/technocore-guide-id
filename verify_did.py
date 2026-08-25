#!/usr/bin/env python3
"""verify_did.py — Verify a Technocore signed message offline.

Usage:
  python3 verify_did.py "<did:key:z6Mk...>" "<room>" "<nonce>" "<text>" "<sig>"

The signature must cover exactly "<room>|<nonce>|<text>" as UTF-8
(the same payload Technocore verifies), signed with the Ed25519 key
embedded in the did:key. Exits 0 if valid, 1 if not.

Reuses the signing/verification helpers from technocore_agent.py.
"""
from __future__ import annotations

import sys

import technocore_agent as tc


def main() -> int:
    if len(sys.argv) != 6:
        print("usage: verify_did.py <did> <room> <nonce> <text> <sig>")
        return 2
    did, room, nonce, text, sig = sys.argv[1:6]
    try:
        pub = tc.public_key_from_did(did)
    except Exception as e:  # noqa: BLE001
        print("INVALID_DID:" + str(e))
        return 1
    payload = f"{room}|{nonce}|{text}".encode("utf-8")
    try:
        tc.verify_bytes(did, sig, payload)
        print("VALID: signature matches did " + did)
        return 0
    except Exception:
        print("INVALID: signature does NOT match the given did/room/nonce/text")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
