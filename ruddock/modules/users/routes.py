import time
import httplib
import flask
import sqlalchemy

from ruddock import auth_utils
from ruddock.decorators import login_required
from ruddock.modules.users import blueprint, helpers
from ruddock.resources import Permissions

@blueprint.route('/list', defaults={'search_type': 'all'})
@blueprint.route('/list/<search_type>')
@login_required()
def show_memberlist(search_type):
  """
  Displays the member list. Optionally filters for only current students
  or only alumni.
  """
  # If search_type is not a valid value (someone is messing with the URL),
  # abort the request.
  if search_type not in ['all', 'current', 'alumni']:
    flask.abort(httplib.NOT_FOUND)

  memberlist = helpers.get_memberlist(search_type)
  return flask.render_template(
      'memberlist.html',
      memberlist=memberlist,
      search_type=search_type)

@blueprint.route('/view/<user_id>')
@login_required()
def view_member(user_id):
  """Procedure to show a member's profile and membership details."""
  member_info = helpers.get_member_info(user_id)
  offices = helpers.get_office_info(user_id)

  # member_info will return None if the user_id was invalid
  if member_info is not None:
    return flask.render_template(
        'view_user.html',
        info=member_info,
        offices=offices,
        strftime=time.strftime,
        edit_permission=auth_utils.check_permission(Permissions.USERS),
        user_id=user_id)
  flask.abort(httplib.NOT_FOUND)

@blueprint.route('/manage/<user_id>', methods=['GET', 'POST'])
@login_required(Permissions.USERS)
def manage_member(user_id):
  """Procedure to edit a member in the database if the user browsing the
  website has the permissions necessary to edit users (USERS or ADMIN)."""
  member_info = helpers.get_member_info(user_id)

  if member_info is not None:
    if flask.request.method == 'GET':
      return flask.render_template(
          'manage_member.html',
          user_id=user_id,
          info=member_info)
    elif flask.request.method == 'POST':
      if 'remove' in flask.request.form:
        if helpers.remove_member(user_id):
          flask.flash('Success!')
        else:
          flask.flash('An error occurred trying to perform your operation. '
                      'Please contact an IMSS Rep!')
      elif 'edit' in flask.request.form:
        success = True

        # Use dict.items() instead in Python 3.
        for key, value in flask.request.form.iteritems():
          # Check that the user wants to change the value, check that this is a
          # part of the form we care about, and check that the column name
          # is safe, respectively. Checking that the key is part of the result
          # of member_info works since SQLAlchemy's RowProxy behaves like
          # an ordered dictionary and it will always give us all the column
          # names hard-coded in get_member_info as keys.
          if value != '' and key != 'edit' and key in member_info:
            if not helpers.edit_member_column(user_id, key, value):
              success = False
        if success:
          flask.flash('Success!')
        else:
          flask.flash('An error occurred trying to perform your operation. '
                      'Please contact an IMSS Rep!')
      return flask.redirect(flask.url_for('users.view_member', user_id=user_id))
  flask.abort(httplib.NOT_FOUND)
