# The executor image for Node seeds (openGym, M2h): the pinned executor image, plus Node 26.13.1 and npm, taken from
# the node:26-bookworm-slim image the subject's feasibility runs used (runs/analysis/opengym/summary.txt), pinned by
# digest. The subject's own dependencies are not in the image: they are installed into the workspace volume.
#   docker build -f images/executor-node.Dockerfile -t lid-cost-eval-executor-node:2.1.323 images/
ARG BASE=lid-cost-eval-executor:2.1.323
ARG NODE_IMAGE=node@sha256:5df79989ed685e09f0a98019db4cebfb22fb9df1a53c0161664a011f7ff6b0f1
FROM ${NODE_IMAGE} AS node
FROM ${BASE}

USER root
# libatomic1: node links it, and the slim base lacks it.
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends libatomic1 >/dev/null \
 && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && node --version && npm --version

USER agent
WORKDIR /work
