#!/usr/bin/env python3
"""Print the CURATED agent's overall track record (ROI, PnL, drawdown, etc.).

This is the agent the skill follows — NOT the user's own copy-trade history.
The agent runs this and relays the output. Pure stdlib (urllib/json), so no
venv is required.

Usage:
    python3 agent_info.py --config /path/to/config_<id>.json [--zh]

Resolves the agent id from the instance config (moss_source.agent_id); if that
is empty (service not started yet), falls back to the repo's active_agent.json
pointer URL in the config.
"""

import argparse
import json
import sys
import urllib.request

DEFAULT_BASE = "https://ai.moss.site"


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "superclaw-agent-info"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def _num(d, *path, default="-"):
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur not in (None, "") else default


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--zh", action="store_true")
    args, _ = ap.parse_known_args()

    try:
        with open(args.config) as f:
            cfg = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: could not read config {args.config}: {e}", file=sys.stderr)
        sys.exit(1)

    moss = cfg.get("moss_source", {}) if isinstance(cfg.get("moss_source"), dict) else {}
    base = str(moss.get("base_url") or DEFAULT_BASE).rstrip("/")
    if base.endswith("/api"):
        base = base[:-4]
    agent_id = str(moss.get("agent_id") or "").strip()

    # Fallback: resolve from the curated pointer if config has no agent yet
    if not agent_id:
        ptr = str(cfg.get("agent_pointer_url") or "").strip()
        if ptr:
            try:
                agent_id = str(_get(ptr).get("agent_id") or "").strip()
            except Exception:  # noqa: BLE001
                pass
    if not agent_id:
        print("Could not determine the curated agent id (start the service once, or check agent_pointer_url).")
        sys.exit(0)

    try:
        d = _get(f"{base}/api/v2/moss/trader/realtime/bots/{agent_id}")
    except Exception as e:  # noqa: BLE001
        print(f"Could not fetch agent info: {e}")
        sys.exit(0)

    lang = "zh" if args.zh else "en"
    bot = d.get("bot", {}) if isinstance(d.get("bot"), dict) else {}
    perf = d.get("performance", {}) if isinstance(d.get("performance"), dict) else {}
    acct = d.get("account", {}) if isinstance(d.get("account"), dict) else {}

    name = _num(bot, "name_i18n", lang) or bot.get("name", agent_id)
    strat = _num(d, "prompt", "full_i18n", lang)
    if strat == "-":
        strat = _num(d, "prompt", "brief_i18n", lang)

    roi = perf.get("roi", "-")
    pnl = perf.get("pnl", acct.get("realized_pnl", "-"))
    maxp = perf.get("max_profit_percent", "-")
    maxp_usd = perf.get("max_profit", "-")
    dd = perf.get("max_drawdown", "-")
    liq = perf.get("liquidation_count", "-")
    wr = perf.get("overall_win_rate", "-")
    pf = perf.get("profit_factor", "-")
    trades = perf.get("total_trades", "-")
    status = bot.get("status", "-")
    days = bot.get("running_days", "-")

    if lang == "zh":
        out = [f"Agent（官方挑选）：{name}  ({status}，运行 {days} 天)"]
        if strat and strat != "-":
            out += ["", "— 策略 —", f"  {strat}"]
        out += [
            "", "— 核心指标（该 Agent 的整体表现，非你的记录）—",
            f"  ROI(收益率)      : {roi}%",
            f"  账户累计盈亏      : {pnl} USDC",
            f"  历史最大盈利      : {maxp}%  ({maxp_usd} USDC)",
            f"  最大回撤          : {dd}%   ← 风险",
            f"  爆仓次数          : {liq}",
            "", "— 其他 —",
            f"  胜率 / 盈亏比      : {wr}% / {pf}",
            f"  交易笔数          : {trades}",
            "", "注意：官方挑选 Agent 不构成投资建议，也不保证收益；过往业绩不代表未来表现，盈亏与风险由你自担。",
        ]
    else:
        out = [f"Agent (platform-curated): {name}  ({status}, running {days} days)"]
        if strat and strat != "-":
            out += ["", "— Strategy —", f"  {strat}"]
        out += [
            "", "— Key metrics (this agent's OVERALL record, not your own) —",
            f"  ROI               : {roi}%",
            f"  Account PnL       : {pnl} USDC",
            f"  Max profit        : {maxp}%  ({maxp_usd} USDC)",
            f"  Max drawdown      : {dd}%   <- risk",
            f"  Blow-ups (liqs)   : {liq}",
            "", "— Secondary —",
            f"  Win rate / PF     : {wr}% / {pf}",
            f"  Trades            : {trades}",
            "", "Note: the platform selecting an agent for you is not investment advice and "
            "guarantees no profit; past performance does not predict future results, and you bear all risk.",
        ]
    print("\n".join(out))


if __name__ == "__main__":
    main()
