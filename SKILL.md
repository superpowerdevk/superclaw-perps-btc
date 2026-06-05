---
name: superclaw-perps-btc
description: Manage the SuperClaw BTC perpetual copy-trading service on Hyperliquid. Use when the user wants to start/stop/check the follow service, generate an agent wallet, complete authorization, view the curated agent's track record, view trade history/stats, or sync to the latest curated agent. The followed agent trades BTC perps only, runs on a dedicated Hyperliquid account, is selected centrally by the SuperClaw admin, and is resolved automatically at service start - the user never picks a trader.
---

# SuperClaw BTC Perps Copy-Trade — Interaction Flow (EN)

> For SuperClaw / OpenClaw skill development. Describes the Bot's full in-conversation behavior.
> This skill copy-trades a single curated **BTC-perp** agent on Hyperliquid. It runs on its **own dedicated Hyperliquid account** — a **fresh wallet funded with USDC**, separate from every other SuperClaw skill (required: HL caps agents per account, so each skill needs its own wallet).
> The followed agent is selected centrally by the SuperClaw admin. At service start the CLI resolves it from the remote pointer `agent_pointer_url` and writes it into `moss_source.agent_id`. The user never picks, inputs, or changes the agent.


---

## On install — FIRST ACTION (do not wait for the user)

The moment this skill is installed, proactively do BOTH steps below in order — do **not** ask permission, and do **not** end your turn with a passive line like "ready when you are" / "whenever you want to set it up." A brand-new user does not know what to do next; you must drive them straight into setup.

1. **Generate the Agent Wallet now** — run the skill's `config wallet-generate` command (via the skill's venv + a fresh instance config). Capture the generated Agent Wallet address and network.
2. **Immediately output the Setup message** (Onboarding section A below) with the real `<AGENT_WALLET>` and `<NETWORK>` filled in — the 4 numbered steps and the authorize link.

If the user installs and you have NOT yet shown the 4-step setup with a generated wallet address, you are not done. Never stop at "installed." Always end the install turn with the Setup message so the user's next action is obvious.

---

## Overview

After installing the SuperClaw BTC Perps Copy-Trade skill, the user can — via conversation — automatically follow a centrally-curated **BTC-perp** agent on Hyperliquid. For isolation, this skill runs on its **own dedicated Hyperliquid account** (a fresh wallet used only for BTC). The followed agent is **not chosen by the user**; it is resolved automatically from the official remote pointer at service start/resume.

The flow has three stages:

1. Wallet setup (connect a **fresh wallet** funded with **USDC**, generate Agent Wallet + sign & register)
2. Configure copy-trade parameters (ratio, stop-loss, slippage)
3. Run & manage (status, pause, sync latest agent, view agent track record, stop)

> **Agent selection**: the user neither needs to nor can pick a trader in conversation. The active agent is delivered by the admin via the `agent_pointer_url` remote pointer and written into config at service start. After a device change/reinstall the user still pulls the current official agent.

## BTC skill specifics

This skill differs from the generic copy-trade flow in three ways. Everything else (wallet setup, parameters, run/manage, FAQ) below still applies.

### 1. Single asset: BTC only
`allowed_coins` is locked to `["BTC"]`. The curated agent trades BTC perps; the skill only ever places BTC orders. Never widen the whitelist.

### 2. Dedicated Hyperliquid account — REQUIRED, one fresh wallet per skill
This skill must run on its **own Hyperliquid account**, i.e. its **own wallet, separate from every other SuperClaw perps skill.** This is mandatory for two reasons: (1) it isolates this skill's margin and risk, and (2) Hyperliquid limits how many trading agents a single account can authorize — **as low as 3 for a new account** — so reusing one wallet across skills WILL fail with "too many agents" once the user passes that limit. One fresh wallet per skill means each account carries only one agent, and the limit never applies.

**The Bot MUST walk the user through this explicitly before authorization — do not assume they know:**

1. **Use a brand-new wallet for this skill.** Not the wallet used for any other SuperClaw skill. In their wallet app (MetaMask, Rabby, etc.) they can create a new account/address in a couple of taps, or use a different wallet they control. If the user authorizes from a wallet already used by another skill and hits **"Too many extra agents… limit is 3,"** that is exactly this — tell them to switch to a new wallet for this skill.
2. **Fund it with USDC only.** Every Hyperliquid perp is **USDC-margined** — the user does **NOT** buy or deposit BTC (or BNB/ETH/HYPE/etc.). They deposit **USDC** into that new wallet's Hyperliquid account (deposit/bridge on the Hyperliquid app). That USDC is the collateral for every position this skill copies, regardless of which asset.
3. **Authorize this skill's agent from that new wallet** (Agent + Builder), then send that wallet's address.

The Bot must NOT let the user reuse a wallet across skills, and must NOT tell them to deposit the traded asset — it is always **USDC** as collateral.

Setup order for this skill: **new wallet → deposit USDC → authorize agent → configure → start.**

### 3. Agent track record (`agent-info`)
When the user asks to see the agent's performance / track record / "what am I getting into," the Bot runs `agent-info` (no signature needed; works before funding) and presents the card. It pulls live metrics from the public Moss endpoint:

- ROI, overall PnL, max profit
- **Max drawdown and win rate are always shown next to ROI** — never present ROI alone.
- Profit factor, trade count, liquidations, status, days running.

Always close the agent-info reply with: the platform selecting this agent is **not investment advice** and guarantees no profit; past performance does not predict future results; the user bears all risk.

CLI: `agent-info` (English). The Bot weaves the numbers into a natural reply rather than dumping raw output.


## Key limits

1. **Coin scope**: locked to **BTC** only via the `allowed_coins` whitelist (`["BTC"]`). The curated agent trades BTC perps; do not widen the whitelist for this skill.
2. **Balance monitoring & alerts**: once the service starts it monitors account balance. When `withdrawable` drops below `low_balance_threshold_usd` (default 10 USDC) an alert is written to the DB; the Bot polls and reminds the user to top up. Alert cadence: at most 3/day, at least 10 minutes apart.

## Hard output rules

