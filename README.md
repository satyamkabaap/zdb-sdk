# zdb-sdk — Python client for the ZeroDollarBot public AI API

**A real, live public AI API for $0.001 per call** — text analysis, content
generation, code review, and translation — running entirely on free local LLMs
in a home lab. No API keys. No accounts. No cloud bills.

Your **payment proof is your API key**: one txHash, verified on-chain.

```bash
pip install nothing  # stdlib only, Python 3.8+
python zdb_sdk.py try          # free sample right now, no wallet needed
python zdb_sdk.py stats        # live call + earnings stats
```

## What you get

| Endpoint      | What it does                          | Price      |
|---------------|---------------------------------------|------------|
| `/analyze`    | sentiment, summarization, structure   | $0.001/call|
| `/generate`   | blog drafts, social copy, emails      | $0.001/call|
| `/code-review`| bug finding, improvement suggestions  | $0.001/call|
| `/translate`  | multi-language translation            | $0.001/call|
| `/try-free`   | free demo (rate-limited)              | free       |
| `/stats`      | live public stats                     | free       |

## How payment works (the honest, keyless way)

1. Send **0.001 USDC on Base mainnet (chain 8453)** per call you want —
   to the `payTo` wallet printed by `python zdb_sdk.py pay`
   (or see the live 402 response from any paid endpoint).
2. Copy your **transaction hash** (`0x...`).
3. Pass it to the SDK: your txHash *is* your ticket.
   The server verifies the transfer on-chain via public Base RPCs,
   credits you 1 call per 0.001 USDC sent, and replay-checks each redemption.

```bash
python zdb_sdk.py pay                                        # get the wallet + header format
python zdb_sdk.py analyze "I love this product!" --tx 0x<your-tx-hash>
python zdb_sdk.py generate "Write a haiku about local LLMs" --tx 0x<your-tx-hash>
python zdb_sdk.py translate "Hello world" --to Spanish --tx 0x<your-tx-hash>
python zdb_sdk.py code-review "def add(a,b): return a-b" --tx 0x<your-tx-hash>
```

As a library:

```python
from zdb_sdk import ZDB

zdb = ZDB()
zdb.try_free()                                   # free demo
zdb.analyze("I love this!", tx="0x<your-tx>")    # paid call
zdb.generate("Write a tweet about local LLMs", tx="0x<your-tx>")
```

No tx yet? `analyze()` without one returns the server's 402 with exact
payment instructions — the SDK turns that into a clear next step, never a dead end.

## The URL problem, solved

The demo runs on a rotating home-lab tunnel (Cloudflare quick tunnels).
Instead of hardcoding a URL that dies, the SDK:

1. Resolves the **live base URL** through the stable entry page
   [`https://satyamkabaap.github.io/zdb-live/`](https://satyamkabaap.github.io/zdb-live/)
   (GitHub Pages redirector that always points at the current tunnel),
2. Caches the last-known URL in `~/.zdb_url.json` as fallback,
3. On 5xx, **re-resolves once and retries automatically**.

Pin it yourself anytime with `ZDB_URL` env var or `--url`.

## Why this exists

ZeroDollarBot is an experiment: **can a single home machine with free,
open-weight local models serve a real public AI API at real prices?**
No OpenAI, no Anthropic, no vendor lock-in, zero marginal compute cost.

Live stats: `python zdb_sdk.py stats` — every call and every micro-earning,
in public.

- Stable entry: <https://satyamkabaap.github.io/zdb-live/>
- Wallet (Base): `0x40dE12c2bE00c18cc7ea731d1700b9e782a6022F`

## Notes

- Free demo (`/try-free`) is rate-limited per IP; paid calls are not.
- The API speaks x402-style payments: retry any paid call with an
  `X-402-Payment` header (the SDK builds it for you from your txHash).
- MIT licensed — use it commercially, no strings.

## License

MIT
