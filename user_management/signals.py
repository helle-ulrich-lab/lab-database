from .models import LabUser

def create_labuser(sender, instance, created, **kwargs):
    """If a new user is created, set some defaults and 
    also create a LabUser"""
    
    if created:
        instance.is_staff = True
        instance.is_active = False
        instance.save()
        LabUser.objects.create(user=instance)