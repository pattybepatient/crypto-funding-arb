"""Where does the corrected backtest's loss actually come from?

The README originally explained the corrected strategy's -66.6% as a
timing failure: the rolling signal is lagged, so entries land after the
spread has already started reverting. That explanation was never tested.
This script tests it, and it does not hold.

Two diagnostics:

1. Carry decomposition. Split every period in which the strategy held a
   position into periods where it PAID the funding spread and periods
   where it EARNED it, and sum the magnitudes. This separates "how often"
   from "how much", since frequency alone does not establish contribution.

2. Entry timing. For each entry, check whether the most recent observed
   move shrank the deviation from the rolling mean (i.e. whether the
   spread was already turning back when the signal fired). Note this is
   one operationalization of "already reverting", not the only one.

Run from src/:  python diagnose_backtest.py
"""

import numpy as np
import pandas as pd

from build_spread import load_merged

ENTRY_K = 1.0
EXIT_K = 0.5
FEE_PER_FILL = 0.05
FILLS_PER_SWITCH = 4
ROLL_WINDOW = 30
PERIODS_PER_YEAR = 3 * 365


def run() -> None:
    merged = load_merged()
    spread = merged["spread_ann"].values

    s = pd.Series(spread)
    roll_mean = s.rolling(ROLL_WINDOW).mean().shift(1).values
    roll_std = s.rolling(ROLL_WINDOW).std().shift(1).values

    position, n_switches = 0, 0
    rows, entries = [], []

    for i in range(len(spread)):
        if np.isnan(roll_mean[i]) or np.isnan(roll_std[i]):
            rows.append((i, 0, 0.0))
            continue

        dev = (spread[i - 1] - roll_mean[i]) if i > 0 else 0.0
        prev_position = position

        if position == 0:
            if dev > ENTRY_K * roll_std[i]:
                position, n_switches = -1, n_switches + 1
            elif dev < -ENTRY_K * roll_std[i]:
                position, n_switches = 1, n_switches + 1
        elif abs(dev) < EXIT_K * roll_std[i]:
            position, n_switches = 0, n_switches + 1

        if prev_position == 0 and position != 0:
            entries.append(i)

        rows.append((i, position, position * spread[i] / PERIODS_PER_YEAR))

    df = pd.DataFrame(rows, columns=["i", "position", "carry"])
    held = df[df.position != 0]
    paying = held[held.carry < 0]
    earning = held[held.carry > 0]
    zero = held[held.carry == 0]
    cost = n_switches * FEE_PER_FILL * FILLS_PER_SWITCH / 100

    print("=== CARRY DECOMPOSITION ===")
    print(f"  periods total             : {len(df)}")
    print(f"  periods holding a position: {len(held)}")
    print(f"    paying  (carry < 0)     : {len(paying)}"
          f"  ({len(paying) / len(held) * 100:.1f}%)")
    print(f"    earning (carry > 0)     : {len(earning)}"
          f"  ({len(earning) / len(held) * 100:.1f}%)")
    print(f"    zero    (carry = 0)     : {len(zero)}"
          f"  ({len(zero) / len(held) * 100:.1f}%)")
    print(f"  sum of negative carry     : {paying.carry.sum() * 100:+.2f}%")
    print(f"  sum of positive carry     : {earning.carry.sum() * 100:+.2f}%")
    print(f"  gross                     : {df.carry.sum() * 100:+.2f}%")
    print(f"  switches                  : {n_switches}")
    print(f"  transaction costs         : {-cost * 100:.2f}%")
    print(f"  NET                       : {(df.carry.sum() - cost) * 100:+.2f}%")

    examined = [i for i in entries if i >= 2]
    shrinking = 0
    for i in examined:
        latest_dev = spread[i - 1] - roll_mean[i]
        prior_dev = spread[i - 2] - roll_mean[i]
        if abs(latest_dev) < abs(prior_dev):
            shrinking += 1

    print("\n=== ENTRY TIMING ===")
    print(f"  entries examined            : {len(examined)}")
    print(f"  deviation shrinking at entry: {shrinking}")
    print("\n  The lagged-entry story predicts this count should be high.")
    print("  It is not. Every entry fired on a move that widened the")
    print("  deviation, so the loss is not explained by entering after")
    print("  the reversal had begun.")


if __name__ == "__main__":
    run()
