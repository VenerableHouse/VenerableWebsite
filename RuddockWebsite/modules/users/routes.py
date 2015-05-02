from flask import render_template, redirect, flash, url_for, request, g, abort
from sqlalchemy import text
from time import strftime

from RuddockWebsite import auth_utils
from RuddockWebsite.constants import Permissions
from RuddockWebsite.decorators import login_required
from RuddockWebsite.modules.users import blueprint, helpers

@blueprint.route('/')
@login_required()
def show_users():
  ''' Procedure to show a list of all users, with all membership details. '''
  # store which columns we want, and their display names
  cols = ["user_id", "fname", "lname", "email", "matriculate_year", \
          "grad_year", "membership_desc"]
  display = [None, "First", "Last", "Email", "Matr.", "Grad.", "Membership"]
  fieldMap = dict(zip(cols, display))

  # check which table to read from
  filterType = request.args.get('filterType', None)
  if filterType == 'current':
    tableName = 'members_current'
  elif filterType == 'alumni':
    tableName = 'members_alumni'
  else:
    tableName = 'members'

  # perform query
  query = text("SELECT * FROM " + tableName + " NATURAL JOIN membership_types" +
               " ORDER BY fname")
  membership_data = g.db.execute(query).fetchall()

  # we also want to map ids to usernames so we can link to individual pages
  query = text("SELECT user_id, username FROM users")
  results = g.db.execute(query)
  idMap = dict(list(results)) # key is user_id, value is username

  return render_template('userlist.html', data=membership_data, fields=cols, \
      displays=display, idMap=idMap, fieldMap=fieldMap, filterType=filterType)

@blueprint.route('/view/<username>')
@login_required()
def show_user_profile(username):
  ''' Procedure to show a user's profile and membership details. '''
  d_dict_user, q_dict_user = helpers.get_user_info(username)
  offices = helpers.get_office_info(username)
  editable = helpers.check_edit_permission(username)

  if d_dict_user != None and q_dict_user != None:
    return render_template('view_user.html', display=d_dict_user, \
        info=q_dict_user, offices=list(offices), strftime=strftime,
        perm=editable)
  else:
    abort(404)

@blueprint.route('/edit/<username>', methods=['GET', 'POST'])
@login_required()
def change_user_settings(username):
  ''' Show a page for users to edit their information. '''
  # To visit this page, they must be either modifying their own page or be an
  # admin with appropriate permissions.
  if not helpers.check_edit_permission(username):
    abort(403)

  params = {}
  tags = ['nickname', 'usenickname', 'bday', 'email', 'email2', 'msc', 'phone', \
      'building', 'room_num', 'major', 'isabroad']
  tag_names = ["Nickname", "Use Nickname", "Birthday", "Email Address", \
      "Alt. Email Address", "MSC", "Phone Number", "Building Name", "Room Number", \
      "Major", "Is Abroad"]

  # Get stored values from database
  query = text("SELECT * FROM users NATURAL JOIN members WHERE username=:u")
  result = g.db.execute(query, u=str(username))
  if result.returns_rows and result.rowcount != 0:
    result_cols = result.keys()
    r = result.first()
    stored_params = dict(zip(result_cols, r)) #stored_params maps sql columns to values

  # Update if needed
  if request.method == 'POST':
    for (i, tag) in enumerate(tags):
      params[tag] = request.form[tag]
      if params[tag] and tag in ['usenickname', 'msc', 'room_num', 'isabroad']:
        try:
          params[tag] = int(params[tag])
        except:
          flash("Invalid input for field %s - your change was not saved!" % tag_names[i])
          params[tag] = stored_params[tag]

    for (i, tag) in enumerate(tags):
      if str(params[tag]) != str(stored_params[tag]):
        new_val = str(params[tag])
        query = text("UPDATE members SET %s = :val WHERE user_id = :u" % tag)
        results = g.db.execute(query, \
            u=auth_utils.get_user_id(username), val=new_val)
        flash("%s was updated!" % tag_names[i])
  if not params:
    params = stored_params
  return render_template('edit_user.html', params=params)
