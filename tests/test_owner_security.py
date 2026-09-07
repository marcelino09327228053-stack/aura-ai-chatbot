"""Owner Console password, MFA, and session tests."""
import base64, os, secrets, unittest
from unittest.mock import patch
import bcrypt, jwt
from fastapi import HTTPException
from app.owner import security

class OwnerSecurityTests(unittest.TestCase):
    def env(self):
        secret=base64.b32encode(b"12345678901234567890").decode().rstrip("=")
        return {"OWNER_EMAIL":"owner@example.com","OWNER_TOTP_SECRET":secret,"OWNER_PASSWORD_HASH":bcrypt.hashpw(b"strong-password",bcrypt.gensalt()).decode(),"OWNER_CONSOLE_SECRET":"s"*40}
    def test_password_totp_and_short_session(self):
        env=self.env()
        with patch.dict(os.environ,env,clear=False), patch("app.owner.security.time.time",return_value=1700000000):
            code=security._totp(env["OWNER_TOTP_SECRET"],1700000000//30)
            security.verify_login("owner@example.com","strong-password",code)
            token=security.create_session(); payload=jwt.decode(token,env["OWNER_CONSOLE_SECRET"],algorithms=["HS256"],options={"verify_exp":False})
            self.assertEqual(payload["sub"],"owner")
            self.assertEqual(payload["exp"],1700001800)
    def test_wrong_mfa_is_rejected(self):
        with patch.dict(os.environ,self.env(),clear=False), self.assertRaises(HTTPException): security.verify_login("owner@example.com","strong-password","000000")

    def test_wrong_email_is_rejected(self):
        env=self.env()
        with patch.dict(os.environ,env,clear=False), patch("app.owner.security.time.time",return_value=1700000000):
            code=security._totp(env["OWNER_TOTP_SECRET"],1700000000//30)
            with self.assertRaises(HTTPException):
                security.verify_login("attacker@example.com","strong-password",code)

    def test_mfa_can_be_deferred_for_local_setup(self):
        env={**self.env(),"OWNER_MFA_REQUIRED":"false"}
        with patch.dict(os.environ,env,clear=False):
            security.verify_login("owner@example.com","strong-password","")

if __name__=="__main__": unittest.main()
