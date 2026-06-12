"""Build the cross-exchange funding spread series.

Key alignment step: Hyperliquid settles hourly, OKX every 8 hours.
HL rates are SUMMED into 8h buckets floored to OKX settlement times
(00:00 / 08:00 / 16:00 UTC) so the two series are directly comparable.
After aggregation both are per-8h-period rates, annualized as x3x365.

Also produces the two overview figures and prints spread statistics.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..")
ANN = 3 * 365 * 100  # 8h period -> annualized %


def load_merged() -> pd.DataFrame:
    """Load both venues, align frequencies, return merged spread dataframe."""
    okx = pd.read_csv(os.path.join(BASE, "data", "funding_okx_btc.csv"),
                      parse_dates=["timestamp"])
    okx["okx_ann"] = okx["funding_rate"] * ANN

    hl = pd.read_csv(os.path.join(BASE, "data", "funding_hyperliquid_btc.csv"),
                     parse_dates=["timestamp"])
    hl["bucket"] = hl["timestamp"].dt.floor("8h")
    hl_8h = hl.groupby("bucket")["funding_rate"].sum().reset_index()
    hl_8h.columns = ["timestamp", "hl_rate"]
    hl_8h["hl_ann"] = hl_8h["hl_rate"] * ANN

    merged = pd.merge(okx[["timestamp", "okx_ann"]],
                      hl_8h[["timestamp", "hl_ann"]],
                      on="timestamp", how="inner")
    merged["spread_ann"] = merged["okx_ann"] - merged["hl_ann"]
    return merged.sort_values("timestamp").reset_index(drop=True)


def main() -> None:
    merged = load_merged()
    print(f"matched periods: {len(merged)}")
    print(f"range: {merged['timestamp'].min()} -> {merged['timestamp'].max()}")
    print("\nspread stats (annualized %, OKX minus Hyperliquid):")
    print(merged["spread_ann"].describe().round(2))

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle("Cross-Exchange Funding: OKX vs Hyperliquid (BTC)", fontsize=14)

    axes[0].plot(merged["timestamp"], merged["okx_ann"], label="OKX",
                 color="#2e86de", linewidth=1.2)
    axes[0].plot(merged["timestamp"], merged["hl_ann"], label="Hyperliquid",
                 color="#a29bfe", linewidth=1.2)
    axes[0].axhline(0, color="black", linewidth=0.8, linestyle="--")
    axes[0].set_ylabel("Funding Rate (annualized %)")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    colors = ["#2ecc71" if x >= 0 else "#e74c3c" for x in merged["spread_ann"]]
    axes[1].bar(merged["timestamp"], merged["spread_ann"], color=colors,
                width=0.15, alpha=0.7)
    axes[1].axhline(0, color="black", linewidth=0.8, linestyle="--")
    axes[1].set_ylabel("Spread: OKX − HL (ann. %)")
    axes[1].set_xlabel("Date")
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    out = os.path.join(BASE, "figures", "cross_exchange_spread.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