1. **Give the authorization link immediately after install**: when the user asks to install/update/test the copy-trade skill and the Agent Wallet has been generated, the reply must include the Agent Wallet address, the network, and the full authorization page URL (built from `hl_authorize_url` + `<wallet_address>`). Don't just say "go to the authorization page," and don't wait for the user to ask "what's the URL."
2. **After authorization, collect only the main wallet address**: when the user says "authorized," prompt them to send their main wallet address. **Do not** ask for, suggest, or accept an agent ID/link from the user — the agent is delivered centrally and resolved automatically at service start; the user does not choose.
3. **Concise summary after a successful start**: keep the start-success message concise but more complete than routine pushes; include at least the agent, the agent's position, init result, follow ratio, slippage, coin whitelist, main wallet address, Agent Wallet address, Follower ID (if any), network, and run state. Don't include stop-loss/take-profit or poll interval by default unless the user just configured them or asks.
4. **Be explicit about the top-up target**: when the user asks about topping up, adding margin, or what to do on low balance, the Bot must clearly say "top up the Hyperliquid account that corresponds to your main wallet" — don't let them think they should send an on-chain transfer to the main wallet address itself.
5. **Never let the user pick the agent**: the agent is centrally selected and delivered via the remote pointer. The Bot must not ask for `agt_xxx`, must not provide an agent list page, and must not let the user paste a link. If the user asks to "switch agents / follow so-and-so," explain that this service's agent is chosen centrally by the platform; the user can send "Sync latest agent" to pull the current official agent, but cannot select a specific one.

---

## Background knowledge

**Agent Wallet mechanism**
Hyperliquid provides an official agent mechanism: the user's main wallet authorizes a separate Agent Wallet, whose private key the Bot holds, to submit trades on Hyperliquid on the user's behalf. The main wallet's assets are never operated directly, and the agent authorization can be revoked at any time.

**Copy-trade logic**
Once the platform centrally selects an agent (delivered via the `agent_pointer_url` remote pointer), the Bot watches that agent's trading activity (via the Moss Source-Core 2.0 API — WS + REST fills) and, scaled by the user's chosen ratio, mirrors it on Hyperliquid through delta position alignment using the Agent Wallet. The user is not involved in agent selection.

**Core mechanism: baseline + delta alignment**
- On start, the agent's current positions are recorded as a baseline.
- When the agent's positions change, a delta is computed and aligned on HL scaled by the account ratio.
- Direction clamping: never opens in the opposite direction — at most closes to 0.
- After the agent flattens, the baseline resets to zero and a new direction can be followed.

---

## Environment setup

First-time use requires initializing a Python virtual environment and installing dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The config file is created automatically by `wallet-generate` (based on the `config_default.json` template):

```bash
.venv/bin/python cli.py config wallet-generate
# creates ~/.hyperliquid-copy-trade/<last 6 of wallet>/config_<last 6>.json and sets per-instance isolated paths automatically
```

**Important**: `config.json` and `config_default.json` are forbidden; every command must point at a specific config via `--config ~/.hyperliquid-copy-trade/<6>/config_<6>.json`.
**Important**: the Agent Wallet config is stored by default at `~/.hyperliquid-copy-trade/<6>/config_<6>.json`, not under the OpenClaw skill directory; that instance's logs, database, and PID are also stored under the same `~/.hyperliquid-copy-trade/<6>/` directory, so a skill upgrade/overwrite/delete or a `/tmp` cleanup won't lose critical data.
**Network template**: the `dev` branch defaults to testnet; explicit templates are `config_default.testnet.json` and `config_default.mainnet.json`, full parameter matrix in `docs/network-config.md`. When the Bot outputs the network and authorization link it should read the current config, not hard-code mainnet or testnet wording.

## Technical implementation

The project root contains `cli.py` and `follow_service/`. All operations run via `.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json`.

**Maintenance convention**: the `dist/` directory is a generated artifact; when changing code, config templates, or skill docs, don't edit `dist/` directly — only edit the source (`follow_service/`, `cli.py`, `config_default.json`, `.claude/skills/**/SKILL.md`); `dist/` is produced later by the packaging step.

### Core modules

| Module | Responsibility |
|--------|----------------|
| `moss_client.py` | Moss REST API client (follower wallet-signature auth) |
| `moss_poller.py` | incremental fills polling + baseline init + delta-alignment trigger |
| `trader.py` | Hyperliquid order execution (IOC limit orders + delta-alignment algorithm) |
| `database.py` | SQLite storage (baseline, events, trade records, account snapshots) |
| `balance_tracker.py` | periodic account-balance snapshots |

### Moss signal-source config (config_<6>.json)

```json
{
  "moss_source": {
    "enabled": true,
    "base_url": "http://54.255.3.5:8088",
    "agent_id": "agt_xxx",
    "fill_poll_secs": 15,
    "symbol_map": {"BTCUSDT":"BTC","BTCUSDC":"BTC","ETHUSDT":"ETH","ETHUSDC":"ETH","SOLUSDT":"SOL","SOLUSDC":"SOL","BNBUSDT":"BNB","BNBUSDC":"BNB","APTUSDT":"APT","APTUSDC":"APT","ATOMUSDT":"ATOM","ATOMUSDC":"ATOM","ARBUSDT":"ARB","ARBUSDC":"ARB","AVAXUSDT":"AVAX","AVAXUSDC":"AVAX","ADAUSDT":"ADA","ADAUSDC":"ADA","BCHUSDT":"BCH","BCHUSDC":"BCH","DOGEUSDT":"DOGE","DOGEUSDC":"DOGE","DOTUSDT":"DOT","DOTUSDC":"DOT","FILUSDT":"FIL","FILUSDC":"FIL","HBARUSDT":"HBAR","HBARUSDC":"HBAR","LINKUSDT":"LINK","LINKUSDC":"LINK","LTCUSDT":"LTC","LTCUSDC":"LTC","NEARUSDT":"NEAR","NEARUSDC":"NEAR","OPUSDT":"OP","OPUSDC":"OP","SUIUSDT":"SUI","SUIUSDC":"SUI","TRXUSDT":"TRX","TRXUSDC":"TRX","XRPUSDT":"XRP","XRPUSDC":"XRP","UNIUSDT":"UNI","UNIUSDC":"UNI"}
  }
}
```

### Moss follower auth

The current version uses follower wallet-signature auth; `api_key` / `api_secret` are no longer needed. On service start it registers a follower with Moss using the Agent Wallet private key, and uses the wallet signature to read the current official agent's read-only positions, account, and fills.

---

## Stage 1: Wallet setup

### Trigger
First conversation after the user installs the skill, or the user sends a keyword like "Start" / "Set up wallet."

### Bot's first message
Introduce the skill and guide the user to the wallet-setup page (completed on a separate page, not inline in chat).

If the user asked the Bot to install/update the skill and prepare the copy-trade service, then after install and Agent Wallet generation the reply must include the full authorization URL:

```
New skill installed and wallet generated ✅

• Agent Wallet: 0xAGENT_ADDRESS
• Network: testnet
• Authorization page: https://alpha.moss.site/hyperliquid/authorize/0xAGENT_ADDRESS

Open the authorization page with your main wallet to complete authorization. Once authorized, just send me your main wallet address — the agent is selected automatically by the platform, so you don't need to choose one.
```

