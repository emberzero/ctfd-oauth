import base64
import hashlib
import secrets
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlencode, urlparse

import requests
from CTFd.cache import clear_team_session, clear_user_session
from CTFd.models import Brackets, Teams, Users, db
from CTFd.utils.config import get_config
from CTFd.utils.helpers import error_for
from CTFd.utils.logging import log
from CTFd.utils.modes import TEAMS_MODE
from CTFd.utils.security.auth import login_user, logout_user
from flask import abort, redirect, request, session, url_for
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .db_utils import DBUtils
from .models import OAUTHUserLink

# Constants
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
ADMIN_GROUP_CONFIG_KEY = "oauth_admin_group"


def get_requests_session() -> requests.Session:
    """Create a requests session with timeout and retry logic."""
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        read=MAX_RETRIES,
        connect=MAX_RETRIES,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge."""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = (
        base64.urlsafe_b64encode(code_challenge).rstrip(b"=").decode("ascii")
    )
    return code_verifier, code_challenge


def oauth2_login() -> Any:
    """Initiate OAuth2 login flow."""
    config = DBUtils.get_config()
    endpoint = config.get("oauth_authorization_endpoint")
    client_id = config.get("oauth_client_id")

    # Validate required configuration
    if not client_id or not endpoint:
        error_for(
            endpoint="auth.login",
            message="OAuth Settings not configured. "
            "Ask your CTF administrator to configure OAuth integration.",
        )
        return redirect(url_for("auth.login"))

    # `openid` is required so the IdP returns the `sub` claim used for identity linking.
    if get_config("user_mode") == TEAMS_MODE:
        default_scope = "openid profile team"
    else:
        default_scope = "openid profile email"

    scope = config.get("oauth_scope", default_scope)

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    # Build authorization URL parameters
    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scope,
        "state": state,
        "redirect_uri": url_for("oauth2.oauth2_callback", _external=True),
    }

    # Add PKCE parameters if enabled
    if config.get("oauth_enable_pkce", "on") == "on":
        code_verifier, code_challenge = generate_pkce_pair()
        session["oauth_code_verifier"] = code_verifier
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    redirect_url = f"{endpoint}?{urlencode(params)}"
    return redirect(redirect_url)


def validate_state(state: Optional[str]) -> bool:
    """Validate OAuth state parameter."""
    if not state:
        return False

    stored_state = session.get("oauth_state")
    if not stored_state:
        return False

    return secrets.compare_digest(stored_state, state)


def exchange_code_for_token(oauth_code: str, config: Dict[str, str]) -> Optional[str]:
    """Exchange authorization code for access token."""
    url = config.get("oauth_token_endpoint")
    client_id = config.get("oauth_client_id")
    client_secret = config.get("oauth_client_secret")

    if not all([url, client_id, client_secret]):
        log(
            "logins",
            "[{date}] {ip} - OAuth configuration incomplete for token exchange",
        )
        return None

    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = {
        "code": oauth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "redirect_uri": url_for("oauth2.oauth2_callback", _external=True),
    }

    # Only include PKCE code_verifier if it was actually used
    code_verifier = session.get("oauth_code_verifier")
    if code_verifier:
        data["code_verifier"] = code_verifier

    try:
        http_session = get_requests_session()
        token_request = http_session.post(
            url, data=data, headers=headers, timeout=REQUEST_TIMEOUT
        )

        if token_request.status_code != requests.codes.ok:
            log(
                "logins",
                f"[{{date}}] {{ip}} - OAuth token request failed with status {token_request.status_code}",
            )
            # Log response body for debugging
            try:
                error_detail = token_request.text[:200]
                log(
                    "logins",
                    f"[{{date}}] {{ip}} - OAuth token error response: {error_detail}",
                )
            except:
                pass
            return None

        token_response = token_request.json()
        return token_response.get("access_token")

    except requests.exceptions.Timeout:
        log("logins", "[{date}] {ip} - OAuth token request timed out")
        return None
    except requests.exceptions.RequestException as e:
        log("logins", f"[{{date}}] {{ip}} - OAuth token request failed: {str(e)}")
        return None
    except ValueError:
        log("logins", "[{date}] {ip} - OAuth token response was not valid JSON")
        return None


def fetch_userinfo(token: str, config: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Fetch user information from OAuth provider."""
    user_url = config.get("oauth_userinfo_url")

    if not user_url:
        log("logins", "[{date}] {ip} - OAuth userinfo URL not configured")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-type": "application/json",
    }

    try:
        http_session = get_requests_session()
        response = http_session.get(
            url=user_url, headers=headers, timeout=REQUEST_TIMEOUT
        )

        if response.status_code != requests.codes.ok:
            log(
                "logins",
                f"[{{date}}] {{ip}} - OAuth userinfo request failed with status {response.status_code}",
            )
            return None

        return response.json()

    except requests.exceptions.Timeout:
        log("logins", "[{date}] {ip} - OAuth userinfo request timed out")
        return None
    except requests.exceptions.RequestException as e:
        log("logins", f"[{{date}}] {{ip}} - OAuth userinfo request failed: {str(e)}")
        return None
    except ValueError:
        log("logins", "[{date}] {ip} - OAuth userinfo response was not valid JSON")
        return None


