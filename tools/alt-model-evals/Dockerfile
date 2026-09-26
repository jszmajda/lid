# Harness image for tools/alt-model-evals/run_eval.py.
# The runner passes OPENCODE_VERSION from its single HARNESS_VERSION constant and
# tags the image with that version and a hash of this file.
FROM node:22.23.3-bookworm-slim

ARG OPENCODE_VERSION

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ripgrep ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN npm install -g "opencode-ai@${OPENCODE_VERSION}" \
 && npm cache clean --force

# The mounted fixture repository is owned by the invoking user's UID, which the
# container also runs as; this only guards runtimes that remap mount ownership.
RUN git config --system --add safe.directory '*'
