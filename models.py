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


class OAUTHUserLink(db.Model):
    """Binds an IdP identity (issuer + sub) to a CTFd user."""

    __tablename__ = "oauth_user_link"

    id = db.Column(db.Integer, primary_key=True)
    issuer = db.Column(db.String(length=512), nullable=False, index=True)
    sub = db.Column(db.String(length=512), nullable=False, index=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_login_at = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint("issuer", "sub", name="uq_oauth_iss_sub"),
    )

    def __repr__(self) -> str:
        return f"<OAUTHUserLink user_id={self.user_id} iss={self.issuer} sub={self.sub}>"
