from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import Group
from config.private_settings import OIDC_ALLOWED_GROUPS, SITE_TITLE, SITE_ADMIN_EMAIL_ADDRESSES, OIDC_UPN_FIELD_NAME
from config.settings import ALLOWED_HOSTS
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.urls import reverse
from inspect import cleandoc


class MyOIDCAB(OIDCAuthenticationBackend):

    def verify_claims(self, claims):
        """Verify the provided claims to decide if authentication should be allowed.
           Check that a user is part of one of the allowed OIDC groups.
        """ 

        # Check that the user is part of one of the allowed OIDC groups
        if OIDC_ALLOWED_GROUPS:
            groups = claims.get('role', [])
            is_allowed = any(g in groups for g in OIDC_ALLOWED_GROUPS)
            if not is_allowed:
                return False

        return super(MyOIDCAB, self).verify_claims(claims)
    
    def filter_users_by_claims(self, claims):

        upn = claims.get(OIDC_UPN_FIELD_NAME)
        sub = claims.get('sub')

        # If a unique identifier (= sub) is available use it to try getting the User
        # sub should match the oidc_identifier field for labuser
        if sub:
            users = self.UserModel.objects.filter(labuser__oidc_identifier=sub)
            if users:
                return users

        # Otherwise try with upn
        if upn:
            try:
                users = self.UserModel.objects.filter(username=upn.split('@')[0].lower())
                if len(users) == 0:
                    raise Exception
                return users
            except:
                #If everything fails, try the regular filter_users_by_claims
                return super(MyOIDCAB, self).filter_users_by_claims(claims)
        
        return self.UserModel.objects.none()

    def send_email_new_user(self, user):

        """Send an email to the lab managers and the site admin when a new user is created
        automatically via the OIDC backend"""

        # URL for the change page of the newly created users
        user_admin_change_url = reverse('admin:auth_user_change', args=(user.id,))
        message = f"""Dear lab manager(s),

                    A new user was just automatically created.
                    
                    Username: {user.username}
                    First name: {user.first_name}
                    Last name: {user.last_name}
                    Email address: {user.email}
                    
                    You can amend this user's properties at https://{ALLOWED_HOSTS[0]}{user_admin_change_url}.

                    Regards,
                    The {SITE_TITLE}

                    """
        
        # Recipient list, all lab managers plus the site admin
        recipients = User.objects.filter(is_active=True, is_superuser=False, labuser__is_principal_investigator=False, groups__name='Lab manager').values_list('first_name', 'email')
        recipients = list(recipients) + SITE_ADMIN_EMAIL_ADDRESSES
        
        send_mail("A new user was just automatically created", cleandoc(message), None, [e[1] for e in recipients], fail_silently=True,)

    def create_user(self, claims):
        """Return object for a newly created user account."""

        # Get relevant claims, if available
        email = claims.get('email', '')
        first_name = claims.get('given_name', '')
        last_name = claims.get('family_name', '')
        sub = claims.get('sub')

        # Create username
        username = self.get_username(claims)
        
        # Create user and update the corresponding labuser's identifier
        # with the value of sub
        user = self.UserModel.objects.create_user(username=username,
                                                  email=email,
                                                  first_name=first_name,
                                                  last_name=last_name
                                                  )
        # Activate user, by default is_active is set to False via a signal
        user.is_active = True
        # Do not allow user to reset password
        user.set_unusable_password()
        user.save()

        labuser = user.labuser
        labuser.oidc_identifier = sub if sub else None
        labuser.save()

        # A user must have at least one group. Therefore assign 
        # the group with the stricest permissions, guest, to the user
        guest_group = Group.objects.filter(name='Guest')
        user.groups.add(*guest_group)

        self.send_email_new_user(user)

        return user

    def update_user(self, user, claims):
        """Update existing user with new claims, if necessary save, and return user"""

        # Get relevant claims, if available
        email = claims.get('email', '')
        first_name = claims.get('given_name', '')
        last_name = claims.get('family_name', '')
        sub = claims.get('sub')
        
        # Update fields
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.set_unusable_password() # Set password to unusable, just in case
        user.save()

        if not user.labuser.oidc_identifier and sub:
            labuser = user.labuser
            labuser.oidc_identifier = sub
            labuser.save()

        return user

    def get_username(self, claims):
        """Generate username based on claims."""
        
        # Get username from upn => e.g. 'username@Uni-Mainz.De', default to regular
        # behaviour when upn is not available
        upn = claims.get(OIDC_UPN_FIELD_NAME)
        username = upn.split('@')[0].lower()
        if username:
            return username
        
        return super(MyOIDCAB, self).get_username(claims)