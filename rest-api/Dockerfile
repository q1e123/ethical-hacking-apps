FROM python:3.10-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Create a non-root user with a home directory
RUN useradd -m nonInteractive && chown -R nonInteractive:nonInteractive /app

USER nonInteractive

# Default command
CMD ["uv", "run", "main.py"]
