# Pangolin Connector

Newt connects local services to an existing Pangolin deployment using an outbound
tunnel. Manage the site and its resources from the Pangolin dashboard.

1. Create a site in Pangolin and copy its Newt endpoint, ID, and secret.
2. Enter those values in Runtipi and start Pangolin Connector.
3. Check that the site is online in Pangolin, then add resources using addresses
   reachable from the connector. For another Runtipi app with an open host port,
   use the Runtipi host's LAN IP and that app's published port.

The connector runs on a Docker bridge network with no published ports or local
web UI. It uses the site credentials stored in Runtipi and needs no data volume.

[Newt setup documentation](https://docs.pangolin.net/manage/sites/install-newt)
