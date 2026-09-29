# renovate: datasource=docker depName=docker
FROM docker:28.5.2-cli AS docker-cli
# renovate: datasource=docker depName=python
FROM python:3.13.15-bookworm AS python-runtime
# renovate: datasource=docker depName=rust
FROM rust:1.97.1-bookworm AS rust-runtime
# renovate: datasource=docker depName=node
FROM node:24.21.0-bookworm AS base
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs curl wget ca-certificates openssh-client rsync bash zsh jq \
    unzip zip tar less nano vim build-essential gcc g++ clang lldb gdb cmake \
    ninja-build make pkg-config ccache python3 python3-pip python3-venv \
    ripgrep fd-find fzf htop gh shellcheck gosu && \
    rm -rf /var/lib/apt/lists/* && \
    usermod -l coder -d /home/coder -s /bin/bash node && \
    groupmod -n coder node && mkdir -p /home/coder && chown coder:coder /home/coder
# Pin Python developer utilities; install outside the persisted developer home.
RUN python3 -m venv /opt/dev-tools && \
    /opt/dev-tools/bin/pip install --no-cache-dir uv==0.8.22 conan==2.20.1 && \
    npm install -g pnpm@10.17.1 bun@1.3.14 && \
    mkdir -p /usr/local/lib/docker/cli-plugins
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins
COPY entrypoint.sh /usr/local/bin/workspace-entrypoint
RUN chmod 755 /usr/local/bin/workspace-entrypoint && \
    printf 'Coder Development Workspace\nClone a repository: git clone <repo>\nTools: Git, GCC/Clang, CMake, Ninja, Python, Node, ccache\n' > /etc/coder-dev-motd && \
    printf '\ncd /workspaces\ncat /etc/coder-dev-motd\n' >> /etc/bash.bashrc
ENV HOME=/home/coder PATH=/home/coder/.local/share/pnpm:/opt/dev-tools/bin:$PATH
WORKDIR /workspaces
ENTRYPOINT ["/usr/local/bin/workspace-entrypoint"]

# Python 3.13 is required by power-price-collector and refurb-compare.
FROM base AS python
COPY --from=python-runtime /usr/local /usr/local
ENV PATH=/usr/local/bin:/opt/dev-tools/bin:$PATH
RUN /opt/dev-tools/bin/pip install --no-cache-dir poetry==2.2.1 && \
    apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    libnspr4 libdbus-1-3 libx11-6 libxcb1 libxext6 libatspi2.0-0 \
    libpango-1.0-0 libcairo2 fonts-liberation xvfb && \
    rm -rf /var/lib/apt/lists/* && ldconfig
ENV PLAYWRIGHT_BROWSERS_PATH=/cache/playwright

# Rustup proxies use the image's pinned toolchain; Cargo downloads persist in home.
FROM base AS rust
COPY --from=rust-runtime /usr/local/cargo/bin /opt/rust-bin
COPY --from=rust-runtime /usr/local/rustup /opt/rustup
ENV RUSTUP_HOME=/opt/rustup CARGO_HOME=/home/coder/.cargo
ENV PATH=/opt/rust-bin:/home/coder/.cargo/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev libclang-dev protobuf-compiler && rm -rf /var/lib/apt/lists/* && \
    chown -R coder:coder /opt/rustup && \
    gosu coder rustup component add rustfmt clippy rust-analyzer && \
    gosu coder rustup target add wasm32-wasip2

# Official source commit for Flutter 3.47.3; SDK downloads happen while building.
# This target is AMD64 only; bootstrap omits it on ARM64 hosts.
FROM base AS flutter
RUN test "`dpkg --print-architecture`" = amd64 && \
    apt-get update && apt-get install -y --no-install-recommends \
    xz-utils libglu1-mesa libgtk-3-dev liblzma-dev openjdk-17-jdk-headless && \
    rm -rf /var/lib/apt/lists/* && \
    git clone --depth 1 --branch 3.47.3 https://github.com/flutter/flutter.git /opt/flutter && \
    test "`git -C /opt/flutter rev-parse HEAD`" = e8113bf45620cbeb8aff64947ee4c93e16adb4cf && \
    chown -R coder:coder /opt/flutter
ENV PATH=/opt/flutter/bin:$PATH PUB_CACHE=/cache/pub
# Runtime /cache is a bind mount created by the entrypoint, not present at build time.
RUN PUB_CACHE=/opt/flutter/.pub-cache gosu coder flutter config --no-analytics --enable-web --enable-linux-desktop && \
    PUB_CACHE=/opt/flutter/.pub-cache gosu coder flutter precache --web --linux

# Keep the previous generic toolset as the default Docker build target too.
FROM base AS general
