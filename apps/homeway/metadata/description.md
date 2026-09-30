# Homeway

Homeway gives you free, secure remote access to your Home Assistant instance — no port forwarding, VPN or dynamic DNS needed. It also adds free Amazon Alexa and Google Assistant integrations and remote access notifications.

## How it works

Homeway runs as a lightweight relay container next to Home Assistant. It makes an outbound connection to the Homeway service, which then proxies secure access back to your instance.

## Configuration

Provide your **Home Assistant IP / hostname** and a **Long-Lived Access Token** during install. Create the token in Home Assistant under *Profile → Security → Long-Lived Access Tokens*.

## Linking

After the container starts, open its **logs** and look for the linking URL:

```
https://homeway.io/getstarted?...
```

Open that URL to connect the container to your free Homeway account. This app has no local web UI — management happens at [homeway.io](https://homeway.io). Configuration is persisted in the `data` volume (`/data`).
