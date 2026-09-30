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
    ripgrep fd-find fzf htop gh shellcheck tmux gosu bubblewrap procps lsof && \
    rm -rf /var/lib/apt/lists/* && \
    usermod -l coder -d /home/coder -s /usr/bin/zsh node && \
    groupmod -n coder node && mkdir -p /home/coder && chown coder:coder /home/coder && \
    ln -s /usr/bin/fdfind /usr/local/bin/fd
# Install the shell framework and theme in the image, outside persistent home.
# renovate: datasource=github-commits depName=ohmyzsh/ohmyzsh
ARG OH_MY_ZSH_COMMIT=4d4cfc287e9d887b81242c0e431b5f49f9cec5c1
# renovate: datasource=github-commits depName=romkatv/powerlevel10k
ARG POWERLEVEL10K_COMMIT=d05a1b00f9a61f9578bf9dc19b8451942dde8734
RUN git clone https://github.com/ohmyzsh/ohmyzsh.git /opt/oh-my-zsh && \
    git -C /opt/oh-my-zsh checkout "$OH_MY_ZSH_COMMIT" && \
    mkdir -p /opt/oh-my-zsh/custom/themes && \
    git clone https://github.com/romkatv/powerlevel10k.git /opt/oh-my-zsh/custom/themes/powerlevel10k && \
    git -C /opt/oh-my-zsh/custom/themes/powerlevel10k checkout "$POWERLEVEL10K_COMMIT" && \
    rm -rf /opt/oh-my-zsh/.git /opt/oh-my-zsh/custom/themes/powerlevel10k/.git
COPY zshrc /etc/skel/.zshrc
# Python 3.13 also supplies Vibe's supported Python runtime in the general image.
COPY --from=python-runtime /usr/local /usr/local
# Pin Python developer utilities; install outside the persisted developer home.
# renovate: datasource=pypi depName=uv
ARG UV_VERSION=0.8.22
# renovate: datasource=pypi depName=conan
ARG CONAN_VERSION=2.20.1
# renovate: datasource=npm depName=pnpm
ARG PNPM_VERSION=10.17.1
# renovate: datasource=npm depName=bun
ARG BUN_VERSION=1.3.14
RUN python3 -m venv /opt/dev-tools && \
    /opt/dev-tools/bin/pip install --no-cache-dir "uv==$UV_VERSION" "conan==$CONAN_VERSION" && \
    npm install -g "pnpm@$PNPM_VERSION" "bun@$BUN_VERSION" && \
    mkdir -p /usr/local/lib/docker/cli-plugins
# AI agent runtimes. Authentication and mutable settings stay under /home/coder.
# renovate: datasource=npm depName=@openai/codex
ARG CODEX_VERSION=0.159.2
# renovate: datasource=npm depName=@anthropic-ai/claude-code
ARG CLAUDE_CODE_VERSION=2.1.285
# renovate: datasource=npm depName=opencode-ai
ARG OPENCODE_VERSION=1.18.33
# renovate: datasource=pypi depName=omnigent
ARG OMNIGENT_VERSION=0.16.0
# renovate: datasource=npm depName=@oh-my-pi/pi-coding-agent
ARG OMP_VERSION=18.4.4
# renovate: datasource=pypi depName=mistral-vibe
ARG VIBE_VERSION=2.25.8
ARG ENABLE_AI_AGENTS=true
RUN if [ "$ENABLE_AI_AGENTS" = true ]; then \
      npm install -g "@openai/codex@$CODEX_VERSION" "@anthropic-ai/claude-code@$CLAUDE_CODE_VERSION" "opencode-ai@$OPENCODE_VERSION" && \
      UV_TOOL_DIR=/opt/omnigent-tools UV_TOOL_BIN_DIR=/usr/local/bin \
        /opt/dev-tools/bin/uv tool install --python /usr/local/bin/python3 "omnigent==$OMNIGENT_VERSION" && \
      BUN_INSTALL=/opt/omp-bun bun install -g "@oh-my-pi/pi-coding-agent@$OMP_VERSION" && \
      UV_TOOL_DIR=/opt/vibe-tools UV_TOOL_BIN_DIR=/usr/local/bin \
        /opt/dev-tools/bin/uv tool install --python /usr/local/bin/python3 "mistral-vibe==$VIBE_VERSION" && \
      PATH="/opt/omp-bun/bin:$PATH" codex --version && \
      PATH="/opt/omp-bun/bin:$PATH" claude --version && \
      opencode --version && omnigent --version && \
      PATH="/opt/omp-bun/bin:$PATH" omp --version && \
      PATH="/opt/omp-bun/bin:$PATH" vibe --version; \
    fi
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins
COPY entrypoint.sh /usr/local/bin/workspace-entrypoint
COPY agent-info /usr/local/bin/agent-info
RUN chmod 755 /usr/local/bin/workspace-entrypoint && \
    chmod 755 /usr/local/bin/agent-info && \
    printf 'Coder Development Workspace\nProject directory: ~/workspaces (/workspaces)\nAI agents: codex, claude, opencode, omnigent, omp, vibe (run agent-info)\nTools: git, gh, tmux, gcc, clang, cmake, ninja, python, uv, node, pnpm\n' > /etc/coder-dev-motd && \
    printf '\ncd /workspaces\ncat /etc/coder-dev-motd\n' >> /etc/bash.bashrc
ENV HOME=/home/coder PATH=/opt/omp-bun/bin:/home/coder/.local/share/pnpm:/opt/dev-tools/bin:$PATH
WORKDIR /workspaces
ENTRYPOINT ["/usr/local/bin/workspace-entrypoint"]

# Python 3.13 is required by power-price-collector and refurb-compare.
FROM base AS python
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
