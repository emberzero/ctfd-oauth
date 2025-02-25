import json
import os

from CTFd.utils import set_config
from flask import redirect, url_for

from .blueprint import load_bp
from .db_utils import DBUtils

PLUGIN_PATH = os.path.dirname(__file__)
CONFIG = json.load(open(f"{PLUGIN_PATH}/config.json"))


def load(app):
    app.db.create_all()  # Create all DB entities
    DBUtils.load_default()
    bp = load_bp(CONFIG["route"])  # Load blueprint
    app.register_blueprint(bp)  # Register blueprint to the Flask app

    config = DBUtils.get_config()

    set_config("registration_visibility", False)

    if config.get("oauth_plugin_enabled") == "on":
        app.view_functions["auth.login"] = lambda: redirect(
            url_for("oauth2.oauth2_login")
        )
        app.view_functions["auth.register"] = lambda: ("", 204)
        app.view_functions["auth.reset_password"] = lambda: ("", 204)
        app.view_functions["auth.confirm"] = lambda: ("", 204)
        app.view_functions["views.settings"] = lambda: redirect(
            config.get("oauth_profile_url")
        )
