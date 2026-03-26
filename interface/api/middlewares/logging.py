import json
import logging
from typing import Optional, Set

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class LoggingMiddleware:
    def __init__(self, app: ASGIApp, *, exclude_paths: Optional[Set[str]] = None) -> None:
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
        headers = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in scope.get("headers", [])}
        # scope headers come as list[tuple[bytes, bytes]]; convert nicely
        if not headers:
            # if we built from scope manually, we might need to re-parse
            headers = {k.decode(): v.decode() for k, v in scope["headers"]}

        body_for_log = None
        content_type = headers.get("content-type", "")
        if body:
            try:
                if "application/json" in content_type:
                    body_for_log = json.loads(body.decode("utf-8"))
                elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:  # noqa: E501
                    body_for_log = body.decode("utf-8", errors="replace")
                else:
                    body_for_log = body.decode("utf-8", errors="replace")
            except Exception:
                body_for_log = body.decode("utf-8", errors="replace")

        req_dict = {
            "request": {
                "method": scope.get("method"),
                "path": path,
                "query_params": scope.get("query_string", b"").decode(),
                "headers": headers,
                "body": body_for_log,
            }
        }
        self._logger.debug("Request access log", extra=req_dict)

        # 4) Wrap send to capture response info
        response_info = {
            "status_code": None,
            "body": None,
            "media_type": None,
        }

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status = message["status"]
                response_info["status_code"] = status
                # headers are in message["headers"]
                # we might want to detect media_type
                resp_headers = {k.decode(): v.decode() for k, v in message.get("headers", [])}
                response_info["media_type"] = resp_headers.get("content-type")
                await send(message)
            elif message["type"] == "http.response.body":
                # try to log non-streaming / small body
                body_bytes = message.get("body", b"")
                more_body = message.get("more_body", False)

                # only buffer if small and not event-stream
                if body_bytes and not more_body and response_info["media_type"] != "text/event-stream" and (response_info["body"] is None):
                    # cap size
                    # we will buffer the body but to avoid breaking streaming, we'll cap
                    if len(body_bytes) <= 10240:  # 10 KB
                        try:
                            parsed = json.loads(body_bytes.decode())
                            response_info["body"] = parsed
                        except Exception:
                            # non-json, skip actual body text to avoid noise
                            pass

                await send(message)
            else:
                await send(message)

        # 5) Call downstream app with our replaying receive & wrapped send
        await self.app(scope, replay_receive, send_wrapper)

        # 6) After response sent, log it
        res_dict = {
            "response": {
                "status_code": response_info["status_code"],
            }
        }
        if response_info["body"] is not None:
            res_dict["response"]["body"] = response_info["body"]

        self._logger.debug("Response log", extra=res_dict)
