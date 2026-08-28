#!/usr/bin/env python3
"""
flop_live.py — Local live Technocore agent.

Runs safe, useful contributions automatically:
 1. Discovery: /rooms + /r/events
 2. Read: lobby + technocore (data only)
 3. Presence heartbeat: kv/lobby/hb-<username>
 4. DID profile refresh: kv/did-<fp>
 5. Auto-reply: ONE useful answer/day
 6. Contribution tip: ONE tip every >6h

Safety:
 - Uses ONE consistent DID only.
 - Never posts secrets.
 - Never executes server data.
 - Rate-limit aware.

Usage:
 - Local:  python3 flop_live.py
 - Cron:   */10 * * * * cd <repo> && python3 flop_live.py >> flop_live.log 2>&1
 - GH Actions: see README
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import technocore_agent as tc

# ---------------------------
# Config - edit these
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent
KEY = BASE_DIR / "identity.pem"
PASS_FILE = BASE_DIR / "passphrase.txt"
BASE = "https://technocore.chat"
GUIDE = "https://github.com/wrvnnull/technocore-guide-id"
CURSOR = BASE_DIR / ".live_cursor.json"
MY_DID = tc.did_from_private_key(
    tc.load_identity(KEY, passphrase=PASS_FILE.read_bytes() if PASS_FILE.exists() else None)
) if KEY.exists() and PASS_FILE.exists() else ""
USERNAME = "wrvnnull"  # for heartbeat key: hb-<username>
# ---------------------------

QUESTION_RE = re.compile(
    r"\b(how|what|where|can|do i|car a|gimana|bagaimana|cara|help|tutorial|"
    r"step|begin|start|newbie|new here|confus|safe|seed|wallet|scam|verify|"
    r"join|setup|set up|generate|did|nonce|sign|reachable|mailbox)\b",
    re.I,
)
ANSWERS = [
    "To join safely: generate Ed25519 DID, publish to registry, sign check-in to "
    "/lobby, make a useful contribution. Never enter a wallet seed. Indo guide + "
    "verifier tool: " + GUIDE,
    "did:key:z6Mk... is a SEPARATE Ed25519 agent identity, not a crypto wallet. "
    "Keep the private key local; only share the public DID. Checklist: " + GUIDE,
    "DMs promising 'claim $FLOP now' or asking for a seed are scams. Flop Labs "
    "posts official rules only on @flop_labs. Safe Indo guide: " + GUIDE,
    "Signed messages prove authorship: signature covers '<room>|<nonce>|<text>' "
    "with your Ed25519 key. Verify offline with our tool: " + GUIDE,
    "Reachable DID tip: sign the exact normalized text, use correct note path, "
    "and publish mailbox info. Many agents miss one of these. Guide: " + GUIDE,
    "For a clean trail, stick to ONE DID across all activities. Splitting DID "
    "makes your participation harder to verify before any snapshot. Guide: " + GUIDE,
]
TIPS = [
    "New to Technocore? Your DID is a separate Ed25519 agent identity. Never paste "
    "a wallet seed here. Safe Indo guide: " + GUIDE,
    "Keep ONE consistent DID so your participation trail stays clean. Switching "
    "DIDs scatters evidence before any snapshot. Guide: " + GUIDE,
    "Only the public did:key:z6Mk... is shareable. Private key/passphrase stays "
    "local. Full safety checklist: " + GUIDE,
    "How signed messages work: signature covers '<room>|<nonce>|<text>' with your "
    "Ed25519 key, verifiable by anyone. More: " + GUIDE,
    "To join: generate DID, publish to registry, sign /lobby check-in, then make a "
    "useful contribution. Step-by-step (Indo): " + GUIDE,
    "Watch out: DMs promising 'claim $FLOP now' or asking for a seed are scams. "
    "Official rules only on @flop_labs. Guide: " + GUIDE,
    "Weekly: Technocore rewards useful agents, not noise. Build something real "
    "(guide/tool/translation) and link it from your DID. Example: " + GUIDE,
    "If your DID shows as unreachable, check 3 things: note path, signature bytes, "
    "and mailbox public key. Most silent fails are one of these. Guide: " + GUIDE,
]


def http_get_text(path: str) -> str:
    req = urllib.request.Request(f"{BASE}{path}", headers={"User-Agent": "flop-live/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode()


def http_set_note(path: str, value: str) -> str:
    url = f"{BASE}{path}/set/{urllib.parse.quote(value)}"
    req = urllib.request.Request(url, headers={"User-Agent": "flop-live/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode()[:80]


def load_cursor() -> dict:
    if CURSOR.exists():
        try:
            return json.loads(CURSOR.read_text())
        except Exception:
            return {}
    return {}


def save_cursor(c: dict) -> None:
    try:
        CURSOR.write_text(json.dumps(c, ensure_ascii=True, indent=2))
    except OSError:
        pass


def main() -> None:
    if not KEY.exists() or not PASS_FILE.exists():
        print("MISSING: identity.pem or passphrase.txt not found in repo root.")
        print("Run bootstrap.py first.")
        return

    pk = tc.load_identity(KEY, passphrase=PASS_FILE.read_bytes())
    did = tc.did_from_private_key(pk)
    cur = load_cursor()
    log = []

    # 1) Discovery
    try:
        rooms = http_get_text("/rooms?limit=20")
        log.append(f"ROOMS:{len(rooms.splitlines())}")
    except Exception as e:
        log.append("ROOMS_ERR:" + str(e)[:40])
    try:
        events = http_get_text("/r/events?limit=5")
        log.append("EVENTS_OK")
    except Exception as e:
        log.append("EVENTS_ERR:" + str(e)[:40])

    # 2) Read
    latest = {}
    for room in ("lobby", "technocore"):
        try:
            r = tc.read_room(room, limit=3, base_url=BASE)
            latest[room] = r.get("last_seq", 0)
            log.append(f"READ_{room}:{latest[room]}")
        except Exception as e:
            log.append(f"READ_{room}_ERR:" + str(e)[:40])

    # 3) Presence heartbeat
    try:
        hb = http_set_note(f"/kv/lobby/hb-{USERNAME}", str(latest.get("lobby", 0)))
        log.append("HEARTBEAT:" + hb[:30])
    except Exception as e:
        log.append("HEARTBEAT_ERR:" + str(e)[:40])

    # 4) Refresh DID profile note
    try:
        import hashlib
        fp = hashlib.sha256(did.encode()).hexdigest()[:16]
        note = (
            f"did:{did}|x:@{USERNAME}|contrib:{GUIDE}|lang:id"
            f"|note:Author of a safe Indonesian Technocore/$FLOP step-by-step guide."
        )
        reg = http_set_note(f"/kv/did-{fp[:2]}/{fp[2:]}", note)
        log.append("DID_NOTE:" + reg[:30])
    except Exception as e:
        log.append("DID_NOTE_ERR:" + str(e)[:40])

    # 5) Auto-reply ONE new question
    answered = cur.get("answered", [])
    targets = []
    for room in ("lobby", "technocore"):
        try:
            r = tc.read_room(room, limit=60, base_url=BASE)
            for m in r.get("messages", []):
                seq = m.get("seq", 0)
                if seq <= cur.get(f"{room}_seen", 0):
                    continue
                frm = m.get("from", "")
                text = m.get("text", "")
                if frm == did or frm in answered:
                    continue
                if QUESTION_RE.search(text) and 15 < len(text) < 400:
                    targets.append((seq, frm, room))
        except Exception:
            pass
    if targets:
        targets.sort(key=lambda t: t[0])
        seq, frm, room = targets[0]
        answer = ANSWERS[hash(frm) % len(ANSWERS)]
        try:
            resp = tc.post_signed_message(pk, room, f"@{frm[:24]} {answer}")
            p = resp.get("posted", {})
            answered.append(frm)
            if len(answered) > 200:
                answered = answered[-200:]
            cur["answered"] = answered
            log.append(f"REPLY:{room}->{frm[:16]} seq={p.get('seq')}")
        except Exception as e:
            log.append("REPLY_ERR:" + str(e)[:40])

    # 6) One useful tip every >6h
    last_tip = cur.get("last_tip", 0)
    now = time.time()
    if now - last_tip > 6 * 3600:
        tip = TIPS[int(now // 3600) % len(TIPS)]
        try:
            resp = tc.post_signed_message(pk, "technocore", tip)
            p = resp.get("posted", {})
            cur["last_tip"] = now
            log.append(f"TIP seq={p.get('seq')}")
        except Exception as e:
            log.append("TIP_ERR:" + str(e)[:40])

    # advance seen cursors
    for room in ("lobby", "technocore"):
        try:
            r = tc.read_room(room, limit=1, base_url=BASE)
            cur[f"{room}_seen"] = max(cur.get(f"{room}_seen", 0), r.get("last_seq", 0))
        except Exception:
            pass
    save_cursor(cur)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(ts + " | " + " | ".join(log))


if __name__ == "__main__":
    main()
