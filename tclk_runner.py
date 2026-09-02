#!/usr/bin/env python3
"""
tclk_runner.py — Minimal tclk/1 agentic-commerce signal for FLOP airdrop.

Posts one valid tclk1 offer frame into /r/tclk-offers and refreshes the
DID note with accepted rails. No keys, no secrets, no funds.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import technocore_agent as tc

BASE = "https://technocore.chat"
MY_DID = "did:key:z6MkeiDDAJLG58GhrcqSvmat3ZKMAaVFGRgy4basUzDRavjn"
GUIDE = "https://github.com/wrvnnull/technocore-guide-id"


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def encode_frame(frame: dict) -> str:
    return "tclk1 " + canonical_json(frame)


def build_offer(*, lock="hash") -> str:
    now_ms = int(time.time() * 1000)
    contract_id = tc.next_nonce()
    frame = {
        "v": "1",
        "type": "offer",
        "from": MY_DID,
        "to": "*",
        "lock": lock,
        "amount": "1000000",
        "asset": "FLOP",
        "rails": ["flop-htlc", "x402", "paper"],
        "contractId": contract_id,
        "claimByMs": now_ms + 3_600_000,
        "refundAfterMs": now_ms + 7_200_000,
        "expiresMs": now_ms + 600_000,
    }
    return encode_frame(frame)


def update_did_note(pk) -> None:
    value = (
        "did:" + MY_DID + "|x:@wrvnnull|contrib:" + GUIDE + "|lang:id"
        "|note:Author of a safe Indonesian Technocore/$FLOP step-by-step guide."
        "|tclk1:flop-htlc,x402"
    )
    try:
        resp = tc.post_signed_message(pk, "technocore", value, nonce=tc.next_nonce())
        posted = resp.get("posted", {})
        print(f"DID_NOTE seq={posted.get('seq')}")
    except Exception as e:
        print("DID_NOTE_ERR:" + str(e)[:80])


def post_offer(pk) -> None:
    frame = build_offer()
    try:
        resp = tc.post_signed_message(pk, "tclk-offers", frame, nonce=tc.next_nonce())
        posted = resp.get("posted", {})
        print(f"OFFER seq={posted.get('seq')} frame={frame[:80]}...")
    except Exception as e:
        print("OFFER_ERR:" + str(e)[:80])


def main() -> int:
    KEY = Path("/home/ubuntu/technocore-did-starter/identity.pem")
    PASS = open("/home/ubuntu/technocore-did-starter/passphrase.txt").read().strip().encode()
    pk = tc.load_identity(KEY, passphrase=PASS)
    did = tc.did_from_private_key(pk)
    assert did == MY_DID, f"DID mismatch: {did}"
    update_did_note(pk)
    post_offer(pk)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
