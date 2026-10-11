# Live mode image: dependencies only in the image; data/, .env and the Telegram session are mounted (deploy/).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
ENV UV_PROJECT_ENVIRONMENT=/venv UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*  # LightGBM
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "--no-sync", "forecast", "live", "--host", "0.0.0.0", "--port", "8790"]
