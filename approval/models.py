from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

User = get_user_model()


class Approval(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    activity_type = models.CharField(
        max_length=20, choices=(("created", "created"), ("changed", "changed"))
    )
    activity_user = models.ForeignKey(User, on_delete=models.PROTECT)
    message = models.TextField(
        "message", max_length=255, help_text="Max. 255 characters", blank=True
    )
    message_date_time = models.DateTimeField(blank=True, null=True)
    edited = models.BooleanField("edited?", blank=True, default=False)
    created_date_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "approval"
        verbose_name_plural = "approvals"