### Wallet-setup page (separate page, sequential)

**Step 1 — Connect main wallet**
- Show wallet options: MetaMask / Phantom / WalletConnect
- User selects and clicks "Connect wallet"
- On success, show the main wallet address and proceed

**Step 2 — Generate Agent Wallet**
- Explain the Agent Wallet's purpose and safety
- User clicks "Generate Agent Wallet"
- System generates a new keypair and shows the Agent Wallet address
- The private key is stored encrypted, used only for Hyperliquid order placement

**Step 3 — Main wallet signature**
- Explain the signature's purpose: register the authorization relationship between the main wallet and the Agent Wallet on Hyperliquid
- Emphasize: no assets are transferred, this is just an on-chain record
- User confirms the signature in the wallet popup
- On success, show the completed state and a "Back to chat" button

### After returning to chat
- The user side auto-sends: "Wallet setup complete ✓"
- The Bot verifies and replies with a confirmation:
  - **Main wallet address** (main_address): 0xMAIN_ADDRESS (the account holding the funds)
  - **Agent Wallet address** (wallet_address): 0xAGENT_ADDRESS (the account that places orders on your behalf)
  - Note: the main wallet authorizes the Agent Wallet to trade for it; funds stay in the main wallet
- **Important reminder**: the Bot must clearly tell the user "confirm your main wallet address is correct — copy-trade funds will be drawn from this account."
- Guide the user to the next stage: configure copy-trade parameters (the agent is already auto-selected by the platform; no user choice needed)

### Matching CLI operations

```bash
# Generate Agent Wallet
.venv/bin/python cli.py config wallet-generate

# Set the main wallet address (the wallet-setup page should do this automatically; run manually if not written)
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json config set main_address <0xMAIN_ADDRESS>

# Verify authorization (run after completing authorization on the auth page)
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json config check-auth
```

**Note**: after the wallet-setup page connects the main wallet, it should write `main_address` into config automatically. After "Back to chat," the Bot should confirm via `config show` that `main_address` is set; if empty, prompt the user for it. If the user only says "authorized" without giving the main wallet address, the Bot should reply: "Once authorized, please send me your main wallet address — the agent is selected automatically by the platform, so you don't need to choose one."

Authorization must be completed by the user on the `hl_authorize_url` page in config, with the trailing address replaced by the actual Agent Wallet address. The `dev` branch defaults to testnet:

```
https://alpha.moss.site/hyperliquid/authorize/<wallet_address>
```

For example, if the Agent Wallet address is `0xAbCd...1234`, the authorization link is:

```
https://alpha.moss.site/hyperliquid/authorize/0xAbCd...1234
```

**Get the wallet_address**:
```bash
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json config show   # view the wallet_address field
```

Two authorizations are required:
1. **Agent authorization** — authorize `wallet_address` as the main account's agent
2. **Builder authorization** — authorize the network's builder address (see `docs/network-config.md`)

### Edge branches
| Situation | Bot handling |
|-----------|--------------|
| User asks "what is an Agent Wallet" | explain the mechanism, confirm safety, continue |
| User asks "what is the signature for" | explain the on-chain authorization relationship, emphasize no asset transfer |
| User asks "is this safe" | explain the private key is stored encrypted, the main wallet is never operated directly, revocable any time |
| User clicks back | return to chat, flow paused, resumable next time |

---

## Agent selection (automatic, no user interaction)

The agent is centrally selected by the platform — there is **no separate "select agent" stage**.

- On service start/resume, the CLI resolves the current official agent from the `agent_pointer_url` remote pointer and writes it into `moss_source.agent_id`.
- If the remote pointer is unreachable, the last-known `agent_id` in config is reused; if it was never resolved, startup fails with a clear message.
- The user can send "Sync latest agent" (`service switch`) at any time to flatten and switch to the current latest official agent.

After wallet setup, **go straight to the next stage (configure copy-trade parameters)** — do not ask the user to choose or paste an agent.

## Stage 2: Configure copy-trade parameters

### Trigger
After wallet setup completes (the agent is already auto-selected by the platform).

### Parameter 1: Follow ratio

The Bot asks for the follow ratio: enter a percentage (e.g. 50%); each trade follows the corresponding fraction of the agent's position. Fixed-amount mode is not supported in the current code.

### Parameter 2: Stop-loss

The Bot asks whether to set a stop-loss:
- Enter a negative percentage (e.g. -20%); copy-trading stops automatically when the loss exceeds that.
- Choose not to set it, and following continues without auto-stop.

### Parameter 3: Slippage

Leverage is no longer a user parameter; orders follow the agent's current position leverage. The user can adjust the IOC slippage:

```bash
.venv/bin/python cli.py config set slippage_percent 1.5
```

### Parameter 4: Coin whitelist

Default majors: BTC, ETH, SOL, BNB, APT, ATOM, ARB, AVAX, ADA, BCH, DOGE, DOT, FIL, HBAR, LINK, LTC, NEAR, OP, SUI, TRX, XRP, UNI. `allowed_coins` is a coin whitelist; the service won't auto-overwrite it on start. For a more conservative setup, keep only some of these coins.

```bash
# Majors whitelist
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json config set allowed_coins '["BTC","ETH","SOL","BNB","APT","ATOM","ARB","AVAX","ADA","BCH","DOGE","DOT","FIL","HBAR","LINK","LTC","NEAR","OP","SUI","TRX","XRP","UNI"]'
```

### Confirmation summary

The Bot summarizes the config for the user to confirm:
- Agent name
- Follow ratio
- Stop-loss (or "not set")
- Slippage
- Coin whitelist

The user can choose "Confirm & start" or "Edit parameters."

---

## Stage 3: Run & manage

### Activation success

```bash
.venv/bin/python cli.py service start
.venv/bin/python cli.py service status
```

The Bot sends a start-success message and tells the user they'll be notified immediately when the agent acts. Keep the start-success message concise, with the key run parameters and the init result.

Recommended format:

```
Copy-trade started and initialized ✅

• Network: <testnet/mainnet, inferred from hl_api_url>
• Agent: agt_xxx (show name if available)
• Agent position: SHORT/LONG <size> BTC-USDC @ <price> (if none: "no position, monitoring only")
• Follow ratio: <percent>% ($your equity / $agent equity, if available)
• Slippage: <slippage_percent>%
• Coin whitelist: BTC
• Main wallet: 0xMAIN_ADDRESS
• Agent Wallet: 0xAGENT_ADDRESS
• Follower ID: flw_xxx (if any)
• Init: bought/sold <size> BTC (open long/open short/close/no order needed)
• Status: running, trades will sync automatically
```

