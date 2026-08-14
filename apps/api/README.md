# AutoScout AI API

This directory contains the backend foundation for AutoScout AI.

## Development

Create a virtual environment with uv:

```bash
uv venv .venv
```

Install dependencies:

```bash
uv sync
```

Run the development server:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API exposes a health endpoint at `/health`.
