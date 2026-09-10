# Compose YAML validation

Apps may supply exactly one `docker-compose.json` or `docker-compose.yml`.
Legacy JSON retains the existing vendored schema and environment-array contract.
Modern YAML uses native Compose keys and `x-runtipi.schema_version: 2`, with one
main service identified by `x-runtipi.is_main` and `internal_port`.

`apps/compose-yaml-schema.json` was generated using
`dynamicComposeSchemaYaml.toJsonSchema({})` from Runtipi v4.10.1 commit
`5734817389df55aafb9afd571e42e12ab7e647e0`, file
`packages/common/src/schemas/compose-yaml.ts`, with arktype 2.1.29.
The upstream common package declares the MIT license. Source:
https://github.com/runtipi/runtipi/blob/5734817389df55aafb9afd571e42e12ab7e647e0/packages/common/src/schemas/compose-yaml.ts

Ajv 2020 validates the generated YAML schema; the existing Ajv validator still
handles legacy JSON. YAML parsing rejects duplicate keys, and source selection
rejects ambiguous JSON/YAML pairs. The upstream schema intentionally allows native
Compose options; it does not validate every Docker option. Run Docker Compose
configuration validation and the exact Runtipi generator for deployment changes.

For ERPNext's migration, the unmodified 4.10.1 converter/generator and Docker
Compose proved identical resolved configuration to the already tested legacy plus
runtime-assets override for private, proxy and open-port configurations, except
for the new release image tag. No host volume, routing, command, health check,
dependency or database/cache configuration changed in the schema migration.

Renovate retains JSON discovery and gains YAML `image:` discovery. Its existing
post-update script resolves `config.json` from the package directory for either
filename. Database and Redis exclusions remain unchanged.