### How copy-trading runs

After the service starts:
1. **Baseline init** — query the agent's current positions on Moss and align on HL by ratio
   - positions with PnL beyond the threshold (default 3%) only record a baseline, no catch-up
   - only the first channel in a given start does the baseline check/init; if a baseline exists but your position is empty, it force-reinits, so a user can resume directly after manually flattening
2. **fills polling** — query the Moss `/fills` endpoint every 15s by default; on restart it looks back at most 20 minutes, to avoid missing fills during a brief downtime without replaying too much history
3. **new fill detected** → query Moss positions → delta alignment → IOC order on HL
4. **agent flattens** → baseline resets to zero → can follow a new direction

### Proactive push notifications
Each time the agent trades, the Bot pushes a notification containing:
- Agent name
- Trade direction (buy / sell)
- Asset
- Execution price
- Your synced position state

### User-initiated queries

When the user sends "Status," the Bot returns a summary:
- Run state (running / paused)
- Current followed agent
- Today's PnL (amount + percent)
- Today's trade count
- Current parameters (ratio, stop-loss)
- A few recent trades (PnL)

Matching CLI:
```bash
.venv/bin/python cli.py service status
.venv/bin/python cli.py stats
.venv/bin/python cli.py trades --limit 10
.venv/bin/python cli.py balance
```

### Management commands

The user can send any of these keywords at any time:

| Command | Behavior | CLI |
|---------|----------|-----|
| Pause | flatten all positions and stop copy-trading | `service pause` |
| Resume | restart copy-trading from paused | `service resume` |
| Sync latest agent | flatten + clear baseline + re-resolve official agent pointer + restart | `service switch` |
| Adjust parameters | reconfigure follow ratio, stop-loss, take-profit, slippage, coin whitelist | `config set ...` |
| Stop | enter a two-step confirmation flow | `service stop` + revoke agent |
| Status | return the current copy-trade status summary | `service status` + `stats` |

---

### Pause flow

**Scenario**: the user wants to stop copy-trading and flatten all positions.

```
User: Pause

Bot: Confirm pause? On pause:
     - all positions will be closed
     - copy-trading will stop
     Please confirm: [Confirm pause] [Cancel]

User: Confirm pause

Bot: (runs service pause)
     ✅ Copy-trading paused
     - all positions closed
     - copy-trading stopped
     To resume, send "Resume"
```

Matching CLI:
```bash
.venv/bin/python cli.py service pause
```

`service pause` does: flatten all → stop service → clear baseline.

**Error handling**:
- User replies "Cancel" → Bot replies "Cancelled, copy-trading continues," no action
- If flattening fails → Bot tells the user the specific error and to handle manually

---

### Resume flow

**Scenario**: the user resumes copy-trading from paused.

```
User: Resume

Bot: (runs service status to check state)
     You're currently paused.
     Confirm resume? On resume, copy-trading restarts from scratch.
     Please confirm: [Confirm resume] [Cancel]

User: Confirm resume

Bot: (runs service resume)
     ✅ Copy-trading resumed
     - Current followed agent: XXX (read agent_id from config)
     - restarted from scratch
```

Matching CLI:
```bash
.venv/bin/python cli.py service status     # check state first
.venv/bin/python cli.py service resume     # resume service
```

`service resume` does: start service → re-bootstrap baseline init.

**Error handling**:
- If not currently paused (service running) → Bot replies "Copy-trading is already running, no need to resume"
- User replies "Cancel" → no action

---

### Sync latest agent flow

**Scenario**: the user wants to make sure they're on the current latest official agent (the platform may have updated it).

```
User: Sync latest agent

Bot: (runs service status to confirm state)
     Syncing will:
     - close all current positions
     - re-pull the current official agent and rebuild the baseline
     Confirm sync? [Confirm] [Cancel]

User: Confirm

Bot: (runs service switch = pause + resume)
     ✅ Synced to the latest official agent
     - old positions closed
     - baseline rebuilt on the current official agent, copy-trading continues
```

Matching CLI:
```bash
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json service switch
```

`service switch` does: pause (flatten all + clear baseline) → restart service (re-resolves `agent_pointer_url` on start and rebuilds the baseline). The user does not need to — and cannot — specify a particular agent.

**Error handling**:
- User replies "Cancel" → no action, current copy-trading is kept.
- Remote pointer unreachable → restart reuses the last-known agent and the Bot tells the user to try again later.

### Adjust parameters flow

**Scenario**: the user wants to change follow ratio, stop-loss, take-profit, slippage, or coin whitelist.

```
User: Adjust parameters

Bot: Which parameter would you like to adjust?
     [Follow ratio] [Stop-loss] [Take-profit] [Slippage] [Coin whitelist]
```

**— Adjust follow ratio —**

```
User: Follow ratio

Bot: (runs config show to read current follow_ratio)
     Current follow ratio: 50%
     ⚠️ Note: above 100% is not recommended; over-following amplifies risk.
     Enter the new ratio:

User: 30%

Bot: (runs config set follow_ratio 0.3)
     ✅ Follow ratio set to 30%
```

**— Adjust stop-loss —**

```
User: Stop-loss

Bot: (runs config show to read current stop_loss_pct)
     Current stop-loss: -10% (0 means not set)
     Enter the new stop-loss (e.g. -8%, enter 0 to disable):

User: -8%

Bot: (runs config set stop_loss_pct 8)
     ✅ Stop-loss set to -8%
```

**— Adjust take-profit —**

```
User: Take-profit

Bot: (runs config show to read current take_profit_pct)
     Current take-profit: 20% (0 means not set)
     Enter the new take-profit (e.g. 25%, enter 0 to disable):

User: 25%

Bot: (runs config set take_profit_pct 25)
     ✅ Take-profit set to 25%
```

**— Adjust slippage —**

```
User: Slippage

Bot: (runs config show to read current slippage_percent)
     Current slippage: 1.5%
     Enter the new IOC slippage percent:

User: 2

Bot: (runs config set slippage_percent 2)
     ✅ Slippage set to 2%
```

Matching CLI:
```bash
.venv/bin/python cli.py config show
.venv/bin/python cli.py config set follow_ratio 0.3
.venv/bin/python cli.py config set stop_loss_pct 8
.venv/bin/python cli.py config set take_profit_pct 25
.venv/bin/python cli.py config set slippage_percent 2
```

**Note**: parameter changes don't require a restart; they take effect on the next delta alignment. But a change in follow ratio affects all subsequent position math — tell the user.

---

### Stop flow (two-step confirmation)

The Bot sends a confirmation prompt explaining:
- existing positions are NOT auto-closed
- the Agent Wallet will be revoked, irreversibly
- to copy-trade again, wallet setup must be redone

