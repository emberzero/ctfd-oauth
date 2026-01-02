from CTFd.models import db


class OAUTHConfig(db.Model):
    """OAuth configuration key-value store."""

    key = db.Column(db.String(length=128), primary_key=True)
    value = db.Column(db.Text)

    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value

    def __repr__(self) -> str:
        return f"<OAUTHConfig {self.key}={self.value}>"
