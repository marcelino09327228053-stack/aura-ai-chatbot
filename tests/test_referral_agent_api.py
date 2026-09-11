"""HTTP authorization checks for Marketing Agent application data."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

db_path=Path(tempfile.gettempdir())/"mb_referral_agent_api.db";db_path.unlink(missing_ok=True)
private_path=Path(tempfile.gettempdir())/"mb_referral_agent_api_private"
os.environ["SQLITE_PATH"]=str(db_path);os.environ["SECRET_KEY"]="referral-api-test-secret-that-is-long-enough"
from fastapi.testclient import TestClient
from main import app
from app.referrals import repository


class ReferralAgentAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.infrastructure.database import sqlite_backend
        from app.database.connection import init_db
        if sqlite_backend._conn is not None:
            sqlite_backend._conn.close()
            sqlite_backend._conn = None
        sqlite_backend.SQLITE_PATH = str(db_path)
        db_path.unlink(missing_ok=True)
        init_db()
        cls.client=TestClient(app,raise_server_exceptions=False);cls.tokens=[]
        for index in (1,2):
            response=cls.client.post("/auth/register",json={"email":f"ref-agent-{index}@example.com","password":"test-password","company_name":f"Agent {index}"})
            cls.tokens.append(response.json()["token"])

    @classmethod
    def tearDownClass(cls):
        from app.infrastructure.database import sqlite_backend
        if sqlite_backend._conn is not None:sqlite_backend._conn.close();sqlite_backend._conn=None
        db_path.unlink(missing_ok=True)
        if private_path.exists():
            for item in private_path.iterdir():item.unlink(missing_ok=True)
            private_path.rmdir()

    def headers(self,index):return {"Authorization":f"Bearer {self.tokens[index]}"}

    def test_application_document_and_payout_fields_are_isolated(self):
        data={"full_name":"Agent One","email":"ref-agent-1@example.com","mobile_number":"09111111111",
          "address_location":"Manila","id_type":"National ID","id_reference":"","payout_method":"gcash",
          "account_holder_name":"Agent One","account_number":"09111111111","bank_name":""}
        files={"identity_document":("id.png",b"\x89PNG\r\n\x1a\nsecure-id","image/png")}
        with patch("app.referrals.service.PRIVATE_ID_DIR",private_path):
            submitted=self.client.post("/referral-agent/application",headers=self.headers(0),data=data,files=files)
            self.assertEqual(submitted.status_code,200,submitted.text)
            dashboard=self.client.get("/referral-agent/me",headers=self.headers(0)).json()
            self.assertNotIn("encrypted_account_number",dashboard["agent"]);self.assertNotIn("id_storage_name",dashboard["agent"])
            self.assertEqual(self.client.get("/referral-agent/identity-document",headers=self.headers(0)).status_code,200)
            self.assertEqual(self.client.get("/referral-agent/identity-document",headers=self.headers(1)).status_code,404)
            self.assertIn(self.client.put(f"/owner/referral-agents/{dashboard['agent']['id']}",headers=self.headers(0),json={"status":"approved"}).status_code,(404,405))

    def test_qr_activates_only_after_owner_approval(self):
        dashboard=self.client.get("/referral-agent/me",headers=self.headers(0)).json();agent_id=dashboard["agent"]["id"]
        self.assertEqual(self.client.get("/referral-agent/qr",headers=self.headers(0)).status_code,403)
        repository.set_agent_status(agent_id,"approved")
        result=self.client.get("/referral-agent/qr",headers=self.headers(0))
        self.assertEqual(result.status_code,200);self.assertEqual(result.headers["content-type"],"image/png")

    def test_z_profile_picture_is_private_and_persists(self):
        picture=b"\x89PNG\r\n\x1a\nprofile-image"
        data={"full_name":"Agent One","mobile_number":"09111111111",
              "address_location":"Manila","profile_bio":"Verified marketing partner"}
        with patch("app.referrals.service.PRIVATE_PROFILE_DIR",private_path):
            saved=self.client.post("/referral-agent/profile",headers=self.headers(0),data=data,
                files={"profile_picture":("profile.png",picture,"image/png")})
            self.assertEqual(saved.status_code,200,saved.text)
            dashboard=self.client.get("/referral-agent/me",headers=self.headers(0)).json()
            self.assertTrue(dashboard["agent"]["has_profile_photo"])
            self.assertNotIn("profile_storage_name",dashboard["agent"])
            photo=self.client.get("/referral-agent/profile-photo",headers=self.headers(0))
            self.assertEqual(photo.status_code,200);self.assertEqual(photo.content,picture)
            self.assertEqual(self.client.get("/referral-agent/profile-photo",headers=self.headers(1)).status_code,404)


if __name__=="__main__":unittest.main()
