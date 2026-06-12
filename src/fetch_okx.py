"""Fetch OKX BTC perpetual funding rate history (8h settlements).

Public endpoint, no auth required. OKX returns max 100 records per call;
the `after` parameter pages BACKWARD in time (returns records older than
the given ms timestamp). Public history depth is ~3 months.

Run again later to incrementally extend: existing rows are deduplicated.
"""

import os
import time

import pandas as pd
import requests

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "funding_okx_btc.csv")
URL = "https://www.okx.com/api/v5/public/funding-rate-history"


def fetch_okx_funding(symbol: str = "BTC-USD-SWAP", after_ms: int | None = None,
                      cutoff: pd.Timestamp | None = None) -> pd.DataFrame:
    """Page backward from `after_ms` until API is exhausted or `cutoff` reached."""
    all_rows = []
    while True:
        params = {"instId": symbol, "limit": 100}
        if after_ms:
            params["after"] = str(after_ms)  # 'after' = records OLDER than this ts

        resp = requests.get(URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            print("stopped: no more data from API")
            break

        for item in data:
            ts = pd.to_datetime(int(item["fundingTime"]), unit="ms")
            if cutoff is not None and ts < cutoff:
                return pd.DataFrame(all_rows)
            all_rows.append({
                "timestamp": ts,
                "exchange": "okx",
                "symbol": "BTC",
                "funding_rate": float(item["realizedRate"]),  # decimal per 8h period
            })

        after_ms = int(data[-1]["fundingTime"])  # oldest record -> next cursor
        time.sleep(0.3)

    return pd.DataFrame(all_rows)


def main() -> None:
    if os.path.exists(DATA_PATH):
        existing = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
        earliest_ms = int(existing["timestamp"].min().timestamp() * 1000)
        print(f"existing: {len(existing)} rows, fetching older than {existing['timestamp'].min()}")
        new = fetch_okx_funding(after_ms=earliest_ms)
        combined = pd.concat([existing, new], ignore_index=True)
    else:
        print("no existing file, fetching from most recent backward")
        combined = fetch_okx_funding()

    combined = (combined
                .drop_duplicates(subset=["timestamp", "exchange", "symbol"])
                .sort_values("timestamp")
                .reset_index(drop=True))
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    combined.to_csv(DATA_PATH, index=False)
    print(f"saved {len(combined)} rows: {combined['timestamp'].min()} -> {combined['timestamp'].max()}")


if __name__ == "__main__":
    main()
