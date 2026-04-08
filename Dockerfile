FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files from repo root (build context = repo root)
COPY pyproject.toml uv.lock requirements.txt ./
COPY models.py ticket_generator.py client.py ./
COPY server/ ./server/
COPY agent/ ./agent/

RUN pip install --no-cache-dir -r requirements.txt
RUN uv sync

ENV WORKERS=4
ENV MAX_CONCURRENT_ENVS=100
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["uv", "run", "server"]
