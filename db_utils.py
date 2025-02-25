from CTFd.models import db

from .models import OAUTHConfig


class DBUtils:
    DEFAULT_CONFIG = [
        {
            "key": "oauth_plugin_enabled",
            "value": "off",
        },  # DOESN'T WORK ATM, CTFD NEEDS TO BE RESTARTED TO REFLECT CHANGES
        {"key": "oauth_client_id", "value": ""},
        {"key": "oauth_client_secret", "value": ""},
        {"key": "oauth_authorization_endpoint", "value": ""},
        {"key": "oauth_token_endpoint", "value": ""},
        {"key": "oauth_userinfo_url", "value": ""},
        {"key": "oauth_profile_url", "value": ""},
    ]

    @staticmethod
    def get(key):
        return OAUTHConfig.query.filter_by(key=key).first()

    @staticmethod
    def get_config():
        configs = OAUTHConfig.query.all()
        result = {}

        for c in configs:
            result[str(c.key)] = str(c.value)

        return result

    @staticmethod
    def save_config(config):
        for c in config:
            q = db.session.query(OAUTHConfig)
            q = q.filter(OAUTHConfig.key == c[0])
            record = q.one_or_none()

            if record:
                record.value = c[1]
                db.session.commit()
            else:
                config = OAUTHConfig(key=c[0], value=c[1])
                db.session.add(config)
                db.session.commit()
        db.session.close()

    @staticmethod
    def load_default():
        for cv in DBUtils.DEFAULT_CONFIG:
            # Query for the config setting
            k = DBUtils.get(cv["key"])
            # If its not created, create it with its default value
            if not k:
                c = OAUTHConfig(key=cv["key"], value=cv["value"])
                db.session.add(c)
        db.session.commit()
