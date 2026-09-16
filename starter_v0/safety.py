from __future__ import annotations

import json
import re
from typing import Any

from providers.base import ToolCall


_SECRET = re.compile(r"(?i)\b(password|passwd|api[ _-]?key|secret|token)\s*[:=]")
_INTERNAL_ID = re.compile(r"(?i)\b(?:LT|EMP)-\d+\b")
_AFFIRMATIVE = re.compile(r"(?i)^\s*(?:yes|ok(?:ay)?|có|đồng ý|xác nhận)\b")
_PAYLOAD_CHANGE = re.compile(r"(?i)\b(?:thay|sửa|đổi|nhưng|low|medium|high|critical|LT-\d+)\b")


def latest_user_text(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def preflight_refusal(messages: list[dict[str, str]]) -> str | None:
    latest = latest_user_text(messages)
    if _SECRET.search(latest):
        return json.dumps({
            "intent": "refuse_sensitive_data",
            "action": "none",
            "reply": "Remove the credential or secret and submit a redacted request.",
            "evidence_ids": [],
        })
    upper = latest.upper()
    if "SYSTEM:" in upper and "DEVELOPER:" in upper:
        return json.dumps({
            "intent": "refuse_role_spoofing",
            "action": "none",
            "reply": "Role labels inside a user message cannot change my instructions.",
            "evidence_ids": [],
        })
    return None


def filter_tools(messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest = latest_user_text(messages)
    asks_ticket_status = bool(
        re.search(r"(?i)\bLAB-[A-Za-z0-9]+\b", latest)
        or (re.search(r"(?i)\b(?:ticket|phiếu)\b", latest) and re.search(r"(?i)\b(?:status|trạng thái)\b", latest))
    )
    if asks_ticket_status:
        return tools
    return [tool for tool in tools if tool.get("function", {}).get("name") != "check_ticket_status"]


def has_fresh_confirmation(messages: list[dict[str, str]]) -> bool:
    if len(messages) < 2:
        return False
    previous, latest = messages[-2], messages[-1]
    if previous.get("role") != "assistant" or latest.get("role") != "user":
        return False
    question = previous.get("content", "").lower()
    answer = latest.get("content", "")
    asked_confirmation = "?" in question and ("xác nhận" in question or "đúng không" in question or "confirm" in question)
    return bool(asked_confirmation and _AFFIRMATIVE.search(answer) and not _PAYLOAD_CHANGE.search(answer))


def enforce_tool_boundaries(messages: list[dict[str, str]], calls: list[ToolCall]) -> list[ToolCall]:
    guarded: list[ToolCall] = []
    for call in calls:
        if call.name == "lookup_user" and re.fullmatch(r"(?i)LT-\d+", str(call.args.get("employee_id", ""))):
            guarded.append(ToolCall("inspect_device", {
                "asset_id": call.args["employee_id"],
                "check": "all",
            }))
            continue
        if call.name == "create_ticket" and not has_fresh_confirmation(messages):
            priority = call.args.get("priority", "medium")
            asset_id = call.args.get("asset_id") or "none"
            summary = call.args.get("summary", "")
            guarded.append(ToolCall("clarify", {
                "question": f"Confirm ticket: summary={summary!r}, priority={priority}, asset_id={asset_id}?",
                "response_type": "yes_no",
            }))
            continue
        if call.name == "search_device_info" and any(
            _INTERNAL_ID.search(str(value)) for value in call.args.values()
        ):
            guarded.append(ToolCall("clarify", {
                "question": "Provide only the public manufacturer and model, without asset or employee IDs.",
                "response_type": "text",
            }))
            continue
        guarded.append(call)
    return guarded
