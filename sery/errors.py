"""Typed exceptions mirroring the data.sery.ai error envelope.

Each HTTP error from POST /public/v1/query maps to a specific class so callers
can branch on failure mode instead of parsing status codes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class SeryError(Exception):
    """Base class for every error raised by the SDK."""


class AuthError(SeryError):
    """401 — missing, malformed, or revoked API key."""


class QueryError(SeryError):
    """400 — the SQL had no sery:// references, a malformed address, or an
    unsupported protocol."""


class MachineNotFound(SeryError):
    """404 — a referenced machine doesn't exist in the workspace."""


class AmbiguousMachine(SeryError):
    """409 — a machine alias matched more than one machine. ``candidates``
    holds {machine_id, label} dicts so you can re-issue with a machine_id."""

    def __init__(self, message: str, candidates: List[Dict[str, str]]):
        super().__init__(message)
        self.candidates = candidates


class CrossMachineJoinUnsupported(SeryError):
    """422 — the query spans multiple machines (distributed joins aren't
    supported yet). ``machines`` holds the {machine_id, label} dicts."""

    def __init__(self, message: str, machines: List[Dict[str, str]]):
        super().__init__(message)
        self.machines = machines


class MachinesUnavailable(SeryError):
    """503 — every targeted machine was offline or errored. ``failures``
    holds {machine, error} dicts."""

    def __init__(self, message: str, failures: List[Dict[str, str]]):
        super().__init__(message)
        self.failures = failures


class APIError(SeryError):
    """Any other non-2xx response. Carries the status code and raw body."""

    def __init__(self, status_code: int, body: Any):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Sery API error {status_code}: {body}")


def _detail_message(detail: Any, fallback: str) -> str:
    if isinstance(detail, dict):
        return str(detail.get("message") or fallback)
    if isinstance(detail, str):
        return detail
    return fallback


def raise_for_response(status_code: int, body: Any) -> None:
    """Translate a non-2xx (status_code, parsed body) into the right
    exception. ``body`` is the decoded JSON (usually ``{"detail": …}``)."""
    detail: Any = body.get("detail") if isinstance(body, dict) else body

    if status_code == 401:
        raise AuthError(_detail_message(detail, "Authentication failed"))
    if status_code == 400:
        raise QueryError(_detail_message(detail, "Bad query"))
    if status_code == 404:
        raise MachineNotFound(_detail_message(detail, "Machine not found"))
    if status_code == 409:
        cands = detail.get("candidates", []) if isinstance(detail, dict) else []
        raise AmbiguousMachine(_detail_message(detail, "Ambiguous machine"), cands)
    if status_code == 422:
        machines = detail.get("machines", []) if isinstance(detail, dict) else []
        raise CrossMachineJoinUnsupported(
            _detail_message(detail, "Cross-machine join unsupported"), machines
        )
    if status_code == 503:
        failures = detail.get("failures", []) if isinstance(detail, dict) else []
        raise MachinesUnavailable(
            _detail_message(detail, "Machines unavailable"), failures
        )
    raise APIError(status_code, body)
