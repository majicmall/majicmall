from __future__ import annotations

import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class MegaverseIdentity(models.Model):
    """
    Stable cross-world identity for a MajicMall Megaverse account.

    This identity belongs to the account itself, not to any individual
    role such as customer, merchant, driver, or creator. Connected
    destinations may store public_id as their stable external reference.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="megaverse_identity",
    )

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} — {self.public_id}"

    class Meta:
        verbose_name = "MajicMall Megaverse Identity"
        verbose_name_plural = "MajicMall Megaverse Identities"


class MegaverseAuthorizationCode(models.Model):
    """
    Short-lived, single-use authorization for connecting a MajicMall
    Megaverse account to an approved external destination.

    Only a SHA-256 digest of the authorization code is persisted.
    The plaintext code is returned once when issued and is never stored.
    """

    identity = models.ForeignKey(
        MegaverseIdentity,
        on_delete=models.CASCADE,
        related_name="authorization_codes",
    )

    code_digest = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )

    destination = models.CharField(
        max_length=100,
        db_index=True,
    )

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def digest_code(code):
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @classmethod
    def issue(cls, *, identity, destination, lifetime_seconds=300):
        code = secrets.token_urlsafe(32)

        authorization = cls.objects.create(
            identity=identity,
            code_digest=cls.digest_code(code),
            destination=destination,
            expires_at=timezone.now()
            + timezone.timedelta(seconds=lifetime_seconds),
        )

        return authorization, code

    @classmethod
    def redeem(cls, *, code, destination):
        """
        Atomically redeem a valid authorization code.

        A code succeeds only when it:
        - exists,
        - belongs to the expected destination,
        - has not expired,
        - has not already been used,
        - belongs to an active MajicMall Megaverse identity.

        Successful redemption permanently marks the code as used.
        """

        code_digest = cls.digest_code(code)

        with transaction.atomic():
            try:
                authorization = (
                    cls.objects.select_for_update()
                    .select_related("identity")
                    .get(code_digest=code_digest)
                )
            except cls.DoesNotExist:
                return None

            if not secrets.compare_digest(
                authorization.destination,
                destination,
            ):
                return None

            if authorization.used_at is not None:
                return None

            now = timezone.now()

            if now >= authorization.expires_at:
                return None

            if not authorization.identity.is_active:
                return None

            authorization.used_at = now
            authorization.save(update_fields=["used_at"])

            return authorization.identity

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def __str__(self):
        return f"{self.destination} — {self.identity.public_id}"

    class Meta:
        verbose_name = "MajicMall Megaverse Authorization Code"
        verbose_name_plural = "MajicMall Megaverse Authorization Codes"
        indexes = [
            models.Index(
                fields=["destination", "expires_at"],
                name="meg_auth_dest_exp_idx",
            ),
        ]
