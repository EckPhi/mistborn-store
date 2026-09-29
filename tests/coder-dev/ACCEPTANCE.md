# Manual Linux RunTipi acceptance

Run on a disposable/trusted Linux host with RunTipi 4.10.1+ and Docker's normal
`/var/run/docker.sock`. This checklist is intentionally **not marked passed**.
No remote test host was available while implementing the app. Repeat on AMD64
and ARM64 before certifying both as fully runtime tested.

## Install and connect

1. Publish/use the store branch containing `coder-dev`, add that store in RunTipi,
   then install **Coder Development Environment** with a unique administrator
   username/email/password. Leave the default workspace name `dev`.
2. Open the app using RunTipi's direct port/domain. Sign in with that password.
   Wait for the initial image build. Confirm `general-development` exists once,
   `dev` exists once and its agent is connected.
3. Inspect bootstrap logs in RunTipi: successful completion; no password/token.
   Confirm PostgreSQL and Coder are healthy, and bootstrap eventually healthy.
4. Connect VS Code and Cursor using Coder Remote; open `/workspaces`. Connect
   JetBrains using its Coder plugin or generated SSH configuration. From your
   laptop run `coder login <url>` and `coder ssh dev`.
5. Repeat connectivity with a LAN URL, a RunTipi HTTPS domain and a Tailscale-only
   host address as available. Verify the workspace agent also reaches each URL.
   A certificate/DNS failure must be fixed before marking this passed.

## Compiler and tools

In `dev`, clone a small C++ repository from any supported Git remote and run its
CMake build/tests. For an independent compiler smoke test, create this example:

```sh
mkdir -p /workspaces/acceptance-cpp
cd /workspaces/acceptance-cpp
cat > CMakeLists.txt <<'CMAKE'
cmake_minimum_required(VERSION 3.16)
project(acceptance LANGUAGES CXX)
enable_testing()
add_executable(hello main.cpp)
add_test(NAME hello COMMAND hello)
CMAKE
printf '#include <iostream>\nint main(){std::cout << "ok\\n"; return 0;}\n' > main.cpp
cmake -S . -B build -G Ninja
cmake --build build
ctest --test-dir build --output-on-failure
python3 --version
node --version
git --version
conan --version
uv --version
pnpm --version
docker --version
docker compose version
```

Run `python3 -m http.server 8000 --bind 0.0.0.0` and access it through
`coder port-forward dev --tcp 8000:8000`. Repeat with a Node/Vite server on
3000/5173. No VPS inbound workspace port should be necessary.

## Persistence and upgrade

1. Write `/workspaces/persistence-test.txt`; record its contents and workspace UUID.
   Set a Git option and create a non-secret test file in `/home/coder/.config`.
2. Stop/start `dev`, restart the RunTipi app, then reboot the host. Reconnect and
   confirm all files/configuration and the UUID remain. Stop `dev` deliberately,
   restart the app again and confirm bootstrap leaves it stopped.
3. Restart the bootstrap repeatedly. Confirm one administrator, one template and
   one default workspace. Change the administrator password inside Coder;
   update the RunTipi password field and confirm restarts never reset it.
4. Upgrade to a reviewable app definition with a template-only change and a bumped
   `tipi_version`. Confirm a new template version, unchanged administrator and
   workspace identity, untouched source/home, and no automatic workspace update.
5. Explicitly update/start the workspace to the new template, verify files again.
6. On a disposable second workspace, write a file and delete the workspace in
   Coder. Confirm `workspaces/<uuid>/source` and `home` remain on the host. A new
   same-name workspace must use fresh UUID storage; it must not reuse old data.

## Failure/recovery and security

- Break access-URL reachability temporarily on the test deployment. The agent
  should fail visibly; fix it and retry without duplicate resources.
- Interrupt bootstrap after admin/template initialization. Restart and confirm
  setup resumes. Test a failed initial workspace build and successful retry.
- Verify the normal workspace has no `/var/run/docker.sock` and `docker info`
  cannot connect. Enable Host Docker socket access on the disposable workspace,
  restart it, then run a small build and `docker compose up/down`. Confirm its
  effective socket GID is detected automatically; never chmod the socket.
- From the host (test verification only), inspect the Coder process UID: 1000.
  Inspect workspace agent UID: 1000. PostgreSQL must have no host port mappings;
  only Coder has the RunTipi UI mapping. No Docker TCP endpoint is introduced.
- Inspect bootstrap/server logs for the exact supplied test secrets without
  publishing their contents. Inspect state-file permissions (0600) and state
  directory (0700). Do not include unredacted installation environment output.
- Run your image scanner against the pulled images and locally built workspace
  image. Record findings rather than assuming a pinned image is vulnerability free.

## Native backup/restore

1. Start two workspaces and deliberately stop a third. Stop the RunTipi app.
   Confirm bootstrap logs **Workspace shutdown complete** before Coder shuts
   down and that both running workspace containers have stopped/disappeared.
   Start the app: only the previous two should resume, using their selected
   template versions. The third must stay stopped. Repeat while interrupting
   shutdown to verify the journal survives and failures produce the manual-stop
   warning. A forced SIGKILL/power loss does not run this handler.
2. Take a RunTipi native backup and verify graceful workspace shutdown in the
   logs. If the handler fails, stop ALL workspaces manually and repeat the backup.
3. Inspect the archive privately: PostgreSQL, coder/bootstrap, workspace source/home
   and caches should be included; `runtime` is regenerable. It contains secrets.
4. Restore to a disposable installation using the SAME app-data host path and
   database/bootstrap credentials. Start the app/workspace. Confirm login,
   template state, workspace identity and all source/configuration fixtures.
5. Record the RunTipi/Docker versions, host architecture and each result. This
   restore test is required before relying on native backups for source data.

Testing is complete only after these live checks pass. Local scenario tests
prove bootstrap control flow, not actual image builds, IDE behavior or host reboot.
