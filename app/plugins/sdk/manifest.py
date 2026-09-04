"""Plugin manifest constants and validation."""

REQUIRED_FIELDS = ("name", "version", "author", "description", "permissions")

ALL_PERMISSIONS = (
    "read_faq",
    "read_company_profile",
    "read_conversations",
    "generate_reports",
    "access_inventory",
)


def validate_manifest_fields(manifest: dict) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in manifest or manifest[f] is None]
    if missing:
        raise ValueError(f"Manifest missing required fields: {', '.join(missing)}")

    if not isinstance(manifest.get("permissions"), list):
        raise ValueError("Manifest permissions must be a list.")

    for perm in manifest["permissions"]:
        if perm not in ALL_PERMISSIONS:
            raise ValueError(f"Invalid permission: {perm}")
