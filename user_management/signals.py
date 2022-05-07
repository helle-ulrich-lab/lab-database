from .models import LabUser

def create_labuser(sender, instance, created, **kwargs):
    # If a new user is created, also create a LabUser
    if created:
        LabUser.objects.create(user=instance)