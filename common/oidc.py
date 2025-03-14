from inspect import cleandoc

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.urls import reverse
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

User = get_user_model()
OIDC_ALLOWED_GROUPS = getattr(settings, "OIDC_ALLOWED_GROUPS", [])
OIDC_ALLOWED_USER_UPNS = getattr(settings, "OIDC_ALLOWED_USER_UPNS", [])
SITE_TITLE = getattr(settings, "SITE_TITLE", "Lab DB")
SITE_ADMIN_EMAIL_ADDRESSES = getattr(settings, "SITE_ADMIN_EMAIL_ADDRESSES", [])
OIDC_UPN_FIELD_NAME = getattr(settings, "OIDC_UPN_FIELD_NAME", "upn")
ALLOWED_HOSTS = getattr(settings, "ALLOWED_HOSTS", [])


class MyOIDCAB(OIDCAuthenticationBackend):
    def verify_claims(self, claims):
        """Verify the provided claims to decide if authentication should be allowed.
        Check that a user is part of one of the allowed OIDC groups.
        """

        # Check that the user is part of one of the allowed OIDC groups
        groups = claims.get("role", [])
        upn = claims.get(OIDC_UPN_FIELD_NAME, "").split("@")[0].lower()
        is_allowed = any(g in groups for g in OIDC_ALLOWED_GROUPS) or (
            upn in OIDC_ALLOWED_USER_UPNS
        )
        if not is_allowed:
            messages.error(
                self.request, f"Your user is not allowed to access the {SITE_TITLE}."
            )
            return False

        return super().verify_claims(claims)

    def filter_users_by_claims(self, claims):
        upn = claims.get(OIDC_UPN_FIELD_NAME)
        sub = claims.get("sub")

        # If a unique identifier (= sub) is available use it to try getting the User
        # sub should match the oidc_id field for user
        if sub:
            users = self.UserModel.objects.filter(oidc_id=sub)
            if users:
                return users

        # Otherwise try with upn
        if upn:
            try:
                users = self.UserModel.objects.filter(
                    username=upn.split("@")[0].lower()
                )
                if len(users) == 0:
                    raise Exception
                return users
            except Exception:
                # If everything fails, try the regular filter_users_by_claims
                return super().filter_users_by_claims(claims)

        return self.UserModel.objects.none()

    def send_email_new_user(self, user):
        """Send an email to the lab managers and the site admin when a new user is created
        automatically via the OIDC backend"""

        # URL for the change page of the newly created users
        user_admin_change_url = reverse("admin:common_user_change", args=(user.id,))
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
        recipients = User.objects.filter(
            is_active=True,
            is_superuser=False,
            is_pi=False,
            groups__name="Lab manager",
        ).values_list("first_name", "email")
        recipients = list(recipients) + SITE_ADMIN_EMAIL_ADDRESSES

        send_mail(
            "A new user was just automatically created",
            cleandoc(message),
            None,
            [e[1] for e in recipients],
            fail_silently=True,
        )

    def create_user(self, claims):
        """Return object for a newly created user account."""

        # Get relevant claims, if available
        email = claims.get("email", "")
        first_name = claims.get("given_name", "")
        last_name = claims.get("family_name", "")
        sub = claims.get("sub")

        # Create username
        username = self.get_username(claims)

        # Create user and update the corresponding user's identifier
        # with the value of sub
        user = self.UserModel.objects.create_user(
            username=username, email=email, first_name=first_name, last_name=last_name
        )
        # Activate user, by default is_active is set to False via a signal
        user.is_active = True
        # Do not allow user to reset password
        user.set_unusable_password()
        user.save()

        user.oidc_id = sub if sub else None
        user.save()

        # A user must have at least one group. Therefore assign
        # the group with the stricest permissions, guest, to the user
        guest_group = Group.objects.filter(name="Guest")
        user.groups.add(*guest_group)

        self.send_email_new_user(user)

        return user

    def update_user(self, user, claims):
        """Update existing user with new claims, if necessary save, and return user"""

        # Get relevant claims, if available
        email = claims.get("email", "")
        first_name = claims.get("given_name", "")
        last_name = claims.get("family_name", "")
        sub = claims.get("sub")

        # Update fields
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.set_unusable_password()  # Set password to unusable, just in case
        user.save()

        if not user.oidc_id and sub:
            user.oidc_id = sub
            user.save()

        return user

    def get_username(self, claims):
        """Generate username based on claims."""

        # Get username from upn => e.g. 'username@Uni-Mainz.De', default to regular
        # behaviour when upn is not available
        upn = claims.get(OIDC_UPN_FIELD_NAME)
        username = upn.split("@")[0].lower()
        if username:
            return username

        return super().get_username(claims)
