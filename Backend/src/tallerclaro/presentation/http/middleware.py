"""Middlewares ASGI de transporte (límite de cuerpo de petición)."""

from __future__ import annotations

import json

from starlette.datastructures import Headers

PAYLOAD_TOO_LARGE_CODE = "PAYLOAD_TOO_LARGE"


class _PayloadTooLarge(Exception):
    """Se lanza cuando el cuerpo supera el límite antes de terminar de leerse."""


class RequestBodyLimitMiddleware:
    """Rechaza cuerpos mayores que ``max_body_bytes`` con HTTP 413.

    Comprueba ``Content-Length`` antes de entrar en la aplicación y, para
    peticiones sin longitud declarada o con ``chunked``, cuenta los bytes
    recibidos mientras el endpoint lee el cuerpo. El límite se aplica antes de
    validar o deserializar el JSON.
    """

    def __init__(self, app, max_body_bytes: int) -> None:
        if max_body_bytes < 1:
            raise ValueError("max_body_bytes must be positive")
        self.app = app
        self.max_body_bytes = int(max_body_bytes)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_body_bytes:
                    await self._send_413(scope, receive, send)
                    return
            except ValueError:
                await self._send_413(scope, receive, send)
                return

        received = 0
        response_started = False

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise _PayloadTooLarge
            return message

        async def tracking_send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _PayloadTooLarge:
            if not response_started:
                await self._send_413(scope, receive, send)

    async def _send_413(self, scope, receive, send) -> None:
        body = json.dumps(
            {
                "code": PAYLOAD_TOO_LARGE_CODE,
                "message": "Request body exceeds the configured limit",
            }
        ).encode("utf-8")
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": headers,
            }
        )
        await send({"type": "http.response.body", "body": body})
