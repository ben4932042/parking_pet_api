import json
import logging
import time
from typing import Optional, Set

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from interface.api.logging_utils import (
    build_input_summary,
    build_resource_from_path_params,
    resolve_request_id,
    summarize_query_string,
)


class LoggingMiddleware:
    def __init__(
        self, app: ASGIApp, *, exclude_paths: Optional[Set[str]] = None
    ) -> None:
        self.app = app
        self._logger = logging.getLogger(__name__)
        self._exclude_paths = exclude_paths or set()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Only handle HTTP
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self._exclude_paths:
            await self.app(scope, receive, send)
            return

        state = scope.setdefault("state", {})

        # 1) Read & buffer the incoming HTTP request body
        body = b""
        more_body = True
        # We also keep the original receive to pass through disconnect later
        original_receive = receive

        while more_body:
            message = await original_receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)
            else:
                # non http.request messages we just ignore here;
                # they will be available via original_receive later
                pass

        # 2) Build a new receive that replays the buffered body once
        body_sent = False

        async def replay_receive() -> Message:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False,
                }
            # after we've replayed the body, delegate to original receive
            return await original_receive()

        # 3) Log the request
        headers = {
            k.decode() if isinstance(k, bytes) else k: v.decode()
            if isinstance(v, bytes)
            else v
            for k, v in scope.get("headers", [])
        }
        # scope headers come as list[tuple[bytes, bytes]]; convert nicely
        if not headers:
            # if we built from scope manually, we might need to re-parse
            headers = {k.decode(): v.decode() for k, v in scope["headers"]}

        request_id, request_id_source = resolve_request_id(headers)
        state["request_id"] = request_id
        state["request_id_source"] = request_id_source

        body_for_log = None
        content_type = headers.get("content-type", "")
        if body:
            try:
                if "application/json" in content_type:
                    body_for_log = json.loads(body.decode("utf-8"))
                elif (
                    "application/x-www-form-urlencoded" in content_type
                    or "multipart/form-data" in content_type
                ):  # noqa: E501
                    body_for_log = body.decode("utf-8", errors="replace")
                else:
                    body_for_log = body.decode("utf-8", errors="replace")
            except Exception:
                body_for_log = body.decode("utf-8", errors="replace")
        state["input_summary"] = build_input_summary(body_for_log)
        state["query_summary"] = summarize_query_string(
            scope.get("query_string", b"").decode()
        )

        # 4) Wrap send to capture response info
        response_info = {
            "status_code": None,
            "media_type": None,
        }

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status = message["status"]
                response_info["status_code"] = status
                # headers are in message["headers"]
                # we might want to detect media_type
                resp_headers = {
                    k.decode(): v.decode() for k, v in message.get("headers", [])
                }
                response_info["media_type"] = resp_headers.get("content-type")
                await send(message)
            elif message["type"] == "http.response.body":
                await send(message)
            else:
                await send(message)

        # 5) Call downstream app with our replaying receive & wrapped send
        started_at = time.perf_counter()
        try:
            await self.app(scope, replay_receive, send_wrapper)
        except Exception:
            if response_info["status_code"] is None:
                response_info["status_code"] = 500
            raise
        finally:
            route = scope.get("route")
            route_name = getattr(route, "name", None)
            if route_name is None:
                endpoint = scope.get("endpoint")
                route_name = getattr(endpoint, "__name__", None)
            state["route_name"] = route_name
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            detail = {
                "event": "http_access",
                "request_id": request_id,
                "request_id_source": request_id_source,
                "user_id": state.get("user_id"),
                "method": scope.get("method"),
                "path": path,
                "route_name": route_name,
                "status_code": response_info["status_code"],
                "latency_ms": latency_ms,
                "query_summary": state.get("query_summary"),
                "input_summary": state.get("input_summary"),
                "resource": build_resource_from_path_params(
                    scope.get("path_params", {})
                ),
                "client": {
                    "ip": headers.get("cf-connecting-ip"),
                    "country": headers.get("cf-ipcountry"),
                    "forwarded_for": headers.get("x-forwarded-for"),
                    "scheme": headers.get("x-forwarded-proto"),
                    "user_agent": headers.get("user-agent"),
                },
            }
            self._logger.debug("HTTP access", extra=detail)
