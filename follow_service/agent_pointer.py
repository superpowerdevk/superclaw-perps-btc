"""
Curated-agent pointer resolver (SuperClaw).

The agent that users follow is selected centrally by the skill admin, not by the
user. The active agent_id is published at a remote, admin-controlled URL
(``agent_pointer_url`` in config) as a small JSON document:

    { "agent_id": "agt_xxxx", "network": "mainnet" }

This module fetches that document at service start (and on resume/switch) and
writes the resolved agent_id into ``moss_source.agent_id``.

Design decisions (v1):
- Read-at-start only. There is no background polling and no per-user notify/
  confirm. Running services are untouched until they next start/resume.
- Resilient fallback. If the fetch fails but the config already has an
  agent_id, we KEEP the last-known agent_id and log a warning, so a transient
  pointer outage never stops an existing follower from restarting.
- Fail-safe. If the fetch fails AND there is no agent_id at all, we return None
  and let the caller's existing validation abort startup with a clear message.
- HTTPS only. The pointer controls where user capital is deployed, so we refuse
  plaintext URLs.
- Only ``agent_id`` is consumed in v1. Other keys (e.g. ``network``) are parsed
  but ignored, reserved for future use.
"""

import json
import logging
import urllib.request

from . import config as cfg

logger = logging.getLogger("follow_agent.agent_pointer")

_FETCH_TIMEOUT_SECS = 10
_USER_AGENT = "superclaw-copytrade/1.0"


def _fetch_pointer(url: str) -> dict:
    """Fetch and parse the pointer JSON document. Raises on any failure."""
    if not url.lower().startswith("https://"):
        raise ValueError(f"agent_pointer_url must use https://, got: {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT_SECS) as resp:  # nosec - admin-controlled https URL
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("agent pointer payload is not a JSON object")
    return data


def _extract_agent_id(data: dict) -> str:
    """Pull a valid agent_id out of the pointer payload. Raises if missing."""
    agent_id = data.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("agent pointer payload missing a valid 'agent_id'")
    agent_id = agent_id.strip()
    if not agent_id.startswith("agt_"):
        # Soft check only: accept it but flag, in case the id format ever changes.
        logger.warning("agent pointer agent_id has unexpected format: %s", agent_id)
    return agent_id


def _write_agent_id(agent_id: str) -> None:
    """Atomically write agent_id into moss_source.agent_id (locked read-modify-write)."""
    def _mutate(c: dict) -> None:
        ms = c.get("moss_source")
        if not isinstance(ms, dict):
            ms = {}
            c["moss_source"] = ms
        ms["agent_id"] = agent_id

    cfg.update_config(_mutate)


def sync_agent_pointer() -> str | None:
    """
    Resolve the curated agent from the remote pointer and persist it to config.

    Returns the agent_id that should be followed, or None if none could be
    resolved (no pointer configured and no existing agent_id, or fetch failed
    with no last-known value).

    Never raises: callers run this best-effort at startup and rely on the
    existing moss_source validation to abort if no agent_id ends up configured.
    """
    url = str(cfg.get("agent_pointer_url", "") or "").strip()
    moss_cfg = cfg.get_moss_source_config()
    current = str(moss_cfg.get("agent_id", "") or "").strip()

    # No pointer configured -> manual mode: use whatever's already in config.
    if not url:
        logger.info(
            "agent_pointer_url not set; using configured agent_id=%s",
            current or "(none)",
        )
        return current or None

    try:
        data = _fetch_pointer(url)
        resolved = _extract_agent_id(data)
    except Exception as exc:  # noqa: BLE001 - any failure falls back to last-known
        if current:
            logger.warning(
                "agent pointer fetch failed (%s); keeping last-known agent_id=%s",
                exc, current,
            )
            return current
        logger.error(
            "agent pointer fetch failed and no agent_id is configured: %s", exc
        )
        return None

    if resolved != current:
        _write_agent_id(resolved)
        logger.info(
            "agent pointer resolved: agent_id %s -> %s",
            current or "(none)", resolved,
        )
    else:
        logger.info("agent pointer resolved: agent_id unchanged (%s)", resolved)
    return resolved
