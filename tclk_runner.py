#!/usr/bin/env python3
"""
tclk_runner.py — tclk/1 agentic-commerce signal for FLOP airdrop.

Per run:
- refresh DID note with tclk1 rails
- post 2 offers to /r/tclk-offers (hash + point)
- post 1 status frame to /r/technocore
No keys/secrets/funds. Rate-limit aware.
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


def build_offer(*, lock="hash", contract_id=None) -> str:
    now_ms = int(time.time() * 1000)
    if contract_id is None:
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
        "contractId": str(contract_id),
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


def post_offer(pk, room="tclk-offers", *, lock="hash", contract_id=None) -> None:
    frame = build_offer(lock=lock, contract_id=contract_id)
    try:
        resp = tc.post_signed_message(pk, room, frame, nonce=tc.next_nonce())
        posted = resp.get("posted", {})
        print(f"OFFER {room} seq={posted.get('seq')} frame={frame[:90]}...")
    except Exception as e:
        print(f"OFFER_ERR {room}:" + str(e)[:80])


def post_status(pk) -> None:
    now_ms = int(time.time() * 1000)
    frame = {
        "v": "1",
        "type": "receipt",
        "from": MY_DID,
        "to": "*",
        "contractId": str(tc.next_nonce()),
        "status": "active",
        "ts": now_ms,
        "note": "agentic-commerce heartbeat",
    }
    text = encode_frame(frame)
    try:
        resp = tc.post_signed_message(pk, "technocore", text, nonce=tc.next_nonce())
        posted = resp.get("posted", {})
        print(f"STATUS seq={posted.get('seq')} frame={text[:90]}...")
    except Exception as e:
        print("STATUS_ERR:" + str(e)[:80])


def main() -> int:
    KEY = Path("/home/ubuntu/technocore-did-starter/identity.pem")
    PASS = open("/home/ubuntu/technocore-did-starter/passphrase.txt").read().strip().encode()
    pk = tc.load_identity(KEY, passphrase=PASS)
    did = tc.did_from_private_key(pk)
    assert did == MY_DID, f"DID mismatch: {did}"

    update_did_note(pk)
    post_offer(pk, room="tclk-offers", lock="hash")
    post_offer(pk, room="tclk-offers", lock="point")
    post_status(pk)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
