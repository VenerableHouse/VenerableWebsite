import json
import flask

import datetime

from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.perm_mgr import blueprint, helpers

@blueprint.route('/')
@login_required(Permissions.PERMISSION_MANAGER)
def show_permissions():
  """Displays a list of permissions for current users and offices."""
  office_perms = [{"name": x["office_name"], 
                   "perms": helpers.decode_perm_string(x['permissions']),
                   "id": x["office_id"]} 
                  for x in helpers.fetch_office_permissions()]
  user_perms = [{"name": x["name"], 
                 "perms": helpers.decode_perm_string(x['permissions']),
                 "id": x["user_id"]} 
                for x in helpers.fetch_user_permissions()]
  return flask.render_template('perm_list.html', office_perms=office_perms,
      user_perms=user_perms)

@blueprint.route('/edit_user/<int:user_id>')
@login_required(Permissions.PERMISSION_MANAGER)
def edit_user_permissions(user_id):
  x = helpers.fetch_specific_user_permissions(user_id)
  user_perms = {"name": x["name"], 
                "perms": helpers.decode_perm_string_with_id(x['permissions']),
                "id": x["user_id"]} 
  all_perms = helpers.get_all_perms()
  diff_perms = [p for p in all_perms if not any(p["id"] == u["id"] for u in user_perms["perms"])]
  return flask.render_template('edit_user.html', info=user_perms,
      all_perms=diff_perms)

@blueprint.route('/edit_office/<int:office_id>')
@login_required(Permissions.PERMISSION_MANAGER)
def edit_office_permissions(office_id):
  x = helpers.fetch_specific_office_permissions(office_id)
  office_perms = {"name": x["office_name"], 
                   "perms": helpers.decode_perm_string_with_id(x['permissions']),
                   "id": x["office_id"]} 
  all_perms = helpers.get_all_perms()
  diff_perms = [p for p in all_perms if not any(p["id"] == o["id"] for o in office_perms["perms"])]
  return flask.render_template('edit_office.html', info=office_perms,
      all_perms=diff_perms)

@blueprint.route('/delete_user_perm/<int:user_id>', methods=["POST"])
@login_required(Permissions.PERMISSION_MANAGER)
def delete_user_perm(user_id):
    perm_id = flask.request.form.get("perm_id")
    helpers.delete_user_permission(user_id, perm_id)
    return flask.redirect(flask.url_for("perm_mgr.edit_user_permissions", user_id=user_id))

@blueprint.route('/delete_office_perm/<int:office_id>', methods=["POST"])
@login_required(Permissions.PERMISSION_MANAGER)
def delete_office_perm(office_id):
    perm_id = flask.request.form.get("perm_id")
    helpers.delete_office_permission(office_id, perm_id)
    return flask.redirect(flask.url_for("perm_mgr.edit_office_permissions", office_id=office_id))

@blueprint.route('/add_user_perm/<int:user_id>', methods=["POST"])
@login_required(Permissions.PERMISSION_MANAGER)
def add_user_perm(user_id):
    perm_id = flask.request.form.get("perm_id")
    helpers.insert_user_permission(user_id, perm_id)
    return flask.redirect(flask.url_for("perm_mgr.edit_user_permissions", user_id=user_id))

@blueprint.route('/add_office_perm/<int:office_id>', methods=["POST"])
@login_required(Permissions.PERMISSION_MANAGER)
def add_office_perm(office_id):
    perm_id = flask.request.form.get("perm_id")
    helpers.insert_office_permission(office_id, perm_id)
    return flask.redirect(flask.url_for("perm_mgr.edit_office_permissions", office_id=office_id))
