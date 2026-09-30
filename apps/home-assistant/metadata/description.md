# Home Assistant

Home Assistant is an open-source home automation platform focused on local control and privacy. It integrates with thousands of devices and services and pairs well with the other apps in this store (Zigbee2MQTT, Matter Server, Music Assistant, go2rtc, Eufy Security WS, …).

## Networking

The container runs in **host network mode**, which Home Assistant requires for device discovery (mDNS/SSDP), HomeKit, and many LAN integrations. Because of that it cannot be reverse-proxied by runtipi — open the UI directly at:

```
http://<host-ip>:8123
```

## Editing configuration files — bundled File Browser

Home Assistant Container has no add-on store (add-ons are a Home Assistant OS feature), so this app bundles [File Browser](https://filebrowser.org) as a sidecar with full read/write access to the Home Assistant `/config` directory. Use it to edit `configuration.yaml`, `automations.yaml`, blueprints, themes, and anything else inside the config volume:

```
http://<host-ip>:8124
```

- **Login:** username `admin`; the randomly generated password is printed in the filebrowser container logs on first start (`docker logs`). Change it after logging in (Settings → User Management).
- After editing configuration files, reload the affected component or restart Home Assistant from *Developer tools → YAML*.

### Embed File Browser in the Home Assistant sidebar

You can access File Browser from within the Home Assistant UI by adding a webpage dashboard: *Settings → Dashboards → Add dashboard → Webpage*, and enter `http://<host-ip>:8124`. It then shows up as an entry in the sidebar like any other dashboard.

## Notes

- `/run/dbus` is mounted read-only for Bluetooth support.
- USB devices (Zigbee/Z-Wave sticks) are best handled by the dedicated Zigbee2MQTT app in this store, but you can also add `devices` entries via a compose user-config override if you want direct pass-through.