Execute after the user replies "Confirm stop"; "Cancel" keeps the current state.

After stopping, the Bot tells the user the Agent Wallet has been revoked and they can send "Start" to set up again.

Matching CLI:
```bash
.venv/bin/python cli.py service stop
```

---

## Full state machine

```
[Install skill]
     ↓
[Bot welcome] → user clicks "Complete wallet setup"
     ↓
[Wallet-setup page]
  Step 1: Connect main wallet
  Step 2: Generate Agent Wallet
  Step 3: Main wallet signature
     ↓ done, auto-message back to chat
[Bot verified] → go to configure parameters (agent already auto-selected)
     ↓
[Agent auto-selected by official pointer, no user interaction]
     ↓
[Configure parameters]
  - Follow ratio
  - Stop-loss
  - Leverage / slippage / coin whitelist
  - Confirmation summary
     ↓ confirm & start
[Copy-trading]
  ├── Moss fills polling (every 15s)
  ├── new fill → delta alignment → HL order
  ├── proactive trade notifications
  ├── user queries "Status"
  ├── user "Adjust parameters" → pick param → enter value → [Copy-trading] (updated, keeps running)
  ├── user "Pause" → confirm → flatten all → [Paused]
  │                                            ├── "Resume" → confirm → rebuild baseline → [Copy-trading]
  │                                            └── "Sync latest agent" → flatten → re-resolve official agent → [Copy-trading]
  └── user "Stop" → confirm → revoke Agent Wallet
                              ↓
                         [Can start over]
```

---

## Keyword trigger list

| Keyword | Stage | Action |
|---------|-------|--------|
| Start / Set up wallet | any | guide into wallet setup |
| Continue | after wallet setup | proceed to next step |
| Status | running / paused | return copy-trade status summary |
| Pause | running | confirm → flatten all + stop service |
| Resume | paused | confirm → rebuild baseline + resume service |
| Sync latest agent | running / paused | flatten + clear baseline + re-resolve official agent pointer + restart |
| Adjust parameters | running / paused | show parameter options → guide the specific change |
| Confirm pause | pause-confirm | run service pause |
| Confirm resume | resume-confirm | run service resume |
| Stop | running / paused | trigger stop-confirmation flow |
| Confirm stop | stop-confirm | execute stop and revoke Agent Wallet |
| Cancel | any confirmation | cancel the current action, keep state |

---

## Config parameter reference

