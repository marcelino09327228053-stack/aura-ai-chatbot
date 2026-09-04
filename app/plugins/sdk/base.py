"""Base plugin class for Aura plugin SDK."""


class BasePlugin:
    """All plugins must subclass this and implement execute()."""

    manifest: dict = {}

    def execute(self, context, **kwargs) -> dict:
        raise NotImplementedError("Plugin must implement execute(context, **kwargs)")
