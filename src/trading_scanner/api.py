"""FastAPI interface (SPEC.md section 7, D12). A thin interface over ``ScanService``.

Run: python -m uvicorn trading_scanner.api:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from trading_scanner import STRATEGY_VERSION
from trading_scanner.config import Settings
from trading_scanner.models import InstrumentSearchResponse, ProviderName, ScanRequest, ScanResponse
from trading_scanner.providers import PROVIDER_NAMES, ProviderError
from trading_scanner.service import InputError, ScanService


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    strategy_version: str
    providers: list[str]
    dhan_configured: bool
    time: datetime


UI_NOT_BUILT = """<!doctype html><title>Four Candle Scanner</title>
<p>The web UI has not been built yet. Run <code>pnpm dev</code> from the project root and open
http://localhost:5173, or run <code>pnpm build</code> and restart this server. The API is available at <a href="/docs">/docs</a>.</p>"""


def create_app(service: ScanService | None = None, ui_dir: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="Four Candle Reversal Scanner",
        version=STRATEGY_VERSION,
        description=(
            "Setup and entry signals for the four candle reversal strategy (SPEC.md 0.2.0). "
            "Reports reference prices only; places no orders. Stop loss, targets, and exits are null "
            "until their rules are defined."
        ),
    )
    app.state.service = service or ScanService()
    app.state.settings = Settings()

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        """Process status. Makes no provider request."""
        svc: ScanService = request.app.state.service
        return HealthResponse(
            status="ok",
            service="four-candle-reversal-scanner",
            strategy_version=STRATEGY_VERSION,
            providers=list(PROVIDER_NAMES),
            dhan_configured=request.app.state.settings.dhan_configured,
            time=svc.now(),
        )

    @app.get("/v1/instruments", response_model=InstrumentSearchResponse)
    def search_instruments(
        request: Request,
        provider: ProviderName,
        query: str = Query(min_length=1, max_length=64),
        limit: int = Query(12, ge=1, le=50),
    ) -> InstrumentSearchResponse:
        """Stock picker suggestions labeled stock, future, or index. Only stocks are scannable."""
        svc: ScanService = request.app.state.service
        try:
            return svc.search_instruments(provider, query, limit)
        except ProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/v1/scans", response_model=ScanResponse)
    def create_scan(body: ScanRequest, request: Request) -> ScanResponse:
        """Scan every distinct stock; per-stock problems are reported as result states."""
        svc: ScanService = request.app.state.service
        try:
            return svc.scan(body)
        except InputError as exc:
            raise HTTPException(
                status_code=422,
                detail=[{"type": "value_error", "loc": ["body", exc.field_name], "msg": exc.message}],
            ) from exc

    # The bare-minimum React UI (frontend/dist), mounted last so API routes take precedence.
    ui = ui_dir if ui_dir is not None else app.state.settings.resolved_ui_dir
    if (ui / "index.html").is_file():
        app.mount("/", StaticFiles(directory=ui, html=True), name="ui")
    else:

        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        def ui_not_built() -> str:
            return UI_NOT_BUILT

    return app


app = create_app()