def get_claim_value(
    api_data: Dict[str, Any], claim_name: str, default: Any = ""
) -> Any:
    """Get a claim value from OAuth userinfo with configurable mapping."""
    config = DBUtils.get_config()
    mapping_key = f"oauth_claim_{claim_name}"
    mapped_claim = config.get(mapping_key, claim_name)
    return api_data.get(mapped_claim, default)


def _resolve_issuer(config: Dict[str, str]) -> str:
    """Resolve the OIDC issuer for identity linking, with a stable fallback."""
    issuer = config.get("oauth_issuer") or ""
    if issuer:
        return issuer
    authz = config.get("oauth_authorization_endpoint") or ""
    if authz:
        parsed = urlparse(authz)
        if parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else parsed.netloc
    return "unknown"


def create_or_update_user(api_data: Dict[str, Any]) -> Optional[Users]:
    """Create a new user or update existing user from OAuth data.

    Identity is keyed on (issuer, sub) via OAUTHUserLink — email is a
    syncable attribute, not an identity key. This prevents email-collision
    account takeovers and keeps logins stable across IdP email changes.
    """
    config = DBUtils.get_config()

    user_name = get_claim_value(api_data, "preferred_username")
    user_email = get_claim_value(api_data, "email")
    user_affiliation = get_claim_value(api_data, "affiliation", "")
    sub = get_claim_value(api_data, "sub")

    if not user_name or not user_email:
        log(
            "logins",
            "[{date}] {ip} - OAuth userinfo missing required fields (username or email)",
        )
        return None

    if not sub:
        log(
            "logins",
            "[{date}] {ip} - OAuth userinfo missing 'sub' claim; refusing login",
        )
        return None

    iss = _resolve_issuer(config)

    # Get or create bracket if provided (for user mode)
    bracket_id = None
    bracket_name = api_data.get("bracket")
    if bracket_name:
        bracket = get_or_create_bracket(bracket_name, bracket_type="users")
        if bracket:
            bracket_id = bracket.id

    link = OAUTHUserLink.query.filter_by(issuer=iss, sub=sub).first()
    user: Optional[Users] = None
    link_existing_by_email = config.get("oauth_link_existing_by_email", "on") == "on"

    if link:
        user = Users.query.filter_by(id=link.user_id).first()
        if user is None:
            # FK CASCADE should have removed the link when the user was deleted,
            # but if we somehow have a dangling link, drop it and treat as new.
            db.session.delete(link)
            db.session.commit()
            link = None

    if user is None:
        candidate = Users.query.filter_by(email=user_email).first()
        if candidate is not None:
            already_linked = OAUTHUserLink.query.filter_by(
                user_id=candidate.id
            ).first()
            if already_linked:
                log(
                    "logins",
                    f"[{{date}}] {{ip}} - OAuth login rejected: email {user_email} already linked to a different sub",
                )
                return None
            if not link_existing_by_email:
                log(
                    "logins",
                    f"[{{date}}] {{ip}} - OAuth login rejected: email {user_email} already in use; email-linking disabled",
                )
                return None
            user = candidate
            db.session.add(
                OAUTHUserLink(issuer=iss, sub=sub, user_id=user.id)
            )
            log(
                "logins",
                f"[{{date}}] {{ip}} - OAuth linked existing user {user_email} to (iss={iss}, sub={sub})",
            )

    if user is None:
        # Respect the user count limit
        num_users_limit = int(get_config("num_users", default=0))
        num_users = Users.query.filter_by(banned=False, hidden=False).count()

        if num_users_limit and num_users >= num_users_limit:
            log("logins", f"[{{date}}] {{ip}} - User limit reached ({num_users_limit})")
            abort(
                403,
                description=f"Reached the maximum number of users ({num_users_limit}).",
            )

        user = Users(
            name=user_name,
            email=user_email,
            verified=True,
            affiliation=user_affiliation,
            bracket_id=bracket_id,
        )

        db.session.add(user)
        db.session.flush()
        db.session.add(
            OAUTHUserLink(issuer=iss, sub=sub, user_id=user.id)
        )
        db.session.commit()
        log("logins", f"[{{date}}] {{ip}} - New user created via OAuth: {user_email}")
    else:
        # Identity is bound to (iss, sub), so email/name/affiliation are safe to sync.
        user.name = user_name
        user.email = user_email
        user.affiliation = user_affiliation

        if bracket_id is not None and user.bracket_id != bracket_id:
            user.bracket_id = bracket_id
            log(
                "logins",
                f"[{{date}}] {{ip}} - User bracket updated via OAuth: {user_email}",
            )

        link_row = OAUTHUserLink.query.filter_by(issuer=iss, sub=sub).first()
        if link_row is not None:
            link_row.last_login_at = db.func.current_timestamp()

        db.session.commit()
        clear_user_session(user_id=user.id)
        log(
            "logins",
            f"[{{date}}] {{ip}} - Existing user updated via OAuth: {user_email}",
        )

    return user


