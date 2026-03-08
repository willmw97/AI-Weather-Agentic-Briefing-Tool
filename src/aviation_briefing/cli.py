"""CLI entry point."""

from __future__ import annotations

import asyncio

import typer
from rich import print

from .briefing_engine import build_briefing
from .taf_fetcher import fetch_raw_taf
from .taf_parser import parse_taf

app = typer.Typer(help="Aviation weather briefing CLI")


@app.command()
def main(station: str, taf: str | None = None) -> None:
    """Generate a briefing from provided or fetched TAF text."""

    raw_taf = taf or asyncio.run(fetch_raw_taf(station))
    record = parse_taf(raw_taf)
    briefing = build_briefing(record)
    print(f"[bold green]{briefing.station}[/bold green]")
    print(briefing.summary)
    if briefing.hazards:
        print("Hazards:")
        for hazard in briefing.hazards:
            print(f"- {hazard}")


if __name__ == "__main__":
    app()
