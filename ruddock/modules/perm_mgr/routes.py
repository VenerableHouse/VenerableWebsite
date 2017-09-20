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
    pass

@blueprint.route('/edit_office/<int:office_id>')
@login_required(Permissions.PERMISSION_MANAGER)
def edit_office_permissions(office_id):
    pass

