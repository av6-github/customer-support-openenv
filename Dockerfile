FROM ghcr.io/meta-pytorch/openenv-base:latest

WORKDIR /app

COPY . .

RUN uv sync

CMD ["server"]