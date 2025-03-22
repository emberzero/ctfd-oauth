import requests
from CTFd.cache import clear_team_session, clear_user_session
from CTFd.models import Teams, Users, Brackets, db
from CTFd.utils.config import get_config
from CTFd.utils.helpers import error_for
from CTFd.utils.logging import log
from CTFd.utils.modes import TEAMS_MODE
from CTFd.utils.security.auth import login_user
from flask import abort, redirect, request, session, url_for
from datetime import datetime

from .db_utils import DBUtils


def oauth2_login():
    config = DBUtils.get_config()
    endpoint = config.get("oauth_authorization_endpoint")

    if get_config("user_mode") == "teams":
        scope = "profile team"
    else:
        scope = "openid profile email"

    client_id = config.get("oauth_client_id")

    if client_id is None:
        error_for(
            endpoint="auth.login",
            message="OAuth Settings not configured. "
            "Ask your CTF administrator to configure OAUTH integration.",
        )
        return redirect(url_for("auth.login"))

    redirect_url = "{endpoint}?response_type=code&client_id={client_id}&scope={scope}&state={state}&redirect_uri={redirect_uri}".format(
        endpoint=endpoint, client_id=client_id, scope=scope, state=session["nonce"], redirect_uri=url_for("oauth2.oauth2_callback", _external=True)
    )
    return redirect(redirect_url)


def oauth2_callback():
    config = DBUtils.get_config()
    oauth_code = request.args.get("code")
    state = request.args.get("state")
    if session["nonce"] != state:
        log("logins", "[{date}] {ip} - OAuth State validation mismatch")
        error_for(endpoint="auth.login", message="OAuth State validation mismatch.")
        return redirect(url_for("auth.login"))

    if oauth_code:
        url = config.get("oauth_token_endpoint")

        client_id = config.get("oauth_client_id")
        client_secret = config.get("oauth_client_secret")
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            "code": oauth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": url_for("oauth2.oauth2_callback", _external=True), # NO FUCKING IDEA WHY AUTHENTIK NEEDS THIS
        }

        token_request = requests.post(url, data=data, headers=headers)

        if token_request.status_code == requests.codes.ok:
            token = token_request.json()["access_token"]
            user_url = config.get("oauth_userinfo_url")

            headers = {
                "Authorization": "Bearer " + str(token),
                "Content-type": "application/json",
            }

        
            api_data = requests.get(url=user_url, headers=headers).json()

            user_name = api_data["preferred_username"]
            user_email = api_data["email"]
            user_groups = api_data.get("groups", [])
            user_affiliation = api_data.get("affiliation", "")

            user = Users.query.filter_by(email=user_email).first()
            if user is None:
                # Respect the user count limit
                num_users_limit = int(get_config("num_users", default=0))
                num_users = Users.query.filter_by(banned=False, hidden=False).count()
                if num_users_limit and num_users >= num_users_limit:
                    abort(
                        403,
                        description=f"Reached the maximum number of users ({num_users_limit}).",
                    )

                user = Users(
                    name=user_name,
                    email=user_email,
                    verified=True,
                    affiliation=user_affiliation,
                )

                db.session.add(user)
                db.session.commit()
            else:
                user.name = user_name
                user.affiliation = user_affiliation
                user.email = user_email
                db.session.commit()
                clear_user_session(user_id=user.id)

            if get_config("user_mode") == TEAMS_MODE and user.team_id is None:
                team_id = api_data["team"]["id"]
                team_name = api_data["team"]["name"]

                team = Teams.query.filter_by(oauth_id=team_id).first()
                if team is None:
                    num_teams_limit = int(get_config("num_teams", default=0))
                    num_teams = Teams.query.filter_by(
                        banned=False, hidden=False
                    ).count()
                    if num_teams_limit and num_teams >= num_teams_limit:
                        abort(
                            403,
                            description=f"Reached the maximum number of teams ({num_teams_limit}). Please join an existing team.",
                        )

                    team = Teams(name=team_name, oauth_id=team_id, captain_id=user.id)
                    db.session.add(team)
                    db.session.commit()
                    clear_team_session(team_id=team.id)

                team_size_limit = get_config("team_size", default=0)
                if team_size_limit and len(team.members) >= team_size_limit:
                    plural = "" if team_size_limit == 1 else "s"
                    size_error = "Teams are limited to {limit} member{plural}.".format(
                        limit=team_size_limit, plural=plural
                    )
                    error_for(endpoint="auth.login", message=size_error)
                    return redirect(url_for("auth.login"))

                team.members.append(user)
                db.session.commit()

            if "CLA Admins" in user_groups and user.type != "admin":
                user.type = "admin"
                user.hidden = True
                db.session.commit()
                clear_user_session(user_id=user.id)
                
            login_user(user)

            return redirect(url_for("views.static_html"))
        else:
            log("logins", "[{date}] {ip} - OAuth token retrieval failure")
            error_for(endpoint="auth.login", message="OAuth token retrieval failure.")
            return redirect(url_for("auth.login"))
    else:
        log("logins", "[{date}] {ip} - Received redirect without OAuth code")
        error_for(
            endpoint="auth.login", message="Received redirect without OAuth code."
        )
        return redirect(url_for("auth.login"))
