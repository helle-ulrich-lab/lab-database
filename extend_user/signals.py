from .models import LabUser

def create_labuser(sender, instance, created, **kwargs):
    """When a new user is created, set is_staff and is_active,
    and also create a LabUser for said User"""
    
    # Do this only if a new user is created
    if created:
        
        # If the User is a superuser, automatically set is_active to True.
        # This mostly convient for when creating the very first superuser of the
        # app
        if instance.is_superuser:
            instance.is_staff = True
            instance.is_active = True

        # For any other User, is_active is set to False to prevent it to be able to
        # log in indiscriminately 
        else:
            instance.is_staff = True
            instance.is_active = False
        instance.save()
        LabUser.objects.create(user=instance)