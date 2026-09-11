"""Production startup security validation tests."""
import os
import unittest
from unittest.mock import patch
from app.core.config import validate_production_config
from app.infrastructure.database import config as database_config

class ProductionSecurityTests(unittest.TestCase):
    def secure_env(self):
        return {"AURA_ENV":"production","SECRET_KEY":"s"*40,
                "PAYMENT_WEBHOOK_SECRET":"w"*40,"AI_METRICS_BEARER_TOKEN":"m"*40,
                "CLOUD_ENCRYPTION_KEY":"e"*44,
                "DB_BACKEND":"postgres","DATABASE_URL":"postgresql://aura:strong-password@database:5432/aura",
                "REDIS_ENABLED":"true","REDIS_URL":"redis://:strong-password@redis:6379/0",
                "MOCK_PAYMENTS_ENABLED":"false","PAYMENT_WEBHOOK_PROVIDER":"paymongo",
                "ALLOWED_HOSTS":"chatbot.example.com",
                "CORS_ALLOWED_ORIGINS":"https://chatbot.example.com","GEMINI_API_KEY":"server-key"}
    def test_secure_production_configuration_passes(self):
        with patch.dict(os.environ,self.secure_env(),clear=True): validate_production_config()
    def test_placeholder_secrets_fail_closed(self):
        env=self.secure_env(); env["SECRET_KEY"]="change-me"
        with patch.dict(os.environ,env,clear=True), self.assertRaises(RuntimeError): validate_production_config()
    def test_non_https_cors_fails_closed(self):
        env=self.secure_env(); env["CORS_ALLOWED_ORIGINS"]="http://chatbot.example.com"
        with patch.dict(os.environ,env,clear=True), self.assertRaises(RuntimeError): validate_production_config()
    def test_mock_payments_fail_closed(self):
        env=self.secure_env(); env["MOCK_PAYMENTS_ENABLED"]="true"
        with patch.dict(os.environ,env,clear=True), self.assertRaises(RuntimeError): validate_production_config()
    def test_default_database_password_fails_closed(self):
        env=self.secure_env(); env["DATABASE_URL"]="postgresql://aura:aura@database:5432/aura"
        with patch.dict(os.environ,env,clear=True), self.assertRaises(RuntimeError): validate_production_config()
    def test_postgres_sql_adaptation(self):
        with patch.object(database_config,"DB_BACKEND","postgres"), patch.object(database_config,"DATABASE_URL","postgresql://db/app"):
            sql=database_config.adapt_sql("INSERT INTO sample(id,created_at) VALUES (?,datetime('now'))")
        self.assertIn("%s",sql); self.assertIn("CURRENT_TIMESTAMP",sql)

if __name__ == "__main__": unittest.main()
