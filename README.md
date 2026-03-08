# Aviation Weather AI Briefing Tool

A Python scaffold for building an AI-assisted aviation weather briefing workflow.

## Features

- Fetch TAF data from NOAA endpoints
- Parse TAF text into structured records
- Generate briefing summaries with flight-category context
- CLI entrypoint for quick terminal usage

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
make test
make run-cli ICAO TAF_STRING
```

## Development

```bash
make lint
make test
```
