"""Mean-reversion switching strategy on the cross-exchange funding spread.

Contains BOTH versions deliberately:

- backtest_naive():   the flawed first attempt (+328% over 3 months).
                      Kept as a teaching artifact: it commits look-ahead
                      bias (full-sample mean/std as thresholds) and uses
                      the WRONG PnL definition (spread *changes* instead
                      of realized carry).

- backtest_corrected(): rolling stats from past data only, real per-period
                      carry cash flows, retail taker fees. Result on this
                      sample: -66.6% net over 3 months.

The gap between the two numbers (+328% vs -66.6%) is the project's
central lesson: a statistically real pattern (mean reversion, see
analysis_meanreversion.py) is not the same thing as an executable edge.
The rolling signal is inherently lagged; because reversion is slow,
entries are systematically late and the position bleeds negative carry
and fees waiting for a reversion that no longer pays for the trip.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from build_spread import load_merged, BASE

ENTRY_K = 1.0          # enter when |deviation| > ENTRY_K * std
EXIT_K = 0.5           # exit when |deviation| < EXIT_K * std
FEE_PER_FILL = 0.05    # % taker fee per fill
FILLS_PER_SWITCH = 4   # open or close = 2 venues x (1 fill each) x 2 legs
ROLL_WINDOW = 30       # ~10 days of 8h periods, used by corrected version
PERIODS_PER_YEAR = 3 * 365


def backtest_naive(spread: np.ndarray) -> dict:
    """FLAWED: full-sample stats (look-ahead) + spread-change PnL (wrong)."""
    mean, std = spread.mean(), spread.std()
    position, n_switches, pnl = 0, 0, []

    for i in range(1, len(spread)):
        dev = spread[i - 1] - mean
        if position == 0:
            if dev > ENTRY_K * std:
                position, n_switches = -1, n_switches + 1
            elif dev < -ENTRY_K * std:
                position, n_switches = 1, n_switches + 1
        elif abs(dev) < EXIT_K * std:
            position, n_switches = 0, n_switches + 1
        pnl.append(position * (spread[i] - spread[i - 1]))  # <-- wrong PnL

    gross = float(np.sum(pnl))
    cost = n_switches * FEE_PER_FILL * FILLS_PER_SWITCH
    return {"gross": gross, "cost": cost, "net": gross - cost,
            "switches": n_switches}


def backtest_corrected(spread: np.ndarray) -> dict:
    """Honest version: rolling past-only stats + realized carry PnL + fees."""
    s = pd.Series(spread)
    roll_mean = s.rolling(ROLL_WINDOW).mean().shift(1).values  # past only
    roll_std = s.rolling(ROLL_WINDOW).std().shift(1).values

    position, n_switches, in_pos = 0, 0, 0
    pnl = []

    for i in range(len(spread)):
        if np.isnan(roll_mean[i]) or np.isnan(roll_std[i]):
            pnl.append(0.0)
            continue

        dev = (spread[i - 1] - roll_mean[i]) if i > 0 else 0.0
        if position == 0:
            if dev > ENTRY_K * roll_std[i]:
                position, n_switches = -1, n_switches + 1
            elif dev < -ENTRY_K * roll_std[i]:
                position, n_switches = 1, n_switches + 1
        elif abs(dev) < EXIT_K * roll_std[i]:
            position, n_switches = 0, n_switches + 1

        # realized carry this period, de-annualized to one 8h period
        pnl.append(position * spread[i] / PERIODS_PER_YEAR)
        if position != 0:
            in_pos += 1

    pnl = np.array(pnl)
    gross_cum = np.cumsum(pnl)
    cost_total = n_switches * FEE_PER_FILL * FILLS_PER_SWITCH / 100
    return {"gross_cum": gross_cum, "cost": cost_total,
            "net": float(gross_cum[-1] - cost_total),
            "switches": n_switches, "time_in_pos": in_pos / len(spread)}


def main() -> None:
    merged = load_merged()
    spread = merged["spread_ann"].values

    naive = backtest_naive(spread)
    print("NAIVE (flawed — look-ahead + wrong PnL):")
    print(f"  net 'pnl': +{naive['net']:.1f} pts over {naive['switches']} switches")
    print("  -> a near-perfect equity curve is a bug report, not a discovery\n")

    res = backtest_corrected(spread)
    print(f"CORRECTED (rolling stats, realized carry, {FEE_PER_FILL}%/fill):")
    print(f"  switches: {res['switches']}, time in position: {res['time_in_pos']*100:.1f}%")
    print(f"  gross: {res['gross_cum'][-1]*100:.2f}% | cost: {res['cost']*100:.2f}%"
          f" | NET: {res['net']*100:.2f}% over ~3 months")

    net_cum = res["gross_cum"] - np.linspace(0, res["cost"], len(res["gross_cum"]))
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(merged["timestamp"], res["gross_cum"] * 100, color="#95a5a6",
            linewidth=1.5, label="gross (before costs)")
    ax.plot(merged["timestamp"], net_cum * 100, color="#e74c3c",
            linewidth=2, label="net (after costs)")
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_title("Mean-Reversion Strategy — Corrected (rolling stats, real carry PnL)\n"
                 f"NET return over 3 months: {res['net']*100:.2f}%")
    ax.set_ylabel("Cumulative return (%)")
    ax.set_xlabel("Date")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(BASE, "figures", "backtest_corrected.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
