import pytest
from fastapi.testclient import TestClient

from helpers import ALL_WINDOWS, WINDOW_0945, in_window, make_service
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
    (result,) = in_window(body["results"])  # the original 10:30 window
    assert result["state"] == "entry_identified" and result["setup_qualified"] is True
    assert result["entry"]["price"] == "111.20" and result["entry"]["time"] == "2026-11-13T11:20:00+05:30"
    assert result["breakout"]["confirmed_at"] == "2026-11-13T11:20:00+05:30"
    assert result["reference"]["high"] == "110.00" and result["reference"]["low"] == "100.00"
    assert result["qualification"]["low_side"]["status"] == "new_extreme"
    assert result["qualification"]["permitted_signal"] == "long"
    assert result["breakout"]["direction_permitted"] is True
    assert result["risk"] == {"stop_loss": None, "stop_loss_basis": None, "targets": None, "exit_time": None,
                              "exit_price": None, "outcome": None, "profit_loss": None, "reason": "Rules not yet defined"}
    assert body["synthetic_data_present"] is True and result["data"]["synthetic"] is True


def test_mixed_batch_returns_200_with_per_stock_states(client):
    response = client.post(
        "/v1/scans", json={"trading_date": "2026-11-13", "stocks": ["SYN-LONG", "SYN-NOTQUAL", "NOPE", "HCLTECH"], "provider": "fixture"}
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 12  # four stocks x three windows
    assert [r["state"] for r in in_window(results)] == ["entry_identified", "not_qualified", "symbol_error", "invalid_data"]


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
    long_, unknown = in_window(body["results"])
    assert len(long_["candles"]) == 75 and long_["candles"][0]["start"] == "2026-11-13T09:15:00+05:30"
    assert long_["candles"][0]["open"] == "104.00" and unknown["candles"] == []


def test_every_scan_reports_all_windows(client):
    body = client.post("/v1/scans", json={"trading_date": "2026-11-13", "stocks": ["SYN-0945-LONG"], "provider": "fixture"}).json()
    assert body["windows"] == [
        {"key": "0945_three_candle", "label": "09:45 three-candle", "reference_candles": ["09:45", "09:50", "09:55"],
         "earlier_window": "09:15-09:40", "qualification_window": "09:15-09:55", "range_final_at": "10:00"},
        {"key": "1030_four_candle", "label": "10:30 four-candle", "reference_candles": ["10:30", "10:35", "10:40", "10:45"],
         "earlier_window": "09:15-10:25", "qualification_window": "09:15-10:45", "range_final_at": "10:50"},
        {"key": "1050_two_candle", "label": "10:50 two-candle", "reference_candles": ["10:50", "10:55"],
         "earlier_window": "09:15-10:45", "qualification_window": "09:15-10:55", "range_final_at": "11:00"},
    ]
    assert [r["strategy_window"] for r in body["results"]] == ALL_WINDOWS
    (three,) = in_window(body["results"], WINDOW_0945)
    assert three["state"] == "entry_identified" and three["entry"]["time"] == "2026-11-13T10:10:00+05:30"
    old_option = client.post("/v1/scans", json={"trading_date": "2026-11-13", "stocks": ["SYN-LONG"], "provider": "fixture",
                                                "strategy_window": WINDOW_0945})
    assert old_option.status_code == 422  # there is no window option any more
