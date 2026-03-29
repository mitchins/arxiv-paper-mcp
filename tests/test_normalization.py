from __future__ import annotations

import importlib
import json


def reload_normalization():
    import core.normalization as normalization

    return importlib.reload(normalization)


def test_normalize_arxiv_id_variants() -> None:
    normalization = reload_normalization()

    assert normalization.normalize_arxiv_id("arXiv:2301.12345v2") == "2301.12345v2"
    assert normalization.normalize_arxiv_id(" hep-th/9901001 ") == "hep-th/9901001"
    assert normalization.normalize_arxiv_id("not-an-id") is None


def test_normalize_query_without_jargon(monkeypatch) -> None:
    monkeypatch.delenv("ARXIV_ENABLE_JARGON_EXPANSION", raising=False)
    monkeypatch.delenv("ARXIV_JARGON_GLOSSARY", raising=False)

    normalization = reload_normalization()

    assert normalization.normalize_query("mechanistic interpretability") == '"mechanistic" AND "interpretability"'


def test_normalize_query_with_config_glossary(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    glossary_path = config_dir / "jargon_glossary.json"
    glossary_path.write_text(
        json.dumps(
            {
                "sparse autoencoder": {
                    "aliases": ["sae", "sparse autoencoders"],
                    "canonical": "sparse autoencoder",
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("ARXIV_ENABLE_JARGON_EXPANSION", "1")
    monkeypatch.delenv("ARXIV_JARGON_GLOSSARY", raising=False)
    monkeypatch.setenv("ARXIV_CONFIG_DIR", str(config_dir))

    normalization = reload_normalization()

    query = normalization.normalize_query("sae")
    assert '"sae"' in query
    assert '"sparse autoencoder"' in query
    assert '"sparse autoencoders"' in query


def test_normalize_query_falls_back_to_bundled_glossary_when_config_empty(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    monkeypatch.setenv("ARXIV_ENABLE_JARGON_EXPANSION", "1")
    monkeypatch.delenv("ARXIV_JARGON_GLOSSARY", raising=False)
    monkeypatch.setenv("ARXIV_CONFIG_DIR", str(config_dir))

    normalization = reload_normalization()

    query = normalization.normalize_query("sae")
    assert '"sae"' in query
    assert '"sparse autoencoder"' in query
    assert '"sparse autoencoders"' in query
