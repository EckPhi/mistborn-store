# AppDaemon

AppDaemon is a sandboxed, multi-threaded Python execution environment for writing powerful home automation apps. It connects to Home Assistant (and other platforms) and lets you build automations in plain Python — far more flexible than YAML automations for complex logic.

## Features

- Write automations as Python classes with a clean event/state API
- Sandboxed, hot-reloading apps — edit and run without restarting
- HADashboard: a customizable dashboard for wall-mounted tablets
- MQTT plugin support in addition to Home Assistant

## Configuration

Provide your **Home Assistant URL** and a **Long-Lived Access Token** during install. Create the token in Home Assistant under *Profile → Security → Long-Lived Access Tokens*.

Apps and the `appdaemon.yaml` configuration live in the `conf` volume (`/conf`). HADashboard and the admin UI are served on port **5050**. See the [docs](https://appdaemon.readthedocs.io) for writing apps.
