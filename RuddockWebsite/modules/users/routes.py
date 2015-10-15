import time
import httplib
import flask
import sqlalchemy

from RuddockWebsite import auth_utils
from RuddockWebsite.decorators import login_required
from RuddockWebsite.modules.users import blueprint, helpers

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
def show_user_profile(username):
  """ Procedure to show a user's profile and membership details. """
  user_info = helpers.get_user_info(username)
  offices = helpers.get_office_info(username)
  has_edit_permission = helpers.check_edit_permission(username)

  if user_info is not None:
    return flask.render_template('view_user.html',
        info=user_info,
        offices=list(offices),
        strftime=time.strftime,
        has_edit_permission=has_edit_permission)
  else:
    flask.abort(httplib.NOT_FOUND)

@blueprint.route('/edit/<username>', methods=['GET', 'POST'])
@login_required()
def change_user_settings(username):
  """ Show a page for users to edit their information. """
  # To visit this page, they must be either modifying their own page or be an
  # admin with appropriate permissions.
  if not helpers.check_edit_permission(username):
    flask.abort(httplib.FORBIDDEN)

  params = {}
  tags = ['nickname', 'usenickname', 'bday', 'email', 'email2', 'msc',
      'phone', 'building', 'room_num', 'major', 'isabroad']
  tag_names = ["Nickname", "Use Nickname", "Birthday", "Email Address",
      "Alt. Email Address", "MSC", "Phone Number", "Building Name",
      "Room Number", "Major", "Is Abroad"]

  # Get stored values from database
  query = sqlalchemy.text("""
    SELECT * FROM users
      NATURAL JOIN members
    WHERE username=:u
    """)
  result = flask.g.db.execute(query, u=username)
  if result.returns_rows and result.rowcount != 0:
    result_cols = result.keys()
    r = result.first()
    stored_params = dict(zip(result_cols, r)) #stored_params maps sql columns to values

  # Update if needed
  if flask.request.method == 'POST':
    for (i, tag) in enumerate(tags):
      params[tag] = flask.request.form[tag]
      if params[tag] and tag in ['usenickname', 'msc', 'room_num', 'isabroad']:
        try:
          params[tag] = int(params[tag])
        except:
          flask.flash("Invalid input for field %s - your change was not saved!" % tag_names[i])
          params[tag] = stored_params[tag]

    for (i, tag) in enumerate(tags):
      if str(params[tag]) != str(stored_params[tag]):
        new_val = str(params[tag])
        query = sqlalchemy.text("UPDATE members SET %s = :val WHERE user_id = :u" % tag)
        results = flask.g.db.execute(query,
            u=auth_utils.get_user_id(username), val=new_val)
        flask.flash("%s was updated!" % tag_names[i])
  if not params:
    params = stored_params
  return flask.render_template('edit_user.html', params=params)
