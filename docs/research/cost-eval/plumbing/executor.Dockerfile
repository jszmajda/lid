FROM python:3.12-slim
RUN apt-get update -qq && apt-get install -y -qq git curl ca-certificates faketime ripgrep procps >/dev/null && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /usr/local/bin/
RUN useradd -m -s /bin/bash agent && mkdir -p /work /cfg && chown agent:agent /work /cfg
USER agent
WORKDIR /home/agent
ARG CLAUDE_VERSION=2.1.323
RUN curl -fsSL https://claude.ai/install.sh | bash -s ${CLAUDE_VERSION} >/dev/null
ENV PATH=/home/agent/.local/bin:$PATH
RUN git config --global user.name "Lab Owner" && git config --global user.email owner@example.invalid && git config --global init.defaultBranch main
ENV CLAUDE_CONFIG_DIR=/cfg
WORKDIR /work
