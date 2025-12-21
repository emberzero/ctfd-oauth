import json
import os
from functools import wraps

from CTFd.cache import cache
from CTFd.utils import set_config
from flask import Flask, g, redirect, request, url_for

from .blueprint import load_bp
from .db_utils import DBUtils

PLUGIN_PATH = os.path.dirname(__file__)
with open(f"{PLUGIN_PATH}/config.json") as config_file:
    CONFIG = json.load(config_file)

# Store original view functions
ORIGINAL_VIEWS = {}

# Cache key for OAuth enabled status
OAUTH_ENABLED_CACHE_KEY = "oauth_plugin_enabled_status"
OAUTH_CACHE_TIMEOUT = 60  # Cache for 60 seconds


@cache.memoize(timeout=OAUTH_CACHE_TIMEOUT)
def is_oauth_enabled() -> bool:
    """
    Check if OAuth is enabled and properly configured.

    Cached for performance to avoid DB queries on every request.
    Cache is automatically cleared when configuration is updated.
    """
    config = DBUtils.get_config()

    if config.get("oauth_plugin_enabled") != "on":
        return False

    # Validate required configuration
    required_fields = [
        "oauth_client_id",
        "oauth_client_secret",
        "oauth_authorization_endpoint",
        "oauth_token_endpoint",
        "oauth_userinfo_url",
    ]

    return all(config.get(field) for field in required_fields)


def oauth_route_wrapper(original_view, oauth_view):
    """Wrapper that dynamically switches between OAuth and original view."""

    @wraps(original_view)
    def wrapper(*args, **kwargs):
        if is_oauth_enabled():
            return oauth_view(*args, **kwargs)
        return original_view(*args, **kwargs)

    return wrapper


def load(app: Flask) -> None:
    """Load the OAuth plugin and configure CTFd authentication."""
    app.db.create_all()  # Create all DB entities
    DBUtils.load_default()
    bp = load_bp(CONFIG["route"])  # Load blueprint
    app.register_blueprint(bp)  # Register blueprint to the Flask app

    # Store original view functions
    ORIGINAL_VIEWS["auth.login"] = app.view_functions.get("auth.login")
    ORIGINAL_VIEWS["auth.register"] = app.view_functions.get("auth.register")
    ORIGINAL_VIEWS["auth.reset_password"] = app.view_functions.get(
        "auth.reset_password"
    )
    ORIGINAL_VIEWS["auth.confirm"] = app.view_functions.get("auth.confirm")
    ORIGINAL_VIEWS["auth.logout"] = app.view_functions.get("auth.logout")
    ORIGINAL_VIEWS["views.settings"] = app.view_functions.get("views.settings")

    # Define OAuth replacement functions
    def oauth_login_redirect():
        return redirect(url_for("oauth2.oauth2_login"))

    def oauth_disabled_endpoint():
        return ("", 204)

    def oauth_settings_redirect():
        config = DBUtils.get_config()
        profile_url = config.get("oauth_profile_url")
        if profile_url:
            return redirect(profile_url)
        # Fall back to original settings if no profile URL
        return ORIGINAL_VIEWS["views.settings"]()

    def oauth_logout_handler():
        from .auth import oauth2_logout

        return oauth2_logout(ORIGINAL_VIEWS["auth.logout"])

    # Wrap all view functions with dynamic OAuth switching
    if ORIGINAL_VIEWS.get("auth.login"):
        app.view_functions["auth.login"] = oauth_route_wrapper(
            ORIGINAL_VIEWS["auth.login"], oauth_login_redirect
        )

    if ORIGINAL_VIEWS.get("auth.register"):
        app.view_functions["auth.register"] = oauth_route_wrapper(
            ORIGINAL_VIEWS["auth.register"], oauth_disabled_endpoint
        )

    if ORIGINAL_VIEWS.get("auth.reset_password"):
        app.view_functions["auth.reset_password"] = oauth_route_wrapper(
            ORIGINAL_VIEWS["auth.reset_password"], oauth_disabled_endpoint
        )

    if ORIGINAL_VIEWS.get("auth.confirm"):
        app.view_functions["auth.confirm"] = oauth_route_wrapper(
            ORIGINAL_VIEWS["auth.confirm"], oauth_disabled_endpoint
        )

    if ORIGINAL_VIEWS.get("auth.logout"):
        app.view_functions["auth.logout"] = oauth_route_wrapper(
            ORIGINAL_VIEWS["auth.logout"], oauth_logout_handler
        )

    if ORIGINAL_VIEWS.get("views.settings"):
        app.view_functions["views.settings"] = oauth_route_wrapper(
            ORIGINAL_VIEWS["views.settings"], oauth_settings_redirect
        )

    # Update registration visibility based on initial state
    @app.before_request
    def update_registration_visibility():
        """Update registration visibility on each request based on OAuth status."""
        if is_oauth_enabled():
            set_config("registration_visibility", False)
        # Note: We don't set it back to True to avoid overwriting admin preferences
