from __future__ import annotations

import json
import re
from typing import Any

from tools._shared import ROOT, err


STATUS_FILE = ROOT / "helpdesk_data" / "ticket_status.json"
TICKET_ID_PATTERN = re.compile(r"^LAB-[A-Z0-9]{4,12}$")


def check_ticket_status(ticket_id: str = "") -> dict[str, Any]:
    if not isinstance(ticket_id, str):
        return {"tool": "check_ticket_status", "error": "invalid_ticket_id_type"}

    normalized_id = ticket_id.strip().upper()
    if not TICKET_ID_PATTERN.fullmatch(normalized_id):
        return {"tool": "check_ticket_status", "error": "invalid_ticket_id"}

    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        for item in data["tickets"]:
            if item["ticket_id"] == normalized_id:
                return {
                    "tool": "check_ticket_status",
                    "ticket_id": item["ticket_id"],
                    "status": item["status"],
                    "priority": item["priority"],
                    "updated_at": item["updated_at"],
                    "checked_at": data["snapshot_at"],
                }
        return {
            "tool": "check_ticket_status",
            "ticket_id": normalized_id,
            "error": "not_found",
        }
    except Exception as exc:
        return err("check_ticket_status", exc)
