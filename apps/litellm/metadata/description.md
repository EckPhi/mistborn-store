# LiteLLM AI Gateway

Configure your AI providers once and connect OMP in every Coder workspace through
this gateway. Provider credentials stay on the server; workspaces use revocable
virtual keys. PostgreSQL stores provider configuration, keys and usage records.

## Install and open the dashboard

Choose a dashboard password during installation. The generated master key,
encryption key and database password are retained in Runtipi's app configuration.
The first startup initializes the database and can take several minutes.

Open `http://<runtipi-host>:4011/ui/` and sign in with your configured username
(default `admin`) and password. For remote access, expose the app on an HTTPS
domain through Runtipi. The client API base URL is `https://<gateway-domain>/v1`.
Port 4011 is the direct host port; PostgreSQL is not exposed on the host.
Use LiteLLM's own authentication for agent requests. Runtipi's additional browser
authentication can redirect API clients to a login page, so leave that option off
for the gateway endpoint.

## Add OpenRouter or Requesty

Use the dashboard's model management page to add models and their provider keys.
Use model aliases such as `coding` and `fast` as the names clients will select.
You can change the upstream model behind an alias centrally.

- **OpenRouter:** select OpenRouter and use a model ID from your OpenRouter
  account. The underlying LiteLLM model is `openrouter/<OpenRouter model ID>`.
- **Requesty:** use an OpenAI-compatible connection with API base
  `https://router.requesty.ai/v1` and your Requesty API key. The underlying
  LiteLLM model is `openai/<Requesty model ID>`; the `openai/` prefix selects the
  compatibility adapter, not an OpenAI account. For example, Requesty's
  `openai/gpt-4o` becomes `openai/openai/gpt-4o` in LiteLLM.

Choose models that support tool calls for OMP. Test a model in the dashboard's
Playground before connecting a workspace. Requesty integration uses its documented
OpenAI-compatible API; it is not a native Requesty provider in this package.

## Connect OMP in Coder

### Automatic workspace provisioning

In the **Coder Development Environment** Runtipi settings, set:

- **Optional AI gateway URL:** the LiteLLM base URL reachable from both Coder's
  server helper and its workspaces, for example `https://ai.example.com`.
- **AI gateway admin key:** `sk-` followed by the generated **Gateway master key
  material** from this app's settings.
- **AI gateway model aliases:** the comma-separated aliases you added in LiteLLM,
  such as `coding,fast`. These are the models each managed workspace key may use.

Update/restart the Coder app. Its server helper checks the bootstrap
administrator's workspaces every 30 seconds and provisions a separate inference
key for each workspace with a persistent home. The admin key remains on the
server; it is not put in Terraform variables or workspace environments.

Each virtual key is saved at `~/.config/ai-gateway/key` with mode 0600. A fresh OMP
installation is configured automatically. Existing OMP catalogs are preserved;
merge `~/.config/ai-gateway/models.yml` into your existing catalog if needed.
Restart OMP after initial provisioning. No template update is required because
provisioning uses the existing persistent workspace home.

Keys survive workspace stops and server restarts. Deleting a Coder workspace
revokes its managed key and removes the matching key file from its retained home.
Blocking, deleting or expiring a key in LiteLLM is respected: provisioning never
silently unblocks it or creates a replacement. Changing the allowed model aliases
updates the existing active keys without resetting their budgets.

Back up Coder's `bootstrap/ai-gateway.json` with its app configuration and workspace
homes. It contains the managed virtual keys and recovery state. Leave the gateway
URL empty to disable provisioning; this does not revoke existing keys. Before
switching to a different gateway URL, revoke the old managed keys and archive the
state file. A lost state file cannot recover existing plaintext keys from LiteLLM.
The configured key path is owned by this automation; move any manual key elsewhere
before enabling it if you need to retain that manual configuration.

### Manual connection

Create a virtual key in the dashboard's Keys page, granting access to the model
aliases you added. One key per workspace lets you revoke a workspace independently.
Set a budget on the key if desired. Do not distribute the gateway's master key or
your upstream provider keys to workspaces.

The store's Coder Development Environment already includes OMP when AI coding
tools are enabled. Run the following in its Bash terminal to save the virtual key
without printing it or putting it in shell history:

```bash
mkdir -p "$HOME/.config/ai-gateway"
chmod 700 "$HOME/.config/ai-gateway"
read -r -s -p 'LiteLLM virtual key: ' gateway_key
printf '\n'
(umask 077; printf '%s' "$gateway_key" > "$HOME/.config/ai-gateway/key")
chmod 600 "$HOME/.config/ai-gateway/key"
unset gateway_key
```

Merge this into `~/.omp/agent/models.yml`, replacing the URL and using the actual
absolute home path if it differs from `/home/coder`:

```yaml
providers:
  personal-gateway:
    baseUrl: https://YOUR-GATEWAY-DOMAIN/v1
    apiKey: "!cat /home/coder/.config/ai-gateway/key"
    api: openai-completions
    discovery:
      type: openai-models-list
```

This uses the OpenAI-compatible Chat Completions route for both providers. OMP
discovers your permitted aliases from `/v1/models`. Restart OMP and select a model
under `personal-gateway`. Generic discovery may provide less context-limit and
pricing metadata than a native provider; set explicit model metadata in OMP if
your chosen model is not recognized. Provider selection and credentials remain
centralized, while OMP's tools run inside the workspace.

Keep the virtual key file out of source repositories. The key file and OMP
settings persist in the Coder workspace home. No OMP broker configuration is
needed for LiteLLM.

## Shared skills

Keep skills in a separate private Git repository and clone it into each
workspace's persistent home. Merge this into `~/.omp/agent/config.yml`:

```yaml
skills:
  customDirectories:
    - /home/coder/.local/share/ai-config/skills
```

Use `skills/<skill-name>/SKILL.md`, with `name` and `description` frontmatter.
Update the checkout with `git pull --ff-only` and restart OMP. Add synchronization
to your Coder startup script if you want updates whenever a workspace starts.
The gateway does not distribute or execute skill files. The store's
`docs/shared-ai-skills.md` contains the full repository and update setup.

## Backups and updates

Back up `${APP_DATA_DIR}/postgres` together with Runtipi's app configuration,
especially the provider encryption key. Stop the app before filesystem backups
or use PostgreSQL's database backup tools. Changing the encryption key makes
stored provider credentials unreadable; it has no in-place rotation. Changing
the database password field after installation does not update PostgreSQL.

Image updates can migrate the database. Back it up before upgrading; restoring
an older image may also require restoring its matching database backup.

## References

- [LiteLLM deployment](https://docs.litellm.ai/docs/proxy/docker_quick_start)
- [Virtual keys](https://docs.litellm.ai/docs/proxy/virtual_keys)
- [Requesty API](https://docs.requesty.ai/)
- [OMP model configuration](https://github.com/can1357/oh-my-pi/blob/v18.8.0/docs/models.md)
