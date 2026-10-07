# Shared AI skills in Coder

Keep personal skills in one private Git repository. The gateway centralizes
provider credentials; the skills repository centralizes instructions and their
supporting files. OMP executes tools in each workspace, so skills must be present
there even when inference runs through a remote gateway.

## Repository layout

```text
ai-config/
  skills/
    review/
      SKILL.md
    python/
      SKILL.md
      scripts/
```

Each `SKILL.md` starts with frontmatter:

```markdown
---
name: review
description: Review a change for correctness, regressions and missing validation.
---

Read the relevant project instructions and inspect the change before commenting.
Report actionable findings with file locations and an explanation of the impact.
```

Keep provider keys and gateway tokens out of this repository. Authenticate private
Git access using the workspace's SSH key or existing Git credential manager.

## First workspace setup

Clone the repository into the persistent workspace home, replacing the example
URL with your actual repository:

```sh
mkdir -p "$HOME/.local/share"
git clone git@github.com:YOUR_ACCOUNT/ai-config.git "$HOME/.local/share/ai-config"
```

Merge this into `~/.omp/agent/config.yml`, using the real absolute home path:

```yaml
skills:
  customDirectories:
    - /home/coder/.local/share/ai-config/skills
```

Do not overwrite existing settings. If `skills.customDirectories` already exists,
append the directory to its list. OMP discovers immediate skill subdirectories;
for a layout such as `skills/team/python/SKILL.md`, list `skills/team` instead.
Restart OMP after updating the checkout so the new skills are discovered.

## Updating all workspaces

Use the same repository URL and revision in every workspace. After committing
and pushing a skills change, update each clean checkout:

```sh
git -C "$HOME/.local/share/ai-config" pull --ff-only
```

For automatic synchronization, add that command to the Coder agent startup
script after the checkout has been provisioned. It runs when a workspace starts,
not continuously while it is running. A failed update should be visible in the
startup log; retain the existing checkout rather than resetting local edits.

For reproducible versions, distribute a commit SHA instead of following a branch:
fetch it and check out that commit in a dedicated clean checkout. Change the
distributed SHA when you want workspaces to receive an update.

## Existing Coder app

The `coder-dev` workspace image already pins OMP 18.8.0 when **Enable AI coding
tools** is enabled. Its persistent `/home/coder` preserves the skills checkout,
OMP settings and Git credentials across workspace restarts. Changes to a Coder
template require explicitly updating existing workspaces to that template version.

## References

- [OMP skill discovery](https://github.com/can1357/oh-my-pi/blob/v18.8.0/docs/skills.md)
- [OMP gateway architecture](https://github.com/can1357/oh-my-pi/blob/v18.8.0/docs/auth-broker-gateway.md)
