#!/usr/bin/env python3
"""
ZeroDollarBot Python SDK — public AI API at $0.001/call (x402-style, verified on-chain).

Zero dependencies (stdlib only). Python 3.8+.

Quick start:
    python zdb_sdk.py try                 # free sample, no wallet needed
    python zdb_sdk.py stats               # public call/earnings stats
    python zdb_sdk.py analyze  "I love this!"  --tx 0x<your-usdc-tx-hash>
    python zdb_sdk.py generate "Write a haiku about local LLMs" --tx 0x...
    python zdb_sdk.py code-review "def add(a,b): return a-b" --tx 0x...
    python zdb_sdk.py translate "Hello world" --to Spanish --tx 0x...
    python zdb_sdk.py pay                 # how to buy calls ($0.001 USDC on Base)

As a library:
    from zdb_sdk import ZDB
    zdb = ZDB()
    zdb.try_free()
    zdb.analyze("I love this!", tx="0x<your-usdc-tx-hash>")

Payment model (the honest, keyless one):
    1. Send any multiple of 0.001 USDC on Base mainnet (chain 8453) to the payTo wallet.
    2. Copy your transaction hash (0x...).
    3. Send it as the tx= argument — the server verifies the transfer on-chain via
       public Base RPCs and redeems 1 call per 0.001 USDC you sent. Replay-checked.
    No API keys. No accounts. Your txHash *is* your ticket.

Set ZDB_URL to pin a specific base URL (the public URL auto-resolves otherwise —
the demo runs on a rotating home-lab tunnel, and the SDK follows it).
"""
import base64
import json
import os
import re
import sys
import time
import urllib.request

__version__ = "1.0.0"
STABLE_ENTRY = "https://satyamkabaap.github.io/zdb-live/"  # never rotates
PRICE = "0.001 USDC"
CHAIN = "8453"  # Base mainnet
USER_AGENT = f"zdb-python-sdk/{__version__}"


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _post_json(url, body, headers=None, timeout=60):
    data = json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:  # 402 etc. carry a JSON body too
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {"raw": str(e)}


def resolve_base_url():
    """Resolve the live API base URL via the stable entry link.

    The entry page meta-refreshes to the current demo tunnel. Returns the
    tunnel origin (scheme + host), falling back to the last-known URL cached
    in ~/.zdb_url.json if the entry page is unreachable.
    """
    cache = os.path.join(os.path.expanduser("~"), ".zdb_url.json")
    last_known = None
    try:
        with open(cache) as f:
            last_known = json.load(f).get("base_url")
    except Exception:
        pass
    pinned = os.environ.get("ZDB_URL")
    if pinned:
        return pinned.rstrip("/")
    try:
        html = _get(STABLE_ENTRY, timeout=15)
        m = re.search(r'url=([^">]+)', html)
        if m:
            url = m.group(1).strip()
            origin = re.match(r"(https?://[^/]+)", url)
            if origin:
                base = origin.group(1)
                with open(cache, "w") as f:
                    json.dump({"base_url": base, "ts": time.time()}, f)
                return base
    except Exception:
        pass
    if last_known:
        return last_known
    raise SystemExit(
        "Could not resolve the API URL. Check https://satyamkabaap.github.io/zdb-live/ "
        "or set ZDB_URL."
    )


