FROM node:22-bookworm-slim

ARG OPENCODE_VERSION=2.3.2
ARG OPENCODE_REPO=anomalyco/opencode
ARG TARGETARCH
ARG PLAYWRIGHT_MCP_VERSION=latest
ARG CONTEXT7_MCP_VERSION=latest

ENV DEBIAN_FRONTEND=noninteractive \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    OPENCODE_DISABLE_AUTOUPDATE=1 \
    OPENCODE_DISABLE_PRUNE=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git coreutils \
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${TARGETARCH:-$(dpkg --print-architecture)}" in amd64) arch=x64 ;; arm64) arch=arm64 ;; *) exit 1 ;; esac; \
    asset="opencode-linux-${arch}.tar.gz"; \
    base="https://github.com/${OPENCODE_REPO}/releases/download/v${OPENCODE_VERSION}"; \
    cd /tmp; \
    curl -fsSLO "${base}/${asset}"; \
    curl -fsSLO "${base}/SHA256SUMS"; \
    grep " ${asset}\$" SHA256SUMS | sha256sum -c -; \
    mkdir oc; tar -xzf "${asset}" -C oc; \
    install -m 0755 "$(find oc -type f -name opencode | head -n1)" /usr/local/bin/opencode; \
    rm -rf oc "${asset}" SHA256SUMS; \
    opencode --version

RUN npm install -g \
      "@playwright/mcp@${PLAYWRIGHT_MCP_VERSION}" \
      "@upstash/context7-mcp@${CONTEXT7_MCP_VERSION}" \
 && cd "$(npm root -g)/@playwright/mcp" \
 && npx --no-install playwright install --with-deps chromium \
 && chmod -R a+rX /ms-playwright \
 && npm cache clean --force

COPY opencode.json /home/node/.config/opencode/opencode.json
COPY run-agent.sh /usr/local/bin/run-agent
RUN chmod +x /usr/local/bin/run-agent \
 && mkdir -p /workspace /out \
 && chown -R node:node /home/node /workspace /out

USER node
WORKDIR /workspace
ENTRYPOINT ["run-agent"]
