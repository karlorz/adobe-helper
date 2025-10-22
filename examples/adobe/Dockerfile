# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_PYTHON_INSTALL_DIR=/opt/python

WORKDIR /app

RUN uv python install 3.11

# Install adobe-helper from PyPI
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv && \
    uv pip install adobe-helper

# Copy test script
COPY examples/adobe/basic_usage.py ./basic_usage.py

CMD ["/bin/sh", "-lc", "uv run python basic_usage.py"]
