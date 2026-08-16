# Garage

[Garage](https://garagehq.deuxfleurs.fr) is a lightweight, S3-compatible object storage service written in Rust by [Deuxfleurs](https://deuxfleurs.fr). It is built for self-hosted infrastructure on cheap, unreliable hardware: no external database, modest RAM usage, and a data model designed around geo-distributed replication.

This app packages Garage as a **single-node** store, with the cluster layout created automatically on first boot, plus the [Garage Web UI](https://github.com/khairul169/garage-webui) for browsing buckets and managing access keys.

## What you get

| Endpoint | Port | Notes |
|---|---|---|
| Web UI | `3909` | The app's main port — this is what the *Open* button and the exposed domain point at |
| S3 API | `3900` | Point `aws-cli`, rclone, restic, Nextcloud, backups… here |
| Static website hosting | `3902` | Serves buckets configured for website access |
| Admin API | internal | Reachable only from the web UI container, on `http://garage:3903` |

The S3 API and the website endpoint are published directly on the host: `http://<your-server-ip>:3900` and `:3902`. Only the web UI goes through the runtipi reverse proxy, so exposing this app on a domain gives you TLS for the *admin UI*, not for the S3 endpoint. If you need S3 over HTTPS from outside your LAN, put your own reverse proxy in front of port 3900.

## First start

On the first boot Garage:

1. writes `/etc/garage/garage.toml` from the app settings,
2. creates a single-node cluster layout sized to the free space of the data disk,
3. creates the access key `GK<default access key>` with the secret you can read back in the app settings,
4. creates the default bucket and grants that key read/write access to it.

Open the web UI, log in (if you set a password), and you will find the key under **Keys** and the bucket under **Buckets**. Create additional keys and buckets there — one key per application is the sane setup.

## Connecting an S3 client

```
endpoint   http://<your-server-ip>:3900
region     garage            (whatever you set as "S3 region")
access key GK…               (from the web UI, or app settings)
secret key …
```

Use **path-style** addressing unless you configured an *S3 root domain*. Example with the AWS CLI:

```bash
aws --endpoint-url http://<your-server-ip>:3900 --region garage s3 ls s3://default
```

Vhost-style access (`bucket.s3.example.com`) only works if you set *S3 root domain* to `.s3.example.com` and point that wildcard DNS record at port 3900 yourself.

## Settings that matter

- **RPC secret / admin API token** are generated once at install. They are written into `garage.toml` (mode `600`) on every start.
- **Default access key / secret key** are only applied while creating the key. Garage refuses to start if you change the secret of an existing key — create a new key in the web UI instead and leave these fields alone.
- **Web UI password** enables the UI login. Leave it empty only on a trusted LAN — the UI has full admin rights over your data. Avoid single quotes in the password; the bcrypt hash is generated at container start and handed to the UI through `app-data/garage/data/webui/webui.env`.
- **Compression level** is the zstd level used for stored blocks.

`garage.toml` is regenerated from these fields on every start, so hand edits to `app-data/garage/data/config/garage.toml` do not survive a restart.

## Data layout

```
app-data/garage/data/meta      # metadata database (LMDB) — small, back this up
app-data/garage/data/blocks    # object data blocks — the bulk of your storage
app-data/garage/data/config    # generated garage.toml
```

Back up `meta` together with `blocks`; metadata alone is worthless and blocks alone cannot be listed. Keep the RPC secret with the backup, too.

## Single-node only

The app starts Garage with `--single-node`, which means `replication_factor = 1` — **there is no redundancy**, exactly like a plain disk. Use RAID or backups for durability. If you later grow this into a real multi-node cluster, the flag will refuse to start once the layout has been changed by hand; at that point you should manage the cluster with the `garage` CLI and drop the flag.

For the full manual — bucket aliases, quotas, website hosting, multi-node layouts — see the [Garage documentation](https://garagehq.deuxfleurs.fr/documentation/).
