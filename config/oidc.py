import requests


def discover_oidc(discovery_url: str) -> dict:
    """
    Performs OpenID Connect discovery to retrieve the provider configuration.
    Plainly stolen from https://github.com/mozilla/mozilla-django-oidc/issues/414
    """
    response = requests.get(discovery_url)
    if response.status_code != 200:
        raise ValueError("Failed to retrieve provider configuration.")

    provider_config = response.json()

    # Extract endpoint URLs from provider configuration
    return {
        "authorization_endpoint": provider_config["authorization_endpoint"],
        "token_endpoint": provider_config["token_endpoint"],
        "userinfo_endpoint": provider_config["userinfo_endpoint"],
        "jwks_uri": provider_config["jwks_uri"],
    }
