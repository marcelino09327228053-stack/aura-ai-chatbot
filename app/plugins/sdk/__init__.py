"""Plugin SDK — manifest validation and base plugin class."""

from app.plugins.sdk.base import BasePlugin
from app.plugins.sdk.manifest import ALL_PERMISSIONS, validate_manifest_fields

__all__ = ["BasePlugin", "ALL_PERMISSIONS", "validate_manifest_fields"]
