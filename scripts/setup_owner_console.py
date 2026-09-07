"""Generate Owner Console secrets without printing the plaintext password."""
import base64, getpass, secrets
import bcrypt
from cryptography.fernet import Fernet

password=getpass.getpass("New Owner Console password: ")
confirm=getpass.getpass("Confirm password: ")
if password!=confirm or len(password)<12: raise SystemExit("Passwords must match and contain at least 12 characters.")
print("OWNER_PASSWORD_HASH="+bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode())
print("OWNER_CONSOLE_SECRET="+secrets.token_urlsafe(48))
print("OWNER_TOTP_SECRET="+base64.b32encode(secrets.token_bytes(20)).decode().rstrip("="))
print("CLOUD_ENCRYPTION_KEY="+Fernet.generate_key().decode())
print("Store these values in the server secret manager. Add the TOTP secret manually to your authenticator app.")
