"""Fetch Hyperliquid BTC perpetual funding rate history (1h settlements).

Public info endpoint, no auth. Unlike OKX (GET, backward pagination),
Hyperliquid uses POST with a JSON body and pages FORWARD via startTime.
Hyperliquid settles funding EVERY HOUR — 8x the frequency of OKX.
"""

import os
import time

import pandas as pd
import requests

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "funding_hyperliquid_btc.csv")
URL = "https://api.hyperliquid.xyz/info"
DEFAULT_START = "2026-03-06"  # match OKX sample start


def fetch_hyperliquid_funding(coin: str = "BTC", start_ms: int | None = None) -> pd.DataFrame:
    all_rows = []
    while True:
        payload = {"type": "fundingHistory", "coin": coin, "startTime": start_ms}
        resp = requests.post(URL, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break

        for item in data:
            all_rows.append({
                "timestamp": pd.to_datetime(int(item["time"]), unit="ms"),
                "exchange": "hyperliquid",
                "symbol": coin,
                "funding_rate": float(item["fundingRate"]),  # decimal per 1h period
            })

        last_ms = int(data[-1]["time"])
        if start_ms is not None and last_ms <= start_ms:
            break  # safety: no forward progress
        start_ms = last_ms + 1
        time.sleep(0.3)
        if len(data) < 2:  # reached the present
            break

    return pd.DataFrame(all_rows)


def main() -> None:
    start_ms = int(pd.Timestamp(DEFAULT_START).timestamp() * 1000)
    df = fetch_hyperliquid_funding(start_ms=start_ms)
    df = (df.drop_duplicates(subset=["timestamp", "exchange", "symbol"])
            .sort_values("timestamp")
            .reset_index(drop=True))
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    print(f"saved {len(df)} rows: {df['timestamp'].min()} -> {df['timestamp'].max()}")


if __name__ == "__main__":
    main()
