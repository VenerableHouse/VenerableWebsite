import time
import httplib
import flask
import sqlalchemy
import sys

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

@blueprint.route('/view/<username>')
@login_required()
def view_profile(username):
  """Procedure to show a member's profile and membership details."""
  if username is not None:
    user_info = helpers.get_user_info(username)
    offices = helpers.get_office_info(username)

    if user_info is not None:
      return flask.render_template('view_user.html',
          info=user_info,
          offices=offices,
          strftime=time.strftime,
          edit_permission=auth_utils.check_permission(Permissions.USERS),
          user_id=helpers.get_user_id_from_username(username))
  flask.abort(httplib.NOT_FOUND)

@blueprint.route('/view_member/<user_id>')
@login_required()
def view_member(user_id):
  """Procedure to show a member's profile and membership details if they have
  no user account on the website."""
  member_info = helpers.get_member_info(user_id)
  if member_info is not None:
    return flask.render_template(
        'view_user.html',
        info=member_info,
        # No user account means we can't call helpers.get_office_info().
        # Hopefully, all officers have an account, although I still think
        # this is something worth changing.
        offices=[],
        strftime=time.strftime,
        edit_permission=auth_utils.check_permission(Permissions.USERS),
        user_id=user_id)
  else:
    flask.abort(httplib.NOT_FOUND)

@blueprint.route('/manage_member/user_id=<user_id>', methods=['GET', 'POST'])
@login_required(Permissions.USERS)
def manage_member(user_id):
  """Procedure to edit a member in the database if the user browsing the
  website has the permissions necessary to edit users (USERS or ADMIN)."""
  member_info = helpers.get_member_info(user_id)
  if flask.request.method == 'GET':
    if user_id is not None:
      return flask.render_template(
          'manage_member.html',
          user_id=user_id,
          info=member_info)
  else: # POST request, so they're submitting a form to edit/remove a user.
    if 'remove' in flask.request.form:
      if helpers.remove_member(user_id):
        flask.flash('Success!')
      else:
        flask.flash('An error occurred trying to perform your operation. '
                    'Please contact an IMSS Rep!')
    elif 'edit' in flask.request.form:
      # Everything comes back from the web page as a unicode string, but
      # when we input the database query, some of these need to be passed
      # as numbers instead. Note that user_id is stored in the database as
      # an int as well, but it's not part of the dictionary, so we just cast
      # it manually when we call helpers.edit_member_column.
      stored_as_int = ('member_type', 'msc', 'room_number')
      success = True

      # use dict.items() instead in Python 3
      for key, value in flask.request.form.iteritems():
        if value != '' and key != 'edit':
          if key in stored_as_int:
            value = int(value)
          if not helpers.edit_member_column(int(user_id), key, value):
            success = False
      if success:
        flask.flash('Success!')
      else:
        flask.flash('An error occurred trying to perform your operation. '
                    'Please contact an IMSS Rep!')
    return show_memberlist('all')
  flask.abort(httplib.NOT_FOUND)
