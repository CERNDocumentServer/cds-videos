# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2022 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""OpenID login.

Copied from invenio-oauthclient, extended with e-groups fetching.
"""

from datetime import datetime, timedelta
from urllib.parse import quote

from flask import Blueprint, current_app, flash, g, redirect, session, url_for
from flask_login import current_user
from flask_principal import (
    AnonymousIdentity,
    RoleNeed,
    UserNeed,
    identity_changed,
    identity_loaded,
)
from invenio_db import db
from invenio_i18n import lazy_gettext as _
from invenio_oauthclient.errors import OAuthCERNRejectedAccountError, OAuthError
from invenio_oauthclient.models import RemoteAccount
from invenio_oauthclient.oauth import oauth_link_external_id, oauth_unlink_external_id
from invenio_oauthclient.proxies import current_oauthclient
from jwt import decode

cern_openid_blueprint = Blueprint("cern_openid_oauth", __name__)


@cern_openid_blueprint.route("/cern/logout")
def logout():
    """CERN logout view.
    This URL will be called when setting `SECURITY_POST_LOGOUT_VIEW = /cern/logout`,
    automatically called after `/logout` actions.
    """
    logout_url = (
        current_app.config["OAUTHCLIENT_REMOTE_APPS"]
        .get(current_app.config["REMOTE_APP_NAME"], {})
        .get("logout_url")
    )

    if not logout_url:
        raise OAuthError(
            "Invalid `logout_url` for OAuth app {}".format(
                current_app.config["REMOTE_APP_NAME"]
            )
        )

    # add redirect to SITE_URL
    redirect_url = "{}?redirect_uri={}".format(
        logout_url, quote(current_app.config["SITE_URL"])
    )
    return redirect(redirect_url, code=302)


def find_remote_by_client_id(client_id):
    """Return a remote application based with given client ID."""
    for remote in current_oauthclient.oauth.remote_apps.values():
        if remote.name == "cern_cdsvideos_openid" and remote.consumer_key == client_id:
            return remote


def fetch_extra_data(resource):
    """Return a dict with extra data retrieved from CERN OAuth."""
    person_id = resource.get("cern_person_id")
    return dict(person_id=person_id, groups=resource["groups"])


def account_roles_and_extra_data(account, resource, refresh_timedelta=None):
    """Fetch account roles and extra data from resource if necessary."""
    updated = datetime.utcnow()
    modified_since = updated
    if refresh_timedelta is not None:
        modified_since += refresh_timedelta
    modified_since = modified_since.isoformat()
    last_update = account.extra_data.get("updated", modified_since)

    if last_update > modified_since:
        return account.extra_data.get("roles", []), account.extra_data.get("groups", [])

    roles = resource["cern_roles"]
    extra_data = fetch_extra_data(resource)

    account.extra_data.update(roles=roles, updated=updated.isoformat(), **extra_data)

    # return roles and user's groups
    return (roles, extra_data["groups"])


def extend_identity(identity, roles, groups):
    """Extend identity with roles based on CERN groups."""
    provides = set(
        [UserNeed(current_user.email)]
        + [RoleNeed(name) for name in roles]
        + [RoleNeed("{0}@cern.ch".format(group)) for group in groups]
    )
    identity.provides |= provides
    key = current_app.config["OAUTHCLIENT_CERN_OPENID_SESSION_KEY"]
    session[key] = provides


def disconnect_identity(identity):
    """Disconnect identity from CERN groups."""
    session.pop("cern_resource", None)
    key = current_app.config["OAUTHCLIENT_CERN_OPENID_SESSION_KEY"]
    provides = session.pop(key, set())
    identity.provides -= provides


def get_dict_from_response(response):
    """Prepare new mapping with 'Value's grouped by 'Type'."""
    result = {}
    if getattr(response, "_resp") and response._resp.code > 400:
        return result

    for key, value in response.data.items():
        result.setdefault(key, value)

    if "groups" in result:
        # use set() to ensure unique groups
        result["groups"] = list(set(result["groups"]))
    return result


def get_resource(remote, token_response=None):
    """Query CERN Resources to get user info and roles."""
    cached_resource = session.pop("cern_resource", None)
    if cached_resource:
        return cached_resource

    url = current_app.config["OAUTHCLIENT_CERN_OPENID_USERINFO_URL"]
    response = remote.get(url)
    dict_response = get_dict_from_response(response)
    if token_response:
        decoding_params = current_app.config[
            "OAUTHCLIENT_CERN_OPENID_JWT_TOKEN_DECODE_PARAMS"
        ]
        token_data = decode(token_response["access_token"], **decoding_params)
        dict_response.update(token_data)
    session["cern_resource"] = dict_response
    return dict_response


def _account_info(remote, resp):
    """Retrieve remote account information used to find local user."""
    g.oauth_logged_in_with_remote = remote
    resource = get_resource(remote, resp)

    valid_roles = current_app.config["OAUTHCLIENT_CERN_OPENID_ALLOWED_ROLES"]
    cern_roles = resource.get("cern_roles")
    if cern_roles is None or not set(cern_roles).issubset(valid_roles):
        raise OAuthCERNRejectedAccountError(
            "User roles {0} are not one of {1}".format(cern_roles, valid_roles),
            remote,
            resp,
        )

    email = resource["email"]
    external_id = str(resource["cern_uid"])
    nice = resource["preferred_username"]
    name = resource["name"]

    return dict(
        user=dict(email=email.lower(), profile=dict(username=nice, full_name=name)),
        external_id=external_id,
        external_method="cern",
        active=True,
    )


def account_info(remote, resp):
    """Retrieve remote account information used to find local user."""
    try:
        return _account_info(remote, resp)
    except OAuthCERNRejectedAccountError as e:
        current_app.logger.warning(e.message, exc_info=True)
        flash(_("CERN account not allowed."), category="danger")
        return redirect("/")


def _disconnect(remote, *args, **kwargs):
    """Handle unlinking of remote account."""
    if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()

    account = RemoteAccount.get(
        user_id=current_user.get_id(), client_id=remote.consumer_key
    )
    external_id = account.extra_data.get("external_id")

    if external_id:
        oauth_unlink_external_id(dict(id=external_id, method="cern"))
    if account:
        with db.session.begin_nested():
            account.delete()

    disconnect_identity(g.identity)


def disconnect_handler(remote, *args, **kwargs):
    """Handle unlinking of remote account."""
    _disconnect(remote, *args, **kwargs)
    return redirect(url_for("invenio_oauthclient_settings.index"))


def account_setup(remote, token, resp):
    """Perform additional setup after user have been logged in."""
    resource = get_resource(remote, resp)

    with db.session.begin_nested():
        external_id = resource.get("cern_uid")

        # Set CERN person ID in extra_data.
        token.remote_account.extra_data = {"external_id": external_id}
        (roles, groups) = account_roles_and_extra_data(token.remote_account, resource)
        assert not isinstance(g.identity, AnonymousIdentity)
        extend_identity(g.identity, roles, groups)

        user = token.remote_account.user

        # Create user <-> external id link.
        oauth_link_external_id(user, dict(id=external_id, method="cern"))


@identity_changed.connect
def on_identity_changed(sender, identity):
    """Store roles in session whenever identity changes.

    :param identity: The user identity where information are stored.
    """
    if isinstance(identity, AnonymousIdentity):
        disconnect_identity(identity)
        return

    # This is not ideal: it assumes that the personal token used this CERN contrib
    # method to login, which might not be the case.
    # However, it is not harmful because it will simply fetch the extra roles cached
    # in the DB.
    # Changing this requires large refactoring.
    logged_in_via_token = hasattr(current_user, "login_via_oauth2") and getattr(
        current_user, "login_via_oauth2"
    )

    remote = g.get("oauth_logged_in_with_remote", None)
    logged_in_with_cern_openid = remote and remote.name == "cern_cdsvideos_openid"

    client_id = current_app.config["CERN_APP_OPENID_CREDENTIALS"]["consumer_key"]
    remote_account = RemoteAccount.get(
        user_id=current_user.get_id(), client_id=client_id
    )
    roles = []
    groups = []

    if remote_account and logged_in_via_token:
        # use cached roles, fetched from the DB
        roles.extend(remote_account.extra_data["roles"])
        groups.extend(remote_account.extra_data["groups"])
    elif remote_account and logged_in_with_cern_openid:
        # new login, fetch roles remotely
        refresh = current_app.config["OAUTHCLIENT_CERN_OPENID_REFRESH_TIMEDELTA"]
        if refresh:
            resource = get_resource(remote)
            (_roles, _groups) = account_roles_and_extra_data(
                remote_account, resource, refresh_timedelta=refresh
            )
            roles.extend(_roles)
            groups.extend(_groups)
        else:
            roles.extend(remote_account.extra_data["roles"])
            groups.extend(remote_account.extra_data["groups"])
    # must be always called, to add the user email in the roles
    extend_identity(identity, roles, groups)


@identity_loaded.connect
def on_identity_loaded(sender, identity):
    """Store roles in session whenever identity is loaded."""
    key = current_app.config["OAUTHCLIENT_CERN_OPENID_SESSION_KEY"]
    identity.provides.update(session.get(key, []))