def get_or_create_bracket(bracket_name: str, bracket_type: str = "teams") -> Optional[Brackets]:
    """Get or create a bracket by name and type."""
    if not bracket_name:
        return None

    # Look up existing bracket by name (case-insensitive) and type
    bracket = Brackets.query.filter(
        db.func.lower(Brackets.name) == bracket_name.lower(),
        Brackets.type == bracket_type
    ).first()

    if bracket is None:
        # Create new bracket
        bracket = Brackets(
            name=bracket_name,
            type=bracket_type,
            description=f"Auto-created from OAuth for {bracket_name}"
        )
        db.session.add(bracket)
        db.session.commit()
        log("logins", f"[{{date}}] {{ip}} - New {bracket_type} bracket created via OAuth: {bracket_name}")

    return bracket


def handle_team_assignment(user: Users, api_data: Dict[str, Any]) -> bool:
    """Handle team assignment in team mode."""
    if get_config("user_mode") != TEAMS_MODE:
        return True

    # Skip if user already has a team
    if user.team_id is not None:
        # Optionally sync team membership from OAuth
        config = DBUtils.get_config()
        if config.get("oauth_sync_teams") == "on":
            team_data = api_data.get("team")
            if team_data:
                team_id = team_data.get("id")
                team = Teams.query.filter_by(id=team_id).first()
                if team and team.id != user.team_id:
                    user.team_id = team.id
                    db.session.commit()

                # Also sync bracket if provided
                bracket_name = team_data.get("bracket")
                if bracket_name and team:
                    bracket = get_or_create_bracket(bracket_name)
                    if bracket and team.bracket_id != bracket.id:
                        team.bracket_id = bracket.id
                        db.session.commit()
                        clear_team_session(team_id=team.id)
        return True

    team_data = api_data.get("team")
    if not team_data:
        log("logins", "[{date}] {ip} - OAuth userinfo missing team data in team mode")
        return False

    team_id = team_data.get("id")
    team_name = team_data.get("name")

    if not team_id or not team_name:
        log("logins", "[{date}] {ip} - OAuth team data incomplete")
        return False

    team = Teams.query.filter_by(id=team_id).first()

    if team is None:
        num_teams_limit = int(get_config("num_teams", default=0))
        num_teams = Teams.query.filter_by(banned=False, hidden=False).count()

        if num_teams_limit and num_teams >= num_teams_limit:
            log("logins", f"[{{date}}] {{ip}} - Team limit reached ({num_teams_limit})")
            abort(
                403,
                description=f"Reached the maximum number of teams ({num_teams_limit}). Please join an existing team.",
            )

        # Get or create bracket if provided
        bracket_id = None
        bracket_name = team_data.get("bracket")
        if bracket_name:
            bracket = get_or_create_bracket(bracket_name)
            if bracket:
                bracket_id = bracket.id

        team = Teams(id=team_id,name=team_name, captain_id=user.id, bracket_id=bracket_id)
        db.session.add(team)
        db.session.commit()
        clear_team_session(team_id=team.id)
        log("logins", f"[{{date}}] {{ip}} - New team created via OAuth: {team_name}")

    team_size_limit = get_config("team_size", default=0)
    if team_size_limit and len(team.members) >= team_size_limit:
        plural = "" if team_size_limit == 1 else "s"
        size_error = f"Teams are limited to {team_size_limit} member{plural}."
        log(
            "logins",
            f"[{{date}}] {{ip}} - Team size limit reached for team {team_name}",
        )
        error_for(endpoint="auth.login", message=size_error)
        return False

    team.members.append(user)
    db.session.commit()
    log("logins", f"[{{date}}] {{ip}} - User {user.email} added to team {team_name}")

    return True


