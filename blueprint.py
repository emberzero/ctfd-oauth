from typing import Any

from CTFd.cache import cache
from CTFd.utils.decorators import admins_only
from flask import Blueprint, render_template, request

from . import auth
from .db_utils import DBUtils

oauth_bp = Blueprint("oauth2", __name__, template_folder="templates")


def clear_oauth_cache() -> None:
    """Clear OAuth configuration cache to pick up changes immediately."""
    # Import here to avoid circular dependency
    from . import is_oauth_enabled

    try:
        cache.delete_memoized(is_oauth_enabled)
    except:
        # If memoized cache fails, try regular cache delete
        pass

    try:
        cache.delete("oauth_plugin_enabled_status")
    except:
        pass


def load_bp(plugin_route: str) -> Blueprint:
    """Load and configure the OAuth blueprint with routes."""

    @oauth_bp.route(plugin_route, methods=["GET"])
    @admins_only
    def get_config() -> str:
        """Display OAuth configuration page."""
        config = DBUtils.get_config()
        is_valid, errors = DBUtils.validate_config()

        return render_template(
            "oauth2/config.html",
            config=config,
            errors=errors if not is_valid else [],
        )

    @oauth_bp.route(plugin_route, methods=["POST"])
    @admins_only
    def update_config() -> str:
        """Update OAuth configuration."""
        config = request.form.to_dict()
        del config["nonce"]

        errors = []

        # Handle OIDC discovery if discovery URL is provided
        discovery_url = config.get("oauth_discovery_url")
        if discovery_url:
            endpoints = DBUtils.discover_oidc_endpoints(discovery_url)
            if endpoints:
                config.update(endpoints)
                errors.append(
                    "OIDC discovery successful! Endpoints have been auto-configured."
                )
            else:
                errors.append(
                    "OIDC discovery failed. Please check the discovery URL or configure endpoints manually."
                )

        DBUtils.save_config(config.items())

        # Clear cache to pick up configuration changes immediately
        clear_oauth_cache()

        # Validate the saved configuration
        is_valid, validation_errors = DBUtils.validate_config()
        if not is_valid:
            errors.extend(validation_errors)
        else:
            # Add success message if configuration is valid
            if config.get("oauth_plugin_enabled") == "on":
                errors.append(
                    "OAuth configuration saved successfully! Changes are active immediately - no restart required."
                )
            else:
                errors.append(
                    "OAuth configuration saved successfully! OAuth is currently disabled."
                )

        return render_template(
            "oauth2/config.html",
            config=DBUtils.get_config(),
            errors=errors,
        )

    @oauth_bp.route("/oauth2/login", methods=["GET"])
    def oauth2_login() -> Any:
        """Handle OAuth login initiation."""
        return auth.oauth2_login()

    @oauth_bp.route("/oauth2/callback", methods=["GET"])
    def oauth2_callback() -> Any:
        """Handle OAuth callback."""
        return auth.oauth2_callback()

    return oauth_bp
