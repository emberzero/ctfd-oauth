from typing import Dict, List, Optional

from CTFd.models import db

from .models import OAUTHConfig


class DBUtils:
    """Database utility class for OAuth configuration management."""

    DEFAULT_CONFIG = [
        {"key": "oauth_plugin_enabled", "value": "off"},
        {"key": "oauth_client_id", "value": ""},
        {"key": "oauth_client_secret", "value": ""},
        {"key": "oauth_authorization_endpoint", "value": ""},
        {"key": "oauth_token_endpoint", "value": ""},
        {"key": "oauth_userinfo_url", "value": ""},
        {"key": "oauth_profile_url", "value": ""},
        {"key": "oauth_logout_url", "value": ""},
        {"key": "oauth_scope", "value": ""},
        {"key": "oauth_admin_group", "value": "CTFd Admins"},
        {"key": "oauth_sync_teams", "value": "off"},
        {"key": "oauth_enable_pkce", "value": "off"},
        # OIDC Discovery
        {"key": "oauth_discovery_url", "value": ""},
        {"key": "oauth_issuer", "value": ""},
        # Claim mappings (for non-standard claim names)
        {"key": "oauth_claim_preferred_username", "value": "preferred_username"},
        {"key": "oauth_claim_email", "value": "email"},
        {"key": "oauth_claim_affiliation", "value": "affiliation"},
        {"key": "oauth_claim_sub", "value": "sub"},
        # Identity linking
        {"key": "oauth_link_existing_by_email", "value": "on"},
    ]

    @staticmethod
    def get(key: str) -> Optional[OAUTHConfig]:
        """Get a single OAuth configuration by key."""
        return OAUTHConfig.query.filter_by(key=key).first()

    @staticmethod
    def get_config() -> Dict[str, str]:
        """Get all OAuth configuration as a dictionary."""
        configs = OAUTHConfig.query.all()
        result = {}

        for c in configs:
            result[str(c.key)] = str(c.value)

        return result

    @staticmethod
    def save_config(config: List[tuple[str, str]]) -> None:
        """Save OAuth configuration from a list of key-value tuples."""
        for key, value in config:
            record = (
                db.session.query(OAUTHConfig)
                .filter(OAUTHConfig.key == key)
                .one_or_none()
            )

            if record:
                record.value = value
            else:
                new_config = OAUTHConfig(key=key, value=value)
                db.session.add(new_config)

        db.session.commit()
        db.session.close()

    @staticmethod
    def load_default() -> None:
        """Load default configuration values for keys that don't exist."""
        for config_item in DBUtils.DEFAULT_CONFIG:
            existing = DBUtils.get(config_item["key"])
            if not existing:
                new_config = OAUTHConfig(
                    key=config_item["key"], value=config_item["value"]
                )
                db.session.add(new_config)

        db.session.commit()

    @staticmethod
    def validate_config() -> tuple[bool, List[str]]:
        """
        Validate OAuth configuration.

        Returns:
            tuple: (is_valid, list_of_errors)
        """
        config = DBUtils.get_config()
        errors = []

        if config.get("oauth_plugin_enabled") != "on":
            return True, []

        # Check required fields
        required_fields = {
            "oauth_client_id": "Client ID",
            "oauth_client_secret": "Client Secret",
        }

        # Check if using OIDC discovery or manual configuration
        if config.get("oauth_discovery_url"):
            # OIDC discovery mode
            if not config.get("oauth_discovery_url").startswith(
                ("http://", "https://")
            ):
                errors.append("Discovery URL must be a valid HTTP(S) URL")
        else:
            # Manual configuration mode
            required_fields.update(
                {
                    "oauth_authorization_endpoint": "Authorization Endpoint",
                    "oauth_token_endpoint": "Token Endpoint",
                    "oauth_userinfo_url": "UserInfo URL",
                }
            )

        for field, label in required_fields.items():
            if not config.get(field):
                errors.append(f"{label} is required")

        # Validate URLs
        url_fields = [
            "oauth_authorization_endpoint",
            "oauth_token_endpoint",
            "oauth_userinfo_url",
            "oauth_profile_url",
            "oauth_logout_url",
        ]

        for field in url_fields:
            value = config.get(field)
            if value and not value.startswith(("http://", "https://")):
                field_name = field.replace("oauth_", "").replace("_", " ").title()
                errors.append(f"{field_name} must be a valid HTTP(S) URL")

        return len(errors) == 0, errors

    @staticmethod
    def discover_oidc_endpoints(discovery_url: str) -> Optional[Dict[str, str]]:
        """
        Discover OAuth endpoints using OIDC discovery.

        Args:
            discovery_url: The OIDC discovery URL (e.g., https://idp.example.com/.well-known/openid-configuration)

        Returns:
            Dictionary with discovered endpoints or None on failure
        """
        import requests

        try:
            response = requests.get(discovery_url, timeout=10)
            if response.status_code != 200:
                return None

            discovery_doc = response.json()

            return {
                "oauth_authorization_endpoint": discovery_doc.get(
                    "authorization_endpoint", ""
                ),
                "oauth_token_endpoint": discovery_doc.get("token_endpoint", ""),
                "oauth_userinfo_url": discovery_doc.get("userinfo_endpoint", ""),
                "oauth_logout_url": discovery_doc.get("end_session_endpoint", ""),
                "oauth_issuer": discovery_doc.get("issuer", ""),
            }

        except Exception:
            return None
