# renovate: datasource=docker depName=docker
FROM docker:28.5.2-cli AS docker-cli
# renovate: datasource=docker depName=node
FROM node:24.21.0-bookworm
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
    npm install -g pnpm@10.17.1 && \
    mkdir -p /usr/local/lib/docker/cli-plugins
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins
COPY entrypoint.sh /usr/local/bin/workspace-entrypoint
RUN chmod 755 /usr/local/bin/workspace-entrypoint && \
    printf 'Coder Development Workspace\nClone a repository: git clone <repo>\nTools: Git, GCC/Clang, CMake, Ninja, Python, Node, ccache\n' > /etc/coder-dev-motd && \
    printf '\ncd /workspaces\ncat /etc/coder-dev-motd\n' >> /etc/bash.bashrc
ENV HOME=/home/coder PATH=/opt/dev-tools/bin:$PATH
WORKDIR /workspaces
ENTRYPOINT ["/usr/local/bin/workspace-entrypoint"]
