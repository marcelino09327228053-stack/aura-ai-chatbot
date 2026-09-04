"""Load plugin classes from the examples directory."""

import importlib.util
from pathlib import Path

from app.plugins.runtime.validator import load_manifest_from_file

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
_loaded: dict[str, type] = {}


def load_plugin_class(plugin_key: str) -> type:
    if plugin_key in _loaded:
        return _loaded[plugin_key]

    plugin_dir = EXAMPLES_DIR / plugin_key
    plugin_file = plugin_dir / "plugin.py"
    if not plugin_file.exists():
        raise FileNotFoundError(f"Plugin code not found: {plugin_key}")

    load_manifest_from_file(plugin_key)

    spec = importlib.util.spec_from_file_location(
        f"aura_plugin_{plugin_key}",
        plugin_file,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load plugin module: {plugin_key}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    plugin_cls = getattr(module, "Plugin", None)
    if plugin_cls is None:
        raise ImportError(f"Plugin '{plugin_key}' must define a Plugin class.")

    _loaded[plugin_key] = plugin_cls
    return plugin_cls
