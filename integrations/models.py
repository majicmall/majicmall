from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


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
