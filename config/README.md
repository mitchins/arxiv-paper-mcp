# Config Mount

The stock compose file mounts this directory into the container at `/config`.
You can leave it empty unless you want to override runtime config.

Useful persisted files:

- `.env`
- `jargon_glossary.json`

The published image already includes the default `jargon_glossary.json`, so the
common Docker path needs no copy step.

Example:

```bash
export ARXIV_CONFIG_HOST_PATH=$PWD/config
cp .env.example config/.env
# Optional: cp jargon_glossary.json config/jargon_glossary.json
```
