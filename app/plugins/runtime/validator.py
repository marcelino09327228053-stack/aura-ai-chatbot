"""Validate plugin manifests and plugin classes."""

import json
from pathlib import Path

from app.plugins.sdk.manifest import validate_manifest_fields

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def validate_manifest(manifest: dict) -> None:
    validate_manifest_fields(manifest)


def load_manifest_from_file(plugin_key: str) -> dict:
    path = EXAMPLES_DIR / plugin_key / "plugin.json"
    if not path.exists():
        raise FileNotFoundError(f"No plugin.json for '{plugin_key}'.")
    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)
    validate_manifest(manifest)
    return manifest
