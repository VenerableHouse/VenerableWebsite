import time
import httplib
import flask
import sqlalchemy

from ruddock import auth_utils
from ruddock.decorators import login_required
from ruddock.modules.users import blueprint, helpers

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
          strftime=time.strftime)
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
        # All officers should definitely have an account anyways.
        offices=[],
        strftime=time.strftime)
  else:
    flask.abort(httplib.NOT_FOUND)
