"""Quick sanity-check plots proving each compound incident archetype is
genuinely invisible to single-channel thresholds: every raw sensor stays
under its alarm line, while the (illustrative) compound risk index clearly
spikes during the incident window.

Usage:
    python engine/preview.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from simulator import CHANNEL_SPECS, generate_scenario, preview_compound_risk_index

OUT_DIR = Path(__file__).resolve().parent / "_preview"

EVENT_COLOR = "#e74c3c"
NORMAL_BAND_COLOR = "#2ecc71"
ALARM_COLOR = "#c0392b"
RISK_COLOR = "#8e44ad"
LINE_COLOR = "#2c3e50"


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ts"] = pd.to_datetime(df["timestamp"])
    return df


def _shade_event(ax, df, event, label="Incident window"):
    start = df["ts"].iloc[event["start_idx"]]
    end = df["ts"].iloc[event["end_idx"]]
    ax.axvspan(start, end, color=EVENT_COLOR, alpha=0.12, label=label)


def _plot_channel(ax, df, channel, label):
    spec = CHANNEL_SPECS[channel]
    ax.plot(df["ts"], df[channel], color=LINE_COLOR, linewidth=1.1, label=label)
    ax.axhspan(spec["normal_band"][0], spec["normal_band"][1], color=NORMAL_BAND_COLOR, alpha=0.08)
    ax.axhline(
        spec["alarm_high"], color=ALARM_COLOR, linestyle="--", linewidth=1.3,
        label=f"Single-channel alarm ({spec['alarm_high']:.1f} {spec['unit']})",
    )
    ax.set_ylabel(f"{label}\n({spec['unit']})")
    ax.margins(x=0)


def _format_xaxis(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))


def _legend(ax, *extra_handles_labels):
    handles, labels = ax.get_legend_handles_labels()
    for h, l in extra_handles_labels:
        handles += h
        labels += l
    ax.legend(handles, labels, loc="upper left", fontsize=8, framealpha=0.9)


def _plot_risk_panel(ax, df, event, risk):
    ax.plot(df["ts"], risk, color=RISK_COLOR, linewidth=1.4, label="Compound risk index (preview only)")
    ax.set_ylabel("Compound risk index\n(illustrative, S1 preview)")
    ax.margins(x=0)
    _shade_event(ax, df, event)
    _legend(ax)


def plot_gas_leak(df, event, risk, out_path: Path):
    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True)
    fig.suptitle(f"Archetype 1 — {event['title']}", fontsize=13, fontweight="bold")

    _plot_channel(axes[0], df, "gas_ppm", "Gas concentration")
    _shade_event(axes[0], df, event)
    _legend(axes[0])

    _plot_channel(axes[1], df, "pressure_bar", "Tank / pipeline pressure")
    _shade_event(axes[1], df, event)
    _legend(axes[1])

    ax2 = axes[2]
    ax2.plot(df["ts"], df["wind_speed_kmh"], color="#2980b9", linewidth=1.1, label="Wind speed (km/h)")
    ax2.set_ylabel("Wind speed\n(km/h)")
    ax2.margins(x=0)
    ax2b = ax2.twinx()
    ax2b.step(df["ts"], df["workers_in_tank_farm"], color="#d35400", linewidth=1.3, where="post",
               label="Workers in Tank Farm")
    ax2b.set_ylabel("Workers present")
    ax2b.set_ylim(-0.2, 3.2)
    _shade_event(ax2, df, event)
    h2, l2 = ax2.get_legend_handles_labels()
    h2b, l2b = ax2b.get_legend_handles_labels()
    ax2.legend(h2 + h2b, l2 + l2b, loc="upper left", fontsize=8, framealpha=0.9)

    _plot_risk_panel(axes[3], df, event, risk)
    _format_xaxis(axes[3])
    axes[3].set_xlabel("Time of day")

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_bearing_failure(df, event, risk, out_path: Path):
    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True)
    fig.suptitle(f"Archetype 2 — {event['title']}", fontsize=13, fontweight="bold")

    _plot_channel(axes[0], df, "vibration_mms", "COMP-01 vibration")
    _shade_event(axes[0], df, event)
    _legend(axes[0])

    _plot_channel(axes[1], df, "temp_compressor_c", "COMP-01 discharge temp")
    _shade_event(axes[1], df, event)
    _legend(axes[1])

    ax2 = axes[2]
    ax2.plot(df["ts"], df["compressor_health"], color="#16a085", linewidth=1.4, label="COMP-01 health score")
    ax2.axhline(1.0, color="#95a5a6", linestyle=":", linewidth=1.0, label="As-new (1.0)")
    ax2.set_ylabel("Health score\n(0-1)")
    ax2.set_ylim(0.0, 1.05)
    ax2.margins(x=0)
    _shade_event(ax2, df, event)
    ax2.annotate(
        "MT-01 (bearing inspection)\noverdue 6 days at day start",
        xy=(df["ts"].iloc[event["start_idx"]], df["compressor_health"].iloc[event["start_idx"]]),
        xytext=(15, -40), textcoords="offset points", fontsize=8,
        arrowprops=dict(arrowstyle="->", color="#7f8c8d"),
    )
    _legend(ax2)

    _plot_risk_panel(axes[3], df, event, risk)
    _format_xaxis(axes[3])
    axes[3].set_xlabel("Time of day")

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_overpressure(df, event, risk, out_path: Path):
    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True)
    fig.suptitle(f"Archetype 3 — {event['title']}", fontsize=13, fontweight="bold")

    _plot_channel(axes[0], df, "pressure_bar", "TANK-01 pressure")
    _shade_event(axes[0], df, event)
    _legend(axes[0])

    _plot_channel(axes[1], df, "temp_tank_c", "TANK-01 shell temp")
    _shade_event(axes[1], df, event)
    _legend(axes[1])

    ax2 = axes[2]
    ax2.plot(df["ts"], df["relief_capacity_pct"], color="#2980b9", linewidth=1.3, label="Relief capacity (%)")
    ax2.set_ylabel("Relief capacity\n(%)")
    ax2.set_ylim(0, 110)
    ax2.margins(x=0)
    ax2b = ax2.twinx()
    ax2b.step(df["ts"], df["hot_work_permit_active"].astype(int), color="#c0392b", linewidth=1.3,
              where="post", label="Hot-work permit active")
    ax2b.set_ylabel("Permit active")
    ax2b.set_ylim(-0.2, 1.2)
    _shade_event(ax2, df, event)
    h2, l2 = ax2.get_legend_handles_labels()
    h2b, l2b = ax2b.get_legend_handles_labels()
    ax2.legend(h2 + h2b, l2 + l2b, loc="upper left", fontsize=8, framealpha=0.9)

    _plot_risk_panel(axes[3], df, event, risk)
    _format_xaxis(axes[3])
    axes[3].set_xlabel("Time of day")

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_overview(df, events, risk, out_path: Path):
    channels = [
        ("pressure_bar", "Pressure (bar)"),
        ("gas_ppm", "Gas (ppm)"),
        ("temp_tank_c", "Tank temp (°C)"),
        ("temp_compressor_c", "Compressor temp (°C)"),
        ("vibration_mms", "Vibration (mm/s)"),
    ]
    fig, axes = plt.subplots(len(channels) + 1, 1, figsize=(11, 13), sharex=True)
    fig.suptitle(
        "PlantPulse Demo Day — All Channels Read Normal Alone, "
        "3 Compound Incidents Hidden in the Combination",
        fontsize=12, fontweight="bold",
    )

    colors = ["#c0392b", "#8e44ad", "#d35400", "#16a085", "#2980b9"]
    for ax, (channel, label), color in zip(axes, channels, colors):
        spec = CHANNEL_SPECS[channel]
        ax.plot(df["ts"], df[channel], color=color, linewidth=1.0)
        ax.axhline(spec["alarm_high"], color=ALARM_COLOR, linestyle="--", linewidth=1.0, alpha=0.8)
        ax.set_ylabel(label, fontsize=9)
        ax.margins(x=0)
        for event in events:
            _shade_event(ax, df, event, label=event["title"])

    _plot_risk_panel(axes[-1], df, events[0], risk)
    for event in events[1:]:
        _shade_event(axes[-1], df, event, label=event["title"])

    _format_xaxis(axes[-1])
    axes[-1].set_xlabel("Time of day")

    handles = [
        plt.Line2D([0], [0], color=ALARM_COLOR, linestyle="--", linewidth=1.2, label="Single-channel alarm"),
        plt.Rectangle((0, 0), 1, 1, color=EVENT_COLOR, alpha=0.15, label="Compound incident window (×3)"),
    ]
    fig.legend(handles=handles, loc="upper right", fontsize=8, bbox_to_anchor=(0.99, 0.985))

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df, plant, events = generate_scenario()
    df = _prep(df)
    risk = preview_compound_risk_index(df)
    by_id = {e["id"]: e for e in events}

    plot_overview(df, events, risk, OUT_DIR / "00_full_day_overview.png")
    plot_gas_leak(df, by_id["evt-gas-leak-01"], risk, OUT_DIR / "01_gas_leak_archetype.png")
    plot_bearing_failure(df, by_id["evt-bearing-failure-01"], risk, OUT_DIR / "02_bearing_failure_archetype.png")
    plot_overpressure(df, by_id["evt-overpressure-01"], risk, OUT_DIR / "03_overpressure_archetype.png")

    print(f"Wrote 4 preview plots to {OUT_DIR}")
    for channel, spec in CHANNEL_SPECS.items():
        for event in events:
            if channel not in event["affected_channels"]:
                continue
            window = df.iloc[event["start_idx"]:event["end_idx"] + 1]
            peak = window[channel].max()
            print(
                f"  [{event['id']}] {channel}: peak={peak:.2f} {spec['unit']} "
                f"vs alarm={spec['alarm_high']:.2f} {spec['unit']} "
                f"({peak / spec['alarm_high'] * 100:.0f}% of threshold)"
            )


if __name__ == "__main__":
    main()
