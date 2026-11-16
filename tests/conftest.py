"""Every test runs isolated from the local .env credentials and from the real network."""

import httpx
import pytest


@pytest.fixture(autouse=True)
def _isolate_from_local_environment_and_network(monkeypatch, tmp_path):
    for variable in ("DHAN_CLIENT_ID", "DHAN_ACCESS_TOKEN", "SCANNER_FIXTURE_DIR", "SCANNER_UI_DIR", "STOP_LOSS_ENABLED"):
        monkeypatch.setenv(variable, "")  # environment beats .env; blank means unset (stop loss: disabled)
    monkeypatch.setenv("SCANNER_DATA_DIR", str(tmp_path / "data"))

    def blocked(self, request):
        # Behaves like an offline machine, so provider code takes its real failure path.
        raise httpx.ConnectError(f"Real network access is disabled in tests: {request.url}", request=request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
