import time
import http.client
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
  search_filters_all = ['all', 'current', 'alumni'] + helpers.get_all_grad_years()
  if search_type not in search_filters_all:
    flask.abort(http.client.NOT_FOUND)

  memberlist = helpers.get_memberlist(search_type)
  return flask.render_template(
      'memberlist.html',
      memberlist=memberlist,
      search_type=search_type,
      search_terms=search_filters_all)

@blueprint.route('/view/<username>')
@login_required()
def view_profile(username):
  """Procedure to show a user's profile and membership details."""
  user_info = helpers.get_user_info(username)
  offices = helpers.get_office_info(username)

  if user_info is not None:
    return flask.render_template('view_user.html',
        info=user_info,
        offices=offices,
        strftime=time.strftime)
  else:
    flask.abort(http.client.NOT_FOUND)
