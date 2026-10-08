"""Optional dedicated-staging SDK verification; never uses production credentials."""

import os
import unittest
import uuid

from cryptography.fernet import Fernet
from workos import WorkOSClient
from workos.session import seal_session_from_auth_response
from workos.user_management import PasswordPlaintext


@unittest.skipUnless(
    os.getenv("RUN_WORKOS_LIVE") == "1", "Dedicated WorkOS staging check not enabled"
)
class WorkOSLiveTest(unittest.TestCase):
    def test_real_staging_session(self):
        key = os.environ["WORKOS_TEST_API_KEY"]
        client_id = os.environ["WORKOS_TEST_CLIENT_ID"]
        self.assertTrue(key.startswith("sk_test_"))
        client = WorkOSClient(
            api_key=key,
            client_id=client_id,
            jwt_issuer=[
                "https://api.workos.com",
                "https://api.workos.com/user_management/" + client_id,
            ],
        )
        user = None
        password = uuid.uuid4().hex + "A1!"
        try:
            user = client.user_management.create_user(
                email="pii-ci-" + uuid.uuid4().hex + "@example.org",
                password=PasswordPlaintext(password),
                email_verified=True,
            )
            auth = client.user_management.authenticate_with_password(
                email=user.email, password=password
            )
            secret = Fernet.generate_key().decode()
            sealed = seal_session_from_auth_response(
                access_token=auth.access_token,
                refresh_token=auth.refresh_token,
                user=auth.user.to_dict(),
                cookie_password=secret,
            )
            result = client.user_management.load_sealed_session(
                session_data=sealed, cookie_password=secret
            ).authenticate()
            self.assertTrue(result.authenticated)
            self.assertEqual(result.user["id"], user.id)
            from app.auth.workos import WorkOSGateway
            from app.config import Settings

            gateway = WorkOSGateway(
                Settings(
                    workos_api_key=key,
                    workos_client_id=client_id,
                    workos_cookie_password=secret,
                )
            )
            verified = gateway.authenticate(sealed)
            self.assertEqual(verified.user["id"], user.id)
            self.assertEqual(
                client.user_management.get_user(id=user.id).email, user.email
            )
            client.user_management.revoke_session(session_id=result.session_id)
            from app.schemas.common import ApiError

            with self.assertRaises(ApiError):
                gateway.authenticate(sealed)
        finally:
            if user:
                client.user_management.delete_user(id=user.id)
