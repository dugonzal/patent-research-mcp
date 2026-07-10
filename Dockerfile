# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir build && \
    python -m build --wheel

# ---- Runtime stage ----
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/

RUN pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl && \
    playwright install chromium --with-deps 2>/dev/null || true

ENV PATENT_RESEARCH_DATA=/data
VOLUME ["/data"]

EXPOSE 8000

ENTRYPOINT ["python", "-m", "patent_research_mcp.server"]
CMD []
