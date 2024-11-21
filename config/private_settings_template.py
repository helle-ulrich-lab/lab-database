# Django private settings, can be copied, edited and renamed to private_settings.py
SECRET_KEY = "abc"
ALLOWED_HOSTS = [
    "abc.xyz.com",
]  # The first item should be the publicly accessible domain
DB_NAME = "db_name"
DB_USER = "db_user"
DB_PASSWORD = "db_password"
DEBUG = False

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "email_proxy"
EMAIL_PORT = 25
EMAIL_HOST_USER = None
EMAIL_HOST_PASSWORD = None
SERVER_EMAIL_ADDRESS = "server_email_address"
SITE_ADMIN_EMAIL_ADDRESSES = [("admin_name", "admin_email_address")]

# Lab-specific settings
SITE_TITLE = "site_title"
# Abbreviation to be appended to files, e.g. HU for Helle Ulrich. Can be empty, like so ''
LAB_ABBREVIATION_FOR_FILES = ""
WORM_ALLELE_LAB_IDS = []
WORM_ALLELE_LAB_ID_DEFAULT = "worm_allele_lab_id_default"
DEFAULT_ECOLI_STRAIN_IDS = []
PLASMID_AS_ECOLI_STOCK = False

# OIDC settings, if available, otherwise set ALLOW_OIDC to False
ALLOW_OIDC = True
if ALLOW_OIDC:
    from config.oidc import discover_oidc

    try:
        discovery_info = discover_oidc(
            "https://abc.xyz.com/.well-known/openid-configuration"
        )
        OIDC_OP_AUTHORIZATION_ENDPOINT = discovery_info["authorization_endpoint"]
        OIDC_OP_TOKEN_ENDPOINT = discovery_info["token_endpoint"]
        OIDC_OP_USER_ENDPOINT = discovery_info["userinfo_endpoint"]
        OIDC_OP_JWKS_ENDPOINT = discovery_info["jwks_uri"]
    except:
        OIDC_OP_JWKS_ENDPOINT = "oidc_op_jwks_endpoint"
        OIDC_OP_AUTHORIZATION_ENDPOINT = "oidc_op_authorization_endpoint"
        OIDC_OP_TOKEN_ENDPOINT = "oidc_op_token_endpoint"
        OIDC_OP_USER_ENDPOINT = "oidc_op_user_endpoint"

    OIDC_PROVIDER_NAME = "oidc_provider_name"
    OIDC_RP_CLIENT_ID = "oidc_rp_client_id"
    OIDC_RP_CLIENT_SECRET = "oidc_rp_client_secret"
    OIDC_RP_SIGN_ALGO = "oidc_rp_sign_algo"
    OIDC_RP_SCOPES = "openid email name groups"
    OIDC_UPN_FIELD_NAME = "upn"
    OIDC_ALLOWED_GROUPS = []
    OIDC_ALLOWED_USER_UPNS = []  # all lowercase!

# Others
MS_TEAMS_WEBHOOK = "ms_teams_webhook"
ORDER_EMAIL_ADDRESSES = ["order_email_address"]
HOMEPAGE_DOCS_URL = "homepage_docs_url"