def handle_admin_promotion(user: Users, api_data: Dict[str, Any]) -> None:
    """Handle admin privilege promotion based on group membership."""
    config = DBUtils.get_config()
    admin_group = config.get(ADMIN_GROUP_CONFIG_KEY, "CTFd Admins")
    user_groups = api_data.get("groups", [])

    if admin_group in user_groups and user.type != "admin":
        user.type = "admin"
        user.hidden = True
        db.session.commit()
        clear_user_session(user_id=user.id)
        log(
            "logins",
            f"[{{date}}] {{ip}} - User {user.email} promoted to admin via OAuth group '{admin_group}'",
        )


def oauth2_callback() -> Any:
    """Handle OAuth2 callback after authorization."""
    config = DBUtils.get_config()
    oauth_code = request.args.get("code")
    state = request.args.get("state")

    # Validate state parameter
    if not validate_state(state):
        log("logins", "[{date}] {ip} - OAuth state validation mismatch or missing")
        error_for(
            endpoint="auth.login",
            message="OAuth state validation failed. Please try again.",
        )
        return redirect(url_for("auth.login"))

    # Clean up state from session
    session.pop("oauth_state", None)

    if not oauth_code:
        log("logins", "[{date}] {ip} - Received redirect without OAuth code")
        error_for(
            endpoint="auth.login",
            message="OAuth authorization failed. No code received.",
        )
        return redirect(url_for("auth.login"))

    # Exchange code for token
    token = exchange_code_for_token(oauth_code, config)
    if not token:
        error_for(
            endpoint="auth.login",
            message="Failed to obtain access token from OAuth provider. Please contact your administrator.",
        )
        # Redirect to challenges to avoid infinite loop (since auth.login redirects back to OAuth)
        return redirect(url_for("challenges.listing"))

    # Clean up code verifier
    session.pop("oauth_code_verifier", None)

    # Fetch user information
    api_data = fetch_userinfo(token, config)
    if not api_data:
        error_for(
            endpoint="auth.login",
            message="Failed to retrieve user information from OAuth provider. Please contact your administrator.",
        )
        return redirect(url_for("challenges.listing"))

    # Create or update user
    user = create_or_update_user(api_data)
    if not user:
        error_for(
            endpoint="auth.login",
            message="Failed to create or update user account. Please contact your administrator.",
        )
        return redirect(url_for("challenges.listing"))

    # Handle team assignment in team mode
    if not handle_team_assignment(user, api_data):
        return redirect(url_for("auth.login"))

    # Handle admin promotion
    handle_admin_promotion(user, api_data)

    # Log successful login
    log("logins", f"[{{date}}] {{ip}} - Successful OAuth login for user {user.email}")

    # Log in the user
    login_user(user)

    return redirect(url_for("challenges.listing"))


def oauth2_logout(original_logout: Optional[Callable] = None) -> Any:
    """Handle OAuth2 logout."""
    config = DBUtils.get_config()
    logout_url = config.get("oauth_logout_url")

    # Log out from CTFd
    if original_logout:
        original_logout()
    else:
        logout_user()

    # Clear OAuth session data
    session.pop("oauth_state", None)
    session.pop("oauth_code_verifier", None)

    # Redirect to OAuth provider logout if configured
    if logout_url:
        post_logout_redirect = url_for("views.static_html", _external=True)
        params = {"post_logout_redirect_uri": post_logout_redirect}
        return redirect(f"{logout_url}?{urlencode(params)}")

    return redirect(url_for("views.static_html"))
