"""April 2026 stress window analysis: divergence, not co-crash.

Zooms into Apr 8-20, annotates the spread extreme (Apr 11: OKX -17% while
HL +11%), and compares cross-venue correlation inside vs outside the window.
Finding: extremes arrive STAGGERED (3-6 days apart), correlation stays flat
(~0.35) — stress is desynchronized rather than synchronized, which is what
throws the spread to its extremes.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

from build_spread import load_merged, BASE

WINDOW_START, WINDOW_END = "2026-04-08", "2026-04-20"


def main() -> None:
    merged = load_merged()
    window = merged[(merged["timestamp"] >= WINDOW_START) &
                    (merged["timestamp"] <= WINDOW_END)].copy()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle("Divergence, Not Co-Crash: OKX vs Hyperliquid During the April Stress Window",
                 fontsize=13)

    ax1.plot(window["timestamp"], window["okx_ann"], label="OKX",
             color="#2e86de", linewidth=2, marker="o", markersize=4)
    ax1.plot(window["timestamp"], window["hl_ann"], label="Hyperliquid",
             color="#a29bfe", linewidth=2, marker="s", markersize=4)
    ax1.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax1.fill_between(window["timestamp"], window["okx_ann"], window["hl_ann"],
                     where=(window["okx_ann"] < window["hl_ann"]),
                     alpha=0.15, color="#e74c3c", label="divergence gap")
    ax1.set_ylabel("Funding Rate (annualized %)")
    ax1.legend(loc="lower left")
    ax1.grid(alpha=0.3)

    peak = window.loc[window["spread_ann"].idxmin()]
    ax1.annotate(
        f"{peak['timestamp']:%b %d %H:%M}\nOKX: {peak['okx_ann']:.1f}%  HL: +{peak['hl_ann']:.1f}%",
        xy=(peak["timestamp"], peak["okx_ann"]),
        xytext=(peak["timestamp"] + pd.Timedelta(days=2), peak["okx_ann"] - 3),
        arrowprops=dict(arrowstyle="->", color="black"), fontsize=9)

    colors = ["#2ecc71" if x >= 0 else "#e74c3c" for x in window["spread_ann"]]
    ax2.bar(window["timestamp"], window["spread_ann"], color=colors,
            width=0.25, alpha=0.8)
    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax2.set_ylabel("Spread: OKX − HL (ann. %)")
    ax2.set_xlabel("Date")
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    out = os.path.join(BASE, "figures", "april_stress_divergence.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"saved {out}\n")

    print("stress window stats:")
    print(f"  OKX min:    {window['okx_ann'].min():.2f}%")
    print(f"  HL min:     {window['hl_ann'].min():.2f}%")
    print(f"  spread min: {window['spread_ann'].min():.2f}%")
    print(f"  OKX-HL correlation in window:   {window['okx_ann'].corr(window['hl_ann']):.3f}")
    print(f"  OKX-HL correlation full period: {merged['okx_ann'].corr(merged['hl_ann']):.3f}")


if __name__ == "__main__":
    main()
