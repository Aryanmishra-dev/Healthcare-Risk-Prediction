import hashlib
import hmac
import secrets
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class WebhookSecurityService:
    @staticmethod
    def generate_secret() -> str:
        return secrets.token_hex(32)

    @staticmethod
    def sign_payload(payload: bytes, secret: str) -> str:
        return hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_signature(payload: bytes, secret: str, signature: str) -> bool:
        expected = WebhookSecurityService.sign_payload(payload, secret)
        return hmac.compare_digest(expected, signature)

    @staticmethod
    async def rotate_secret(
        db: AsyncSession, webhook_id: UUID, tenant_id: UUID
    ) -> Optional[str]:
        from backend.app.services.webhook_service import WebhookService

        webhook = await WebhookService.get_webhook(db, webhook_id, tenant_id)
        if not webhook:
            return None
        new_secret = WebhookSecurityService.generate_secret()
        webhook.secret = new_secret
        await db.commit()
        return new_secret


webhook_security_service = WebhookSecurityService()
