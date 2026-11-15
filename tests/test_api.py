import pytest
from fastapi.testclient import TestClient

from helpers import make_service
from trading_scanner.api import create_app
from trading_scanner.service import ScanService


@pytest.fixture
def client():
    return TestClient(create_app(make_service()))


def test_health_makes_no_provider_request():
    def explode(name):
        raise AssertionError("health must not touch a provider")

    client = TestClient(create_app(ScanService(provider_factory=explode)))
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok" and body["strategy_version"] == "0.2.0" and body["providers"] == ["fixture", "dhan"]


def test_scan_returns_decimal_strings_nulls_and_kolkata_times(client):
    response = client.post("/v1/scans", json={"trading_date": "2026-11-13", "stocks": ["SYN-LONG"], "provider": "fixture"})
    assert response.status_code == 200
    body = response.json()
    result = body["results"][0]
    assert result["state"] == "entry_identified" and result["setup_qualified"] is True
    assert result["entry"]["price"] == "111.20" and result["entry"]["time"] == "2026-11-13T11:20:00+05:30"
    assert result["breakout"]["confirmed_at"] == "2026-11-13T11:20:00+05:30"
    assert result["reference"]["high"] == "110.00" and result["reference"]["low"] == "100.00"
    assert result["qualification"]["high_side"]["status"] == "new_extreme"
    assert result["risk"] == {"stop_loss": None, "targets": None, "exit_time": None, "exit_price": None,
                              "outcome": None, "profit_loss": None, "reason": "Rules not yet defined"}
    assert body["synthetic_data_present"] is True and result["data"]["synthetic"] is True


def test_mixed_batch_returns_200_with_per_stock_states(client):
    response = client.post(
        "/v1/scans", json={"trading_date": "2026-11-13", "stocks": ["SYN-LONG", "SYN-NOTQUAL", "NOPE", "HCLTECH"], "provider": "fixture"}
    )
    assert response.status_code == 200
    assert [r["state"] for r in response.json()["results"]] == ["entry_identified", "not_qualified", "symbol_error", "invalid_data"]


def test_dhan_request_is_valid_but_reports_provider_errors(client):
    response = client.post("/v1/scans", json={"trading_date": "2026-11-13", "stocks": ["HCLTECH"], "provider": "dhan"})
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["state"] == "provider_error" and result["data"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"trading_date": "2026-11-13", "stocks": [], "provider": "fixture"},
        {"trading_date": "2026-11-13", "stocks": ["  "], "provider": "fixture"},
        {"trading_date": "2026-11-13", "stocks": ["SYN-LONG"]},
        {"trading_date": "2026-11-13", "stocks": ["SYN-LONG"], "provider": "csv"},
        {"trading_date": "13/11/2026", "stocks": ["SYN-LONG"], "provider": "fixture"},
        {"trading_date": "2026-11-13", "stocks": "SYN-LONG", "provider": "fixture"},
        {"trading_date": "2026-11-13", "stocks": ["A"] * 101, "provider": "fixture"},
        {"date": "2026-11-13", "stocks": ["SYN-LONG"], "provider": "fixture"},
    ],
)
def test_malformed_requests_return_422(client, payload):
    assert client.post("/v1/scans", json=payload).status_code == 422


def test_future_date_returns_422_with_field_detail(client):
    response = client.post("/v1/scans", json={"trading_date": "2026-11-16", "stocks": ["SYN-LONG"], "provider": "fixture"})
    assert response.status_code == 422
    detail = response.json()["detail"][0]
    assert detail["loc"] == ["body", "trading_date"] and "in the future" in detail["msg"]


def test_ui_is_served_at_root_when_built_and_api_routes_still_win(tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><div id='root'></div>")
    client = TestClient(create_app(make_service(), ui_dir=tmp_path))
    assert "id='root'" in client.get("/").text
    assert client.get("/health").json()["status"] == "ok"
    response = client.post("/v1/scans", json={"trading_date": "2026-11-13", "stocks": ["SYN-LONG"], "provider": "fixture"})
    assert response.status_code == 200 and response.json()["results"][0]["state"] == "entry_identified"


def test_root_explains_how_to_build_when_ui_is_missing(tmp_path):
    client = TestClient(create_app(make_service(), ui_dir=tmp_path / "missing"))
    response = client.get("/")
    assert response.status_code == 200 and "pnpm build" in response.text


def test_health_reports_dhan_configuration_without_secrets(client):
    body = client.get("/health").json()
    assert body["dhan_configured"] is False  # tests run with credentials cleared


def test_instrument_search_returns_labeled_suggestions(client):
    response = client.get("/v1/instruments", params={"provider": "fixture", "query": "syn-lo"})
    assert response.status_code == 200
    (item,) = response.json()["results"]
    assert item["symbol"] == "SYN-LONG" and item["kind"] == "stock" and item["scannable"] is True and item["synthetic"] is True
    taught = client.get("/v1/instruments", params={"provider": "fixture", "query": "larsen"}).json()["results"]
    assert taught[0]["symbol"] == "LT" and taught[0]["synthetic"] is False


def test_instrument_search_validates_input_and_reports_provider_failure(client):
    assert client.get("/v1/instruments", params={"query": "hcl"}).status_code == 422  # provider is required
    assert client.get("/v1/instruments", params={"provider": "fixture", "query": ""}).status_code == 422
    failed = client.get("/v1/instruments", params={"provider": "dhan", "query": "hcl"})  # network blocked in tests
    assert failed.status_code == 503 and "instrument list" in failed.json()["detail"]


def test_scan_results_include_session_candles_for_charts(client):
    body = client.post("/v1/scans", json={"trading_date": "2026-11-13", "stocks": ["SYN-LONG", "NOPE"], "provider": "fixture"}).json()
    long_, unknown = body["results"]
    assert len(long_["candles"]) == 75 and long_["candles"][0]["start"] == "2026-11-13T09:15:00+05:30"
    assert long_["candles"][0]["open"] == "104.00" and unknown["candles"] == []
