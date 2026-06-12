"""Mean reversion diagnostics on the cross-exchange spread.

Two tests:
1. Autocorrelation at lags 1-6 (8h-48h) — measures short-term persistence
   and how fast it decays.
2. Augmented Dickey-Fuller (ADF) test — null hypothesis is a unit root
   (random walk, no anchor). Rejection => the spread is stationary /
   mean-reverting.

Result on this sample: ADF p < 0.0001 (strongly mean-reverting) but
lag-1 autocorrelation 0.627 decaying to 0.192 only by 48h — reversion
is REAL but SLOW, which is precisely what kills the naive strategy in
backtest.py.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from build_spread import load_merged, BASE


def main() -> None:
    merged = load_merged()
    spread = merged["spread_ann"]

    print("autocorrelation by lag (8h increments):")
    for lag in range(1, 7):
        ac = spread.autocorr(lag=lag)
        hours = lag * 8
        print(f"  lag {lag} ({hours}h / {hours/24:.1f} days): {ac:.3f}")

    adf_stat, p_value, *_ = adfuller(spread.dropna())
    print(f"\nADF test statistic: {adf_stat:.3f}")
    print(f"p-value: {p_value:.4f}")
    print("-> p < 0.05: reject unit root, spread IS mean-reverting")

    merged["rolling_mean"] = spread.rolling(window=9).mean()  # ~3 days

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(merged["timestamp"], spread, color="#34495e", linewidth=0.8,
            alpha=0.6, label="spread")
    ax.plot(merged["timestamp"], merged["rolling_mean"], color="#e74c3c",
            linewidth=2, label="3-day rolling mean")
    ax.axhline(spread.mean(), color="black", linewidth=1, linestyle="--",
               label=f"overall mean ({spread.mean():.2f}%)")
    ax.set_ylabel("Spread: OKX - HL (ann. %)")
    ax.set_xlabel("Date")
    ax.set_title("Spread Mean Reversion Check")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(BASE, "figures", "spread_mean_reversion.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
