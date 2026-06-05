"""
Hyperliquid sub-account management (SuperClaw isolated per-asset skills).

Each per-asset skill trades into its own named sub-account under the user's
master wallet, so margin and PnL are isolated from other skills. Orders are
routed to the sub-account via the Exchange ``vault_address`` (see trader.py);
this module only handles *creating* the sub-account and recording its address.

Design decisions (v1):
- Create only. Funding is NOT automated here. ``sub_account_transfer``'s ``usd``
  field is an integer in micro-units and moving funds is a sensitive action, so
  the skill guides the user to fund the sub-account themselves (HL Portfolio →
  Transfer, or a future confirmed CLI). This also avoids depending on whether an
  agent wallet may sign transfers.
- Agent-signed create attempt, guided fallback. We try to create the sub-account
  with the Agent Wallet. If Hyperliquid rejects agent-signed creation (only the
  master may create), we surface clear instructions for the user to create it in
  the HL UI and paste the address.
- Idempotent. If ``subaccount_address`` is already set in config, this is a no-op.
"""

import logging

from . import config as cfg

logger = logging.getLogger("follow_agent.subaccount")


def _extract_address(resp: dict) -> str | None:
    """Pull the new sub-account address out of a createSubAccount response."""
    if not isinstance(resp, dict):
        return None
    if resp.get("status") != "ok":
        return None
    data = resp.get("response", {}).get("data")
    if isinstance(data, str) and data.startswith("0x"):
        return data.strip()
    # Some responses nest the address differently; be defensive.
    if isinstance(data, dict):
        addr = data.get("subAccountUser") or data.get("address")
        if isinstance(addr, str) and addr.startswith("0x"):
            return addr.strip()
    return None


def _write_subaccount_address(address: str) -> None:
    def _mutate(c: dict) -> None:
        c["subaccount_address"] = address
    cfg.update_config(_mutate)


def ensure_subaccount() -> str | None:
    """
    Ensure a sub-account exists and its address is recorded in config.

    Returns the sub-account address, or None if it could not be created
    automatically (caller should then guide the user to create it manually).

    Never raises: best-effort, called at service start.
    """
    existing = str(cfg.get("subaccount_address", "") or "").strip()
    if existing:
        return existing

    name = str(cfg.get("subaccount_name", "") or "").strip()
    if not name:
        logger.error("subaccount_name not configured; cannot create sub-account")
        return None

    # Build an Exchange client (Agent Wallet signer). Imported lazily so this
    # module stays importable without the HL SDK present.
    try:
        from eth_account import Account
        from hyperliquid.exchange import Exchange
    except Exception as exc:  # noqa: BLE001
        logger.error("HL SDK unavailable for sub-account creation: %s", exc)
        return None

    private_key = cfg.get("private_key", "")
    if not private_key:
        logger.error("private_key not configured; cannot create sub-account")
        return None
    api_url = cfg.get("hl_api_url", "https://api.hyperliquid-testnet.xyz")
    main_address = cfg.get("main_address") or None

    try:
        wallet = Account.from_key(private_key)
        exchange = Exchange(wallet, api_url, account_address=main_address)
        resp = exchange.create_sub_account(name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("agent-signed create_sub_account failed: %s", exc)
        return None

    address = _extract_address(resp)
    if not address:
        logger.warning(
            "create_sub_account returned no usable address (resp=%s); "
            "user may need to create '%s' manually", resp, name,
        )
        return None

    _write_subaccount_address(address)
    logger.info("sub-account '%s' created and recorded: %s", name, address)
    return address


def guidance_text() -> str:
    """Human-facing instructions for manual sub-account setup (guided fallback)."""
    name = str(cfg.get("subaccount_name", "sc-hype") or "sc-hype")
    return (
        f"Could not auto-create the sub-account. On Hyperliquid, create a "
        f"sub-account named '{name}', then set its address:\n"
        f"  config set subaccount_address 0xYOUR_SUBACCOUNT\n"
        f"Then fund it by transferring USDC from your main account into "
        f"'{name}' (Hyperliquid Portfolio -> Transfer)."
    )
