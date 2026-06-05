"""
Curated-agent info card (SuperClaw) — shared identically across all per-asset skills.

Fetches the public Moss agent metadata endpoint and formats the metrics users
ask for before committing capital. Highlighted order (per product spec):
  1. ROI   2. Account PnL   3. Max profit   4. Max drawdown   5. Blow-ups (liquidations)
then win rate / profit factor / trades as secondary.

Max drawdown and blow-ups are ALWAYS shown — a headline ROI without the downside
misleads. This is not investment advice; the user bears all risk.
"""

import logging

from . import config as cfg
from .moss_client import MossClient

logger = logging.getLogger("follow_agent.agent_card")


def _num(d: dict, *path, default="-"):
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur not in (None, "") else default


def fetch_card(lang: str = "en") -> dict | None:
    """Fetch + map agent metrics. Returns a flat dict, or None on failure."""
    moss_cfg = cfg.get_moss_source_config()
    agent_id = str(moss_cfg.get("agent_id", "") or "").strip()
    base_url = str(moss_cfg.get("base_url", "") or "").strip()
    if not agent_id or not base_url:
        logger.error("agent-info: missing agent_id or base_url")
        return None
    try:
        client = MossClient(base_url=base_url, agent_id=agent_id, private_key=cfg.get("private_key", ""))
        data = client.get_agent_info()
    except Exception as exc:  # noqa: BLE001
        logger.error("agent-info fetch failed: %s", exc)
        return None
    if not isinstance(data, dict):
        return None

    bot = data.get("bot", {}) if isinstance(data.get("bot"), dict) else {}
    perf = data.get("performance", {}) if isinstance(data.get("performance"), dict) else {}
    acct = data.get("account", {}) if isinstance(data.get("account"), dict) else {}
    lang = "zh" if lang == "zh" else "en"

    name = _num(bot, "name_i18n", lang) or bot.get("name", agent_id)
    brief = _num(data, "prompt", "brief_i18n", lang)
    strategy = _num(data, "prompt", "full_i18n", lang)
    if strategy == "-":
        strategy = brief

    return {
        "agent_id": agent_id,
        "name": name,
        "brief": brief,
        "strategy": strategy,
        "status": bot.get("status", "-"),
        "running_days": bot.get("running_days", "-"),
        "roi_pct": perf.get("roi", "-"),
        "pnl": perf.get("pnl", acct.get("realized_pnl", "-")),
        "max_profit_pct": perf.get("max_profit_percent", "-"),
        "max_profit_usd": perf.get("max_profit", "-"),
        "max_drawdown_pct": perf.get("max_drawdown", "-"),
        "liquidation_count": perf.get("liquidation_count", "-"),
        "win_rate_pct": perf.get("overall_win_rate", "-"),
        "profit_factor": perf.get("profit_factor", "-"),
        "total_trades": perf.get("total_trades", "-"),
    }


def render_text(card: dict, lang: str = "en") -> str:
    """Plain-text card. Highlights first; drawdown + blow-ups always shown."""
    if lang == "zh":
        lines = [f"Agent：{card['name']}  ({card['status']}，运行 {card['running_days']} 天)"]
        if card.get("strategy") and card["strategy"] != "-":
            lines += ["", "— 策略 —", f"  {card['strategy']}"]
        lines += [
            "",
            "— 核心指标 —",
            f"  ROI(收益率)       : {card['roi_pct']}%",
            f"  账户累计盈亏       : {card['pnl']} USDC",
            f"  历史最大盈利       : {card['max_profit_pct']}%  ({card['max_profit_usd']} USDC)",
            f"  最大回撤           : {card['max_drawdown_pct']}%   ← 风险",
            f"  爆仓次数           : {card['liquidation_count']}",
            "",
            "— 其他 —",
            f"  胜率 / 盈亏比       : {card['win_rate_pct']}% / {card['profit_factor']}",
            f"  交易笔数           : {card['total_trades']}",
            "",
            "注意：官方为你挑选 Agent 不构成投资建议，也不保证收益；过往业绩不代表未来表现，盈亏与风险由你自担。",
        ]
        return "\n".join(lines)

    lines = [f"Agent: {card['name']}  ({card['status']}, running {card['running_days']} days)"]
    if card.get("strategy") and card["strategy"] != "-":
        lines += ["", "— Strategy —", f"  {card['strategy']}"]
    lines += [
        "",
        "— Key metrics —",
        f"  ROI               : {card['roi_pct']}%",
        f"  Account PnL       : {card['pnl']} USDC",
        f"  Max profit        : {card['max_profit_pct']}%  ({card['max_profit_usd']} USDC)",
        f"  Max drawdown      : {card['max_drawdown_pct']}%   <- risk",
        f"  Blow-ups (liqs)   : {card['liquidation_count']}",
        "",
        "— Secondary —",
        f"  Win rate / PF     : {card['win_rate_pct']}% / {card['profit_factor']}",
        f"  Trades            : {card['total_trades']}",
        "",
        "Note: the platform selecting an agent for you is not investment advice and "
        "guarantees no profit; past performance does not predict future results, and "
        "you bear all trading risk.",
    ]
    return "\n".join(lines)
