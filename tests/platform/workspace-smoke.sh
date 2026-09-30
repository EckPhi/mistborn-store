#!/bin/bash
set -euo pipefail
test "$(id -u)" = 1000
for tool in git git-lfs curl wget jq rg fd fdfind fzf tmux rsync ssh gh bash zsh vim nano zip unzip tar gcc g++ clang gdb lldb cmake ninja make pkg-config ccache python3 uv node npm pnpm conan codex claude opencode omnigent; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
python3 --version
node --version
git --version
codex --version
claude --version
opencode --version
omnigent --version
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
cat > CMakeLists.txt <<'CMAKE'
cmake_minimum_required(VERSION 3.16)
project(platform_smoke LANGUAGES CXX)
enable_testing()
add_executable(smoke main.cpp)
add_test(NAME smoke COMMAND smoke)
CMAKE
printf 'int main() { return 0; }\n' > main.cpp
cmake -S . -B build -G Ninja
cmake --build build
ctest --test-dir build --output-on-failure
