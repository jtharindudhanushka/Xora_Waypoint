"""RFC 7807 problem+json errors. Domain errors carry a code and, when relevant, a business-rule id."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"


class DomainError(Exception):
    """Raised by services when a business rule or precondition fails."""

    status_code = 422
    title = "Rule violated"

    def __init__(self, code: str, detail: str, *, rule_id: str | None = None, **extra: Any) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.rule_id = rule_id
        self.extra = extra


class NotFoundError(DomainError):
    status_code = 404
    title = "Not found"


class ForbiddenError(DomainError):
    status_code = 403
    title = "Forbidden"


class ConflictError(DomainError):
    status_code = 409
    title = "Conflict"


def _problem(status: int, title: str, detail: str, **fields: Any) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    body.update({k: v for k, v in fields.items() if v is not None})
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            exc.status_code, exc.title, exc.detail, code=exc.code, rule_id=exc.rule_id, **exc.extra
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem(exc.status_code, str(exc.detail), str(exc.detail), code="HTTP_ERROR")

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            422, "Invalid request", "Request validation failed", code="VALIDATION", errors=exc.errors()
        )
