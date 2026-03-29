# Config Mount

This directory is intended to be mounted into the container at `/config`.

Useful persisted files:

- `.env`
- `jargon_glossary.json`

Example:

```bash
export ARXIV_CONFIG_HOST_PATH=$PWD/config
cp .env.example config/.env
cp jargon_glossary.json config/jargon_glossary.json
```
