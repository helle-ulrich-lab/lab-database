# Django-based web app for managing the lab collections and orders of the Ulrich lab @ IMB Mainz

This is a web app for managing the lab collections and 
orders of the Ulrich lab @ IMB Mainz. It is based on a heavily customised Django admin site.

If you want to use this app as is, you will need to

* Set up a SnapGene server (free for academic use, see <https://www.snapgene.com/academics/snapgene-server/>)
* Set up a [plasmid viewer](https://github.com/helle-ulrich-lab/ove-plasmid-viewer) based on [TeselaGen's openVectorEditor](https://github.com/TeselaGen/openVectorEditor)
* Include a file called private_settings.py in the config folder that contains the following variables (amend as appropriate!)

```python
# /config/private_settings.py
# Django settings

SECRET_KEY = 'secret_key'
ALLOWED_HOSTS = ['host1', 'host2'] # The first item should be the publicly accessible domain 
DB_NAME = 'db_name'
DB_USER = 'db_user'
DB_PASSWORD = 'db_password'
DEBUG = False
SERVER_EMAIL_ADDRESS = 'server_email_address'
SITE_ADMIN_EMAIL_ADDRESSES = [('name', 'email')]

# The title to show in the header and some email communication
SITE_TITLE = 'site_title'

# Abbreviation to be appended to files, e.g. HU for Helle Ulrich. Can be empty, like so ''
LAB_ABBREVIATION_FOR_FILES = 'lab_abbreviation_for_files'

# OIDC settings
ALLOW_OIDC = True
OIDC_PROVIDER_NAME = 'oidc_provider_name'
OIDC_RP_CLIENT_ID = 'oidc_rp_client_id'
OIDC_RP_CLIENT_SECRET = 'oidc_rp_client_secret'
OIDC_RP_SIGN_ALGO = 'oidc_rp_sign_algo'
OIDC_OP_JWKS_ENDPOINT = "oidc_op_jwks_endpoint"
OIDC_OP_AUTHORIZATION_ENDPOINT = "oidc_op_authorization_endpoint"
OIDC_OP_TOKEN_ENDPOINT = "oidc_op_token_endpoint"
OIDC_OP_USER_ENDPOINT = "oidc_op_user_endpoint"
OIDC_RP_SCOPES = 'openid email name groups'
OIDC_ALLOWED_GROUPS = ['group1', 'group2', ]
```