class ZDB:
    def __init__(self, base_url=None, tx=None):
        self.base_url = (base_url or resolve_base_url()).rstrip("/")
        self.tx = tx or os.environ.get("ZDB_TX")

    # ---- low-level -------------------------------------------------------
    def _claim(self, tx):
        """Build the X-402-Payment header value from an on-chain tx hash."""
        if not tx:
            raise SystemExit(
                "No tx hash provided. Buy calls first: send 0.001 USDC on Base "
                "(chain 8453) to the payTo wallet (run `python zdb_sdk.py pay`), "
                "then pass --tx 0x<your-tx-hash> or set ZDB_TX."
            )
        claim = json.dumps(
            {"v": "chain", "txHash": tx, "chain": CHAIN}, separators=(",", ":")
        )
        return base64.b64encode(claim.encode()).decode()

    def _call(self, endpoint, body=None, tx=None, method="POST", _retry=True):
        url = f"{self.base_url}{endpoint}"
        if method == "GET":
            status, data = _post_json.__wrapped__ if False else (
                _get_status(url)
            )
        else:
            headers = {"X-402-Payment": self._claim(tx)} if tx else {}
            status, data = _post_json(url, body or {}, headers=headers)
        if status in (000, 530) or (status >= 500 and _retry):
            # tunnel likely rotated — re-resolve once and retry
            fresh = resolve_base_url()
            if fresh != self.base_url:
                self.base_url = fresh
                return self._call(endpoint, body, tx, method, _retry=False)
        return status, data

    # ---- free -------------------------------------------------------------
    def health(self):
        return self._call("/health", method="GET")

    def stats(self):
        return self._call("/stats", method="GET")

    def pay_info(self):
        return self._call("/pay", method="GET")

    def try_free(self, text=None, task=None):
        """Rate-limited free demo (no payment). Optional text + task steer it."""
        body = {}
        if text:
            body["text"] = text
        if task:
            body["task"] = task
        return self._call("/try-free", body or None)

    # ---- paid ($0.001/call, on-chain verified) -----------------------------
    def analyze(self, text, tx=None):
        return self._call("/analyze", {"text": text}, tx=tx or self.tx)

    def generate(self, prompt, tx=None):
        return self._call("/generate", {"prompt": prompt, "text": prompt}, tx=tx or self.tx)

    def code_review(self, code, tx=None):
        return self._call("/code-review", {"code": code, "text": code}, tx=tx or self.tx)

    def translate(self, text, target, tx=None):
        return self._call(
            "/translate", {"text": text, "target": target, "target_language": target},
            tx=tx or self.tx,
        )


def _get_status(url):
    """GET with status, following nothing exotic."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {"raw": str(e)}
    except Exception as e:
        return 000, {"error": str(e)}


# ---- CLI ------------------------------------------------------------------
def main():
    import argparse

    p = argparse.ArgumentParser(
        prog="zdb_sdk",
        description=f"ZeroDollarBot AI API client — {PRICE}/call, verified on Base (chain {CHAIN}). "
        "Free demo: `try`/`tryfree`/`stats`. Buy calls: `pay`.",
    )
    p.add_argument(
        "command",
        choices=["try", "tryfree", "analyze", "generate", "code-review",
                 "translate", "stats", "health", "pay", "url", "smoke"],
    )
    p.add_argument("text", nargs="?", help="input text / prompt / code")
    p.add_argument("--to", default=None, help="target language (translate)")
    p.add_argument("--tx", default=None, help="your Base USDC tx hash (0x...)")
    p.add_argument("--url", default=None, help="override base URL")
    args = p.parse_args()

    zdb = ZDB(base_url=args.url, tx=args.tx)

    def show(status, data):
        tag = {200: "OK", 402: "PAYMENT REQUIRED (run `pay` for instructions)"}.get(
            status, f"HTTP {status}"
        )
        print(f"[{tag}]")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0 if status == 200 else 1

    if args.command == "url":
        print(zdb.base_url)
        return 0
    if args.command == "health":
        return show(*zdb.health())
    if args.command == "stats":
        return show(*zdb.stats())
    if args.command == "pay":
        return show(*zdb.pay_info())
    if args.command in ("try", "tryfree"):
        return show(*zdb.try_free())
    if args.command == "smoke":
        s1, d1 = zdb.health()
        print("health:", s1, d1.get("status", d1))
        s2, d2 = zdb.try_free()
        print("try-free:", s2, str(d2.get("sample", d2))[:120])
        return 0 if s1 == s2 == 200 else 1

    # paid endpoints
    if not args.text:
        p.error(f"'{args.command}' requires input text")
    if args.command == "analyze":
        return show(*zdb.analyze(args.text))
    if args.command == "generate":
        return show(*zdb.generate(args.text))
    if args.command == "code-review":
        return show(*zdb.code_review(args.text))
    if args.command == "translate":
        if not args.to:
            p.error("translate requires --to <language>")
        return show(*zdb.translate(args.text, args.to))


if __name__ == "__main__":
    sys.exit(main())