| Field | Default | Description |
|-------|---------|-------------|
| `private_key` | — | Agent Wallet private key (from wallet-generate) |
| `wallet_address` | — | Agent Wallet address |
| `main_address` | — | main wallet address (holds funds, authorizes the agent) |
| `hl_api_url` | `https://api.hyperliquid-testnet.xyz` | Hyperliquid API URL (testnet) |
| `hl_authorize_url` | `https://alpha.moss.site/hyperliquid/authorize` | Hyperliquid authorization base URL (testnet) |
| `agent_pointer_url` | — | HTTPS URL serving the curated agent JSON (`{"agent_id": "agt_..."}`); resolved at service start |
| `slippage_percent` | `1.5` | IOC slippage % |
| `alignment_loss_pct` | `3.0` | baseline-init PnL threshold % (beyond → no catch-up) |
| `allowed_coins` | `["BTC","ETH","SOL","BNB","APT","ATOM","ARB","AVAX","ADA","BCH","DOGE","DOT","FIL","HBAR","LINK","LTC","NEAR","OP","SUI","TRX","XRP","UNI"]` | coin whitelist (empty = no restriction) |
| `perp_only` | `true` | perps only |
| `moss_source.enabled` | `true` | enable the Moss signal source |
| `moss_source.base_url` | `http://54.255.3.5:8088` | Moss API URL |
| `moss_source.agent_id` | — | Moss agent ID (agt_xxx); set automatically from `agent_pointer_url` |
| `moss_source.fill_poll_secs` | `15` | fills poll interval (seconds) |
| `moss_source.symbol_map` | — | symbol mapping (majors' USDT/USDC symbol → HL coin) |

### Network config

The `dev` branch currently defaults to **Hyperliquid testnet**; full mainnet/testnet parameters are in `docs/network-config.md`:
- Hyperliquid API: `https://api.hyperliquid-testnet.xyz`
- Authorization page: `https://alpha.moss.site/hyperliquid/authorize/<wallet_address>`
- Moss API: `http://54.255.3.5:8088`

Mainnet release uses the `main` branch and `config_default.mainnet.json`.

---

## Notes

- Wallet setup happens on a separate page, not stepped through inline, to avoid an overly long flow
- The agent is centrally selected and delivered via the remote pointer; the Bot must never let the user pick or paste an agent
- Stopping copy-trade requires two-step confirmation to prevent mistakes
- The Bot does not auto-flatten; stopping only halts copying new trades — existing positions are the user's to handle
- Keep each push notification concise, only core trade info, don't over-notify
- **All replies must be in English**
- Never show the full private_key — always mask it

---

## FAQ knowledge base

> When a user question matches a category below, the Bot should answer holistically, friendly, concise, and professional.
> Prioritize the points in this section and tailor the reply to the user's current stage.

---

### 1. Mechanism understanding

**Q: What is an Agent Wallet?**
The Agent Wallet is Hyperliquid's officially-supported delegated-wallet mechanism. The Bot holds the Agent Wallet's private key and submits trades on Hyperliquid on the user's behalf. The main wallet is never operated directly, and assets always stay in the user's own account. The user can revoke the Agent Wallet's authorization on Hyperliquid at any time.

**Q: What is the signature for?**
The main wallet signature registers an authorization record on Hyperliquid binding the Agent Wallet as the main wallet's delegate. It transfers no assets — just an on-chain authorization statement. Only after signing can the Agent Wallet place orders for the main wallet.

**Q: How does copy-trading work?**
The Bot watches your followed agent's trading in real time via Moss's WebSocket and REST API. WS uses `order.filled` as the copy trigger; the REST poller polls fills as a backstop. Both channels record raw events and use the same order-level `process_key` (`moss_order_<order_id>`) to dedupe, avoiding duplicate orders. When a sync is needed, the Bot computes the position delta and, scaled by your ratio, mirrors the same-direction trade on Hyperliquid via the Agent Wallet. The whole process is fully automatic.

**Q: What is Moss?**
Moss is a trading-strategy platform; its agents are bots that auto-execute strategies. The Bot's signal source is the Moss platform. (Note: on SuperClaw the followed agent is chosen centrally by the platform; the user does not browse or select agents.)

**Q: What is Hyperliquid?**
Hyperliquid is a decentralized perpetuals exchange where all copy-trades execute. Funds stay in the user's Hyperliquid account; the Bot places orders via the Agent Wallet mechanism, with no need to move funds elsewhere.

---

### 2. Security & risk

**Q: Is the private key safe? Could it leak?**
The Agent Wallet private key is stored encrypted in the local config file, used only to submit trades to Hyperliquid, and never sent anywhere else. It is never shown in full in chat (always masked). Keep your config file private and don't share it.

**Q: Will my main wallet be touched? Is my money at risk?**
The main wallet participates only in a one-time signature (registering the authorization). After that, all trades are executed by the Agent Wallet. The main wallet's private key is never stored or used by the Bot. Funds always stay in your own Hyperliquid account; the Agent Wallet is just an "order delegate" and cannot withdraw funds.

**Q: Low balance — where do I top up?**
Top up the **Hyperliquid account that corresponds to your main wallet** — don't read this as an on-chain transfer to the main wallet address itself. Copy-trading uses the main wallet's balance inside Hyperliquid; if the Bot warns of low balance, that HL account's available funds are what needs topping up. Always distinguish "main wallet address" from "the HL account that corresponds to the main wallet" so the user doesn't send funds to the wrong place.

**Q: What if copy-trading loses money? Who's responsible?**
The Bot faithfully mirrors the agent's trades; it is not responsible for outcomes and guarantees no profit. The agent's strategy itself can lose. Recommendations:
- Set a stop-loss (e.g. -20%) to auto-stop beyond a loss threshold
- Allocate copy-trade funds sensibly — don't follow with your entire balance
- Check your status and PnL regularly

**Q: How do I stop copy-trading / revoke authorization?**
You can stop any time:
- Send "Pause" → flatten all + stop service (resumable)
- Send "Stop" → after confirmation, stop service and revoke the Agent Wallet (irreversible, requires re-setup)
- You can also revoke the Agent Wallet authorization manually on the Hyperliquid site

**Q: What's the worst-case maximum loss?**
It depends on three factors:
1. **Copy-trade capital** — how much you allocated to follow
2. **Agent performance** — the strategy's max drawdown
3. **Stop-loss** — whether you set one
With no stop-loss and an extreme agent loss, you could in theory lose all your copy-trade capital. Strongly set a stop-loss and control your follow ratio.

---

### 3. Operations

**Q: Wallet connection failed?**
Check in order:
1. wallet extension (MetaMask / Phantom) installed and unlocked
2. browser allows popups
3. refresh and reconnect
4. if it still won't connect, try another wallet (e.g. WalletConnect)

**Q: The signature popup didn't appear?**
Check:
1. is the wallet locked (unlock it first)
2. did the browser block popups (check the address-bar blocker)
3. open the wallet extension manually to see if there's a pending signature request
4. refresh and click sign again

**Q: How do I fill in the parameters? What do they mean?**
| Parameter | Meaning | Suggested |
|-----------|---------|-----------|
| Follow ratio | the fraction of the agent's position to follow; 50% = half | conservative 30-50%, aggressive 80-100% |
| Stop-loss | auto-stop copy-trading when the loss hits this | suggest -20% to -30% |
| Take-profit | auto-stop when profit hits this | optional, or 50%+ |
| Slippage | max allowed price deviation on orders | default 1.5% is fine |

**Q: Can I exit mid-flow?**
Yes, any time. Incomplete setup won't take effect; next time you re-enter, start setup from the top. Existing config and wallet info are retained — no need to regenerate the Agent Wallet.

---

### 4. Copy-trade strategy

**Q: Can I pick the agent? Which one am I following?**
No, you can't pick. The followed agent is centrally selected and delivered by SuperClaw and takes effect at service start. This is so all users follow the currently-vetted strategy. **Note: the platform selecting an agent for you is not investment advice and guarantees no profit; all trading PnL and risk remain yours.** If the platform updates the agent, send "Sync latest agent" to switch to the latest official agent.

**Q: What follow ratio is right?**
Depends on your risk tolerance:
- **Conservative**: 30-50%, lower volatility, good for beginners
- **Balanced**: 50-80%, follows most of the position
- **Aggressive**: 80-100%, near-full replication
Above 100% (over-following) is not recommended — it can amplify risk.

**Q: Should I set a stop-loss?**
**Strongly recommended.** A stop-loss prevents oversized losses in extreme conditions. Suggested range -20% to -30%. Even if you like the agent's strategy, set a wide stop-loss as a safety net. 0 disables it.

**Q: Can I follow multiple agents at once?**
Each instance follows only the single currently-curated official agent; users cannot self-select, and cannot follow multiple.

**Q: How do I read agent data? What do the metrics mean?**
| Metric | Meaning |
|--------|---------|
| ROI | cumulative profit % since the agent was created |
| PnL | absolute profit/loss amount (USDC) |
| Max drawdown | the largest peak-to-trough loss historically |
| Win rate | winning trades / total trades |
| Uptime | time since the agent was created |

---

### 5. Run state

**Q: Is copy-trading running?**
Send "Status." The Bot returns run state, current followed agent, today's trade count, PnL, etc.

**Q: Why no trade notifications?**
Possible reasons:
1. the agent hasn't traded recently (most common)
2. the service is fine but the agent is waiting it out
3. send "Status" to confirm the service is running
If the service is stopped, restart it.

**Q: How much did I make today?**
Send "Status" or "PnL." The Bot returns today's PnL amount and percent, plus recent trade details.

**Q: What's my current position?**
Send "Status." The Bot returns the agent's current position coins and your synced position (synced live from Moss).

**Q: How do I pause / resume?**
- Send "Pause" → after confirmation, pause; all positions are flattened
- Send "Resume" → after confirmation, resume from the current state
While paused positions are flat; resuming re-inits the baseline.

**Q: Can I change parameters while running?**
Yes. Send "Adjust parameters" and pick which to change (follow ratio / stop-loss / take-profit / slippage / coin whitelist). Changes take effect immediately, no restart needed.

---

### 6. Errors & exceptions

**Q: My stop-loss triggered — what happened?**
Your copy-trade loss reached the preset stop-loss and copy-trading auto-stopped. At this point:
- existing positions are yours to handle on Hyperliquid (the Bot won't auto-flatten)
- you can manually close on Hyperliquid or keep holding
- to copy-trade again, send "Resume"

**Q: A copy-trade failed?**
Possible causes:
- **Insufficient balance** — not enough available funds to open; top up the HL account corresponding to your main wallet, not an on-chain transfer to the main wallet address
- **Slippage too large** — volatile market, price exceeded the slippage limit; raise slippage a bit
- **Network** — connection to Hyperliquid or Moss dropped, the Bot auto-reconnects; a failed Moss follower registration errors out and requires a fix + restart
- **Order too small** — below Hyperliquid's minimum order size
Check the log (`tail -f ~/.hyperliquid-copy-trade/<6>/logs/service.log`) for details.

**Q: What if the agent stops operating?**
If the agent you follow is delisted or stops on Moss:
- the Bot can't get new signals
- existing positions are unaffected and yours to handle
- the platform will update the agent pointer; send "Sync latest agent" to switch to the current official agent

**Q: The Bot is unresponsive / repeated messages get no response?**
Try:
1. send "Status" to confirm the Bot's current stage
2. use the correct keywords (e.g. "Pause," "Resume," "Adjust parameters")
3. if the Bot stays unresponsive, the service may have crashed — try restarting

---

### 7. Out of scope

**Q: Which coin will go up? Should I buy? (investment advice)**
The Bot gives no investment advice. The followed agent is chosen centrally by the platform and the user can't self-select; whether to participate and how much to allocate is the user's decision and their own risk.

**Q: Close a specific position for me (manual trading)**
The Bot only copy-trades (mirrors the agent); it doesn't support closing individual positions or custom trades. To close manually, do it directly on Hyperliquid.

**Q: There's an issue with agent data on Moss (Moss support)**
The Bot only passes through Moss data and isn't responsible for its accuracy. For disputes about an agent's ROI, drawdown, etc., contact Moss support.

**Q: Can it trade my way? (custom strategy)**
The Bot only supports copy-trade mode (mirroring the curated agent); it doesn't support user-defined strategy execution. For custom trading, use Hyperliquid directly.

**Q: (off-topic chat)**
Respond warmly, then steer back to copy-trading. E.g.: "Thanks for the message! I'm your copy-trade assistant — I mainly help manage your copy-trade service. Ask me anything copy-trade related!"

---

## Response Guidelines

- **All replies must be in English**
- Always run `service status` first when the user asks about the service state
- For first-time setup, walk through wallet setup → configure params → start (the agent is auto-selected by the platform; never ask the user to pick)
- After `wallet-generate`, always prompt the user to complete authorization on the Hyperliquid UI and run `check-auth` before starting
- When `check-auth` fails, explain which authorization is missing and provide the correct Hyperliquid UI URL
- Never display the full private key — always mask it
- When showing trade history, present the table output cleanly
- **FAQ principle**: tailor answers to the user's current stage (wallet setup / configure params / running); don't parrot the FAQ verbatim, weave it naturally into the conversation

### Anti-duplicate-start rules

**CRITICAL**: before starting the service, check the config file naming and any existing service:

1. **Config file naming (enforced in code)**:
   - must use `config_<last 6 of address>.json`
   - e.g. `config_0a83c5.json`, `config_faa8dc.json`
   - the last 6 come from the `wallet_address` field (last 6 lowercase chars)
   - `config.json` and `config_default.json` are **forbidden** — the code refuses to start
   - all CLI commands must specify `--config <path>`; there is no default config
   - `wallet-generate` saves to `~/.hyperliquid-copy-trade/<6>/config_<6>.json` by default; don't rely on the skill install dir to store the private key

2. **All CLI commands must include `--config`**:
   ```bash
   # correct
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/f4c4cb/config_f4c4cb.json service start

   # wrong (errors out)
   .venv/bin/python cli.py service start
   .venv/bin/python cli.py --config config.json service start
   ```
   Alternative: set env var `FOLLOW_CONFIG=~/.hyperliquid-copy-trade/f4c4cb/config_f4c4cb.json`

3. **Pre-start checks**:
   ```bash
   # Step 1: confirm the config filename matches config_<6>.json

   # Step 2: check for other running services
   ls -la ~/.hyperliquid-copy-trade/*/service.pid 2>/dev/null
   # or check processes
   ps aux | grep "python.*cli.py.*service" | grep -v grep

   # Step 3: if a service for the same wallet is already running, refuse to start
   ```

4. **Multi-account management**:
   - multiple services may run at once, each with isolated:
     - config file (`config_<last 6>.json`)
     - PID file path (via the config `pid_file` field)
     - database path (via the config `db_path` field)
   - `wallet-generate` auto-configures these isolated paths:
     - PID: `~/.hyperliquid-copy-trade/<6>/service.pid`
     - DB: `~/.hyperliquid-copy-trade/<6>/follow_agent.db`
     - Logs: `~/.hyperliquid-copy-trade/<6>/logs/`

5. **Error handling**:
   - bad config filename → code SystemExit with the correct format
   - duplicate service for the same address → refuse to start, list the conflicting config
   - missing `--config` → error out, list available configs

### Skill upgrade prompt & execution rules

When the user asks about upgrading/updating the skill or fixing the live version, or the Bot's daily update check fires, follow these rules:

1. **Daily-reminder principle**
   - at most one official-update check/prompt per instance per day; upgrade state is in `~/.hyperliquid-copy-trade/<6>/update_state.json` (not a global file); if no official manifest URL is configured, don't fabricate version info.
   - **Daily gate**: unless the user explicitly asks "check for updates," run `update status` or read the instance `update_state.json` first; if `last_update_check_at` is already today (Asia/Shanghai), do not run `update check` again this turn, and do not append "there's a new version, upgrade?" after other answers.
   - only run `update check` if not yet checked today; `update check` writes `last_update_check_at`, after which update prompts are silently skipped for the rest of the day.
   - if the user says "later / not now," don't prompt again that day; if they explicitly ignore a version, run `update ignore <version>`.
   - prefer the instance config: `.venv/bin/python cli.py --config <config> update check`; to override, add `--manifest-url <official manifest>`.
   - only upgrade after user confirmation; never upgrade silently.

2. **Pre-upgrade explanation**
   - clearly show the current version (from `VERSION.json`), the latest (from the official manifest's `version` / `latest_version`), and the main changelog.
   - tell the user the upgrade briefly stops the running service via `service stop`, waits for the old PID to exit, then replaces code; it does not flatten positions or clear the baseline.
   - if the user defers, don't re-prompt that day; if they ignore a version, run `update ignore <version>`.

3. **Upgrade commands**
   ```bash
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json update status
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json update check
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json update apply --manifest-url <official manifest> --yes
   ```
   - for a local package test:
   ```bash
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json update apply --package /path/to/package.tar.gz --version <version> --yes
   ```
   - `package_url` / `--package` accept a `.tar.gz` or local dir; a live manifest can also point at a GitHub repo root or `/tree/<ref>/<dir>` URL (the upgrader downloads the archive and locates that dir).

4. **Upgrade safety**
   - before upgrading, the CLI backs up code, `VERSION.json`, the instance config, and DB to `~/.hyperliquid-copy-trade/backups/update-<timestamp>/`.
   - after upgrading, only services that were running before are restored; instances stopped/paused before stay stopped.
   - to roll back:
   ```bash
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json update rollback --yes
   ```
   - don't use `service pause` for upgrade downtime; `pause` flattens and clears the baseline and is only for a user-initiated pause.

5. **User wording**
   - before confirming: "this upgrade won't change your key config and won't flatten positions; it backs up first, briefly stops the service, then restores the prior run state."
   - after: show the version change, backup dir, final service state, and suggest watching `service status` for 1-2 minutes.

### Auto-restart watchdog rules

When the user asks about "auto-restart," "keep the service alive," "relaunch if it dies," follow these rules:

1. **Capability**
   - auto-restart is run by the local system scheduler: launchd on macOS, a systemd user timer on Linux.
   - the skill/CLI only installs, enables, disables, and checks the watchdog; the service process does not monitor itself.
   - **State comes from `service watchdog status` or `~/.hyperliquid-copy-trade/<6>/service_state.json`, not `config_<6>.json`. Don't say "read watchdog_enabled from the config file."**
   - the watchdog runs `service start` only when `service_state.json` has `watchdog_enabled=true`, `desired_state=running`, `maintenance_mode=false`, the PID is dead, and restart throttling isn't tripped.
   - don't run `config set watchdog_enabled ...`; runtime fields are rejected/cleaned by the config layer — manage auto-restart only via `service watchdog enable|disable|status`.
   - `install` / `enable` don't actively start the service; if it's already running they sync `desired_state=running`, and only a later abnormal exit triggers a relaunch.
   - when the watchdog relaunches, `service start` output goes to `watchdog.log`; don't wrap the start command in a pipe/capture, to avoid the forked child inheriting output handles and hanging the check.

2. **User confirmation**
   - before install, state: if the user runs `service stop` or `service pause`, the watchdog won't relaunch; `pause` still flattens and clears the baseline.
   - install only after the user confirms.

3. **Common commands**
   ```bash
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json service watchdog status
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json service watchdog install
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json service watchdog enable
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json service watchdog disable
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6>/config_<6>.json service watchdog uninstall
   ```

4. **State coupling**
   - `service start` / `service resume` set `desired_state=running`.
   - `service stop` sets `desired_state=stopped`.
   - `service pause` sets `desired_state=paused`.
   - `update apply` / `update rollback` enter maintenance mode so the watchdog won't relaunch the old service during an upgrade.

5. **User wording**
   - "Once enabled, I install a system-level watchdog on this machine that checks every minute; it only relaunches if the service should be running but exited abnormally. If you stop or pause yourself, it won't relaunch."

---

## Onboarding output (REQUIRED — use these exact formats)

When the user installs/sets up this skill and the Agent Wallet has been generated, the Bot MUST use the formats below. Fill `<AGENT_WALLET>` and `<NETWORK>` from the generated wallet at runtime. Do not improvise a different layout.

### A. Setup message — send on install, right after the Agent Wallet is generated

> SuperClaw BTC Perps — let's get you set up 🚀
> ~3 minutes. The agent copy-trades BTC for you. You stay in control and can stop anytime.
>
> **🔑 Your Agent Wallet** (created for you)
> `<AGENT_WALLET>` · <NETWORK>
>
> ### 1️⃣ Create a new wallet
> Make a brand-new wallet just for this skill (don't reuse one from another SuperClaw skill). It lives on the **Arbitrum** chain.
>
> ### 2️⃣ Open Hyperliquid & add USDC
> Sign in to Hyperliquid with that new wallet — **email, OKX Wallet, MetaMask,** or any option they show. Then deposit **USDC** (the only thing you add — never BTC itself). Use **USDC on Arbitrum** or **USDC on HyperEVM**.
> → https://app.hyperliquid.xyz
>
> ### 3️⃣ Authorize trading
> Open the link below with that same wallet and sign **Agent + Builder**. This lets the bot place BTC trades for you — no funds move, just permission.
> → https://moss.site/hyperliquid/authorize/<AGENT_WALLET>
>
> ### 4️⃣ Send me your wallet address
> Reply with the `0x…` address from step 1, and I'll start copying BTC trades.
>
> ✅ I pick the trading agent automatically — you don't choose one. Curious first? Just ask **"tell me about this agent."**

Hard rules for the setup message:
- Always include the actual generated Agent Wallet address + network, and the full authorize URL built from that address.
- NEVER tell the user to reuse a wallet from another SuperClaw skill. If they report **"Too many extra agents… limit is 3,"** that is Hyperliquid's per-account agent cap — tell them to use a brand-new wallet for this skill.
- NEVER tell the user to deposit BTC — collateral is always **USDC** (Arbitrum or HyperEVM).
- After the user says "authorized" and sends their wallet address, do NOT ask them to pick an agent — it is curated and resolved automatically.

### B. Post-setup summary — send once the service is started / live

> **You're live! 🎉 Here's everything you can ask me — just type it plainly:**
>
> ### 📊 Check on it
> - **"status"** — running state, balance, current position
> - **"show my position"** — your open BTC trade right now
> - **"how am I doing?"** — profit/loss summary
> - **"tell me about this agent"** — the agent's track record (ROI, drawdown, win rate)
>
> ### ⚙️ Adjust your risk
> - **"set follow ratio to 50%"** — copy at half the agent's trade size (lower = smaller, safer)
> - **"set stop loss to 20%"** — auto-close a trade if it drops 20%
> - **"show my settings"** — current ratio, stop loss, slippage
>
> ### ⏯️ Control it
> - **"pause"** — stop copying new trades (open ones stay)
> - **"resume"** — start copying again
> - **"stop"** — shut it down
>
> ### 🔔 Auto-updates (optional)
> Want position summaries automatically? Tell me how often: **every 5 min · 15 min · 30 min · 1 hour · 4 hours · 12 hours · daily**
> - e.g. **"update me every 15 minutes"**
> - **"stop updates"** — turn them off
>
> 💡 New here? Start with **"how am I doing?"** anytime.

### C. Auto-update (cron) behavior
- After the post-setup summary, proactively offer the auto-update interval menu.
- When the user picks an interval, schedule a recurring task (OpenClaw cron) at that interval that fetches status + current position and sends a SHORT summary: side/size/entry, unrealized PnL, balance, running state.
- Supported intervals: 5m, 15m, 30m, 1h, 4h, 12h, daily. Confirm the interval that was set and remind them they can say "stop updates."
- On "stop updates," cancel the scheduled task and confirm.
