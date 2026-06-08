#!/usr/bin/env python3
"""Print the exact SuperClaw onboarding message for this skill.

The agent runs this and relays the output verbatim, so every user sees an
identical, correct message instead of an agent paraphrase. Reads the instance
config JSON directly (no package import / venv needed beyond python3).

Usage:
    python setup_message.py --config /path/to/config_<id>.json          # setup message
    python setup_message.py --config /path/to/config_<id>.json --live   # "you're live" menu

Asset label is derived from allowed_coins (e.g. ["ETH"] -> ETH,
["xyz:GOLD"] -> GOLD), so this same file works for every skill.
"""

import argparse
import json
import sys

SETUP = """SuperClaw {ASSET} Perps — let's get you set up 🚀
~3 minutes. The agent copy-trades {ASSET} for you. You stay in control and can stop anytime.

**🔑 Your Agent Wallet** (created for you)
`{WALLET}` · {NETWORK}

⚠️ **Use a brand-new wallet for this skill** — not one you've used for another SuperClaw skill. Hyperliquid limits each account to ~3 trading agents, so each skill needs its own wallet.

### 1️⃣ Create a fresh wallet
Make a new wallet/account in **OKX Wallet, MetaMask, or Phantom** (just add a new account — a couple of taps). It lives on the **Arbitrum** chain.
💡 Keep a little **ETH on Arbitrum** in it for gas — you'll need it to approve and deposit USDC.

### 2️⃣ Fund it with USDC
Open Hyperliquid with that wallet and deposit **USDC** — that's the only thing you add (never {ASSET} itself; perps are USDC-margined). Use **USDC on Arbitrum** or **USDC on HyperEVM**.
→ https://app.hyperliquid.xyz

### 3️⃣ Authorize trading
Open the link below with that same wallet and sign **Agent + Builder**. This lets the bot place {ASSET} trades for you — no funds move, just permission.
→ https://moss.site/hyperliquid/authorize/{WALLET}

### 4️⃣ Send me your wallet address
Reply with the `0x…` address of the wallet you just used, and I'll start copying {ASSET} trades.

✅ I pick the trading agent automatically — you don't choose one. Curious first? Just ask **"tell me about this agent."**"""

LIVE = """**You're live! 🎉 Here's everything you can ask me — just type it plainly:**

### 📊 Check on it
- **"status"** — running state, balance, current position
- **"show my position"** — your open {ASSET} trade right now
- **"how am I doing?"** — profit/loss summary
- **"tell me about this agent"** — the agent's strategy and track record

### ⚙️ Adjust your risk
- **"set follow ratio to 50%"** — copy at half the agent's trade size (lower = smaller, safer)
- **"set stop loss to 20%"** — auto-close a trade if it drops 20%
- **"show my settings"** — current ratio, stop loss, slippage

### ⏯️ Control it
- **"pause"** — stop copying new trades (open ones stay)
- **"resume"** — start copying again
- **"stop"** — shut it down

### 🔔 Auto-updates (optional)
Want position summaries automatically? Tell me how often: **every 5 min · 15 min · 30 min · 1 hour · 4 hours · 12 hours · daily**
- e.g. **"update me every 15 minutes"**
- **"stop updates"** — turn them off

💡 New here? Start with **"how am I doing?"** anytime."""


def _asset_label(cfg: dict) -> str:
    coins = cfg.get("allowed_coins") or []
    if coins and isinstance(coins, list):
        return str(coins[0]).split(":")[-1].upper()
    return "ASSET"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="path to config_<id>.json")
    ap.add_argument("--live", action="store_true", help="print the live/command-menu message")
    args, _ = ap.parse_known_args()

    try:
        with open(args.config) as f:
            cfg = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: could not read config {args.config}: {e}", file=sys.stderr)
        sys.exit(1)

    asset = _asset_label(cfg)
    wallet = cfg.get("wallet_address") or "(run: config wallet-generate first)"
    api = str(cfg.get("hl_api_url", ""))
    network = "Testnet" if "testnet" in api else "Mainnet"

    template = LIVE if args.live else SETUP
    print(template.format(ASSET=asset, WALLET=wallet, NETWORK=network))


if __name__ == "__main__":
    main()
