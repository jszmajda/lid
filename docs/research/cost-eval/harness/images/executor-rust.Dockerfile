# The executor image for Rust seeds (Clowder): the pinned executor image, plus Rust and the build tools, with a
# seed's crate dependencies already in the image's cargo home so a run never depends on crates.io being up
# (crates.io stays reachable). Build it with build_rust_image.py, which supplies the seed's manifests and lockfile.
ARG BASE=lid-cost-eval-executor:2.1.323
FROM ${BASE}

USER root
# procps: Clowder's terminal lock tests read the process table.
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends build-essential pkg-config procps >/dev/null \
 && rm -rf /var/lib/apt/lists/*
# jj, which Clowder's own instructions ask agents to use; its full and lid variants are colocated jj repositories.
ARG JJ_VERSION=0.46.0
RUN mkdir /tmp/jj \
 && curl -fsSL "https://github.com/jj-vcs/jj/releases/download/v${JJ_VERSION}/jj-v${JJ_VERSION}-$(uname -m)-unknown-linux-musl.tar.gz" \
    | tar -xz -C /tmp/jj \
 && install -m 755 "$(find /tmp/jj -type f -name jj | head -1)" /usr/local/bin/jj \
 && rm -rf /tmp/jj && jj --version

USER agent
RUN jj config set --user user.name "Lab Owner" && jj config set --user user.email owner@example.invalid
ARG RUST_VERSION=1.89.0
ENV RUSTUP_HOME=/home/agent/.rustup CARGO_HOME=/home/agent/.cargo
ENV PATH=/home/agent/.cargo/bin:$PATH
RUN curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain ${RUST_VERSION} --no-modify-path >/dev/null \
 && rustc --version && cargo --version

# The seed's workspace manifests and lockfile, with stub targets: enough for cargo to resolve and fetch every
# locked crate for every platform, and nothing of the seed's code.
COPY --chown=agent:agent fetch /tmp/seed-fetch
RUN cd /tmp/seed-fetch && cargo fetch --locked && rm -rf /tmp/seed-fetch

WORKDIR /work
