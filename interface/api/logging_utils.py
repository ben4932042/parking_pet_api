import logging
import uuid
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qs

from fastapi import Request

event_logger = logging.getLogger("interface.api.events")


def resolve_request_id(headers: Mapping[str, str]) -> tuple[str, str]:
    cloudflare_request_id = headers.get("cf-ray")
    if cloudflare_request_id:
        return cloudflare_request_id, "cf-ray"
    return f"req_{uuid.uuid4().hex[:8]}", "generated"


def summarize_query_string(query_string: str) -> dict[str, Any]:
    if not query_string:
        return {}
    parsed = parse_qs(query_string, keep_blank_values=False)
    return {
        key: values[0] if len(values) == 1 else values for key, values in parsed.items()
    }


def build_input_summary(payload: Any) -> dict[str, Any] | None:
    if payload is None:
        return None
    if isinstance(payload, dict):
        summary: dict[str, Any] = {"body_keys": sorted(payload.keys())}
        content = payload.get("content")
        if isinstance(content, str):
            summary["content_length"] = len(content)
        return summary
    if isinstance(payload, list):
        return {"item_count": len(payload)}
    if isinstance(payload, str):
        return {"content_length": len(payload)}
    return None


def build_resource_from_path_params(
    path_params: Mapping[str, Any],
) -> dict[str, str] | None:
    if "property_id" in path_params:
        return {"type": "property", "id": str(path_params["property_id"])}
    if "user_id" in path_params:
        return {"type": "user", "id": str(path_params["user_id"])}
    return None


def optional_user_id(current_user: Any) -> str | None:
    if current_user is None:
        return None
    user_id = getattr(current_user, "id", None)
    if user_id is None:
        return None
    return str(user_id)


def _compact(detail: Mapping[str, Any]) -> dict[str, Any]:
    compacted: dict[str, Any] = {}
    for key, value in detail.items():
        if value is None:
            continue
        if isinstance(value, dict):
            nested = _compact(value)
            if nested:
                compacted[key] = nested
            continue
        compacted[key] = value
    return compacted


def log_api_event(
    event: str,
    request: Request | None = None,
    level: int = logging.INFO,
    message: str | None = None,
    user_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {"event": event}
    if request is not None:
        request_id = getattr(request.state, "request_id", None)
        request_id_source = getattr(request.state, "request_id_source", None)
        route_name = getattr(request.state, "route_name", None)
        if request_id:
            payload["request_id"] = request_id
        if request_id_source:
            payload["request_id_source"] = request_id_source
        if route_name:
            payload["route_name"] = route_name
    resolved_user_id = user_id
    if resolved_user_id is None and request is not None:
        resolved_user_id = getattr(request.state, "user_id", None)
    if resolved_user_id is not None:
        payload["user_id"] = str(resolved_user_id)
    if extra:
        payload.update(_compact(extra))
    event_logger.log(level, message or event, extra=payload)
