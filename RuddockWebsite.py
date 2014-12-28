from functools import update_wrapper
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash
from collections import OrderedDict
from sqlalchemy import create_engine, text
from time import strftime
from email_utils import sendEmail
from constants import *
import datetime
import re
import config
import auth
import hassle
import email_templates

app = Flask(__name__)
app.debug = False
app.secret_key = config.SECRET_KEY

# Maximum file upload size, in bytes.
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create database engine object.
engine = create_engine(config.DB_URI, convert_unicode=True)

def fetch_all_results(query_result):
  '''
  Takes the result from a database query and organizes results. The output
  format is a list of dictionaries, where the dict keys are the columns
  returned.
  '''
  result = []
  result_keys = query_result.keys()

  for row in query_result:
    row_dict = dict(zip(result_keys, row))
    result.append(row_dict)

  return result

def display_error_msg(msg=False, redirect_location=None):
  if not msg:
    msg = "Invalid request. If you think you have received this message in \
        error, please find an IMSS rep immediately."

  if not redirect_location:
    redirect_location = "home"

  flash(msg)
  return redirect(url_for(redirect_location))

def login_required(permission=None):
  '''
  Login required decorator. Requires user to be logged in. If a permission
  is provided, then user must also have the appropriate permissions to
  access the page.
  '''
  def decorator(fn):
    def wrapped_function(*args, **kwargs):
      # User must be logged in.
      if 'username' not in session:
        flash("This page requires you to be logged in.")
        # Store page to be loaded after login in session.
        session['next'] = request.url
        return redirect(url_for('login'))

      # Check permissions.
      if permission is not None:
        if not auth.check_permission(permission):
          flash("You do have have permission to access this page.")
          session['next'] = request.url
          return redirect(url_for('login'))
      return fn(*args, **kwargs)
    return update_wrapper(wrapped_function, fn)
  return decorator

@app.before_request
def before_request():
  ''' Logic executed before request is processed. '''

  # Connect to the database and publish it in flask.g
  g.db = engine.connect()

@app.teardown_request
def teardown_request(exception):
  ''' Logic executed after every request is finished. '''

  # Close database connection.
  if g.db != None:
    g.db.close()

@app.route('/')
def home():
  return render_template('index.html')

@app.route('/login')
def login():
  ''' Displays the login page. '''
  return render_template('login.html')

@app.route('/login/submit', methods=['POST'])
def attempt_login():
  ''' Handles authentication. '''

  username = request.form.get('username', None)
  password = request.form.get('password', None)

  if username is not None and password is not None:
    user_id = auth.authenticate(username, password)
    if user_id is not None:
      permissions = auth.get_permissions(username)
      session['username'] = username
      session['permissions'] = permissions
      # True if there's any reason to show a link to the admin interface.
      session['show_admin'] = auth.check_permission(Permissions.Admin)
      # Update last login time
      auth.update_last_login(username)

      # Return to previous page if in session
      if 'next' in session:
        redirect_to = session.pop('next')
        return redirect(redirect_to)
      else:
        return redirect(url_for('home'))
  flash('Incorrect username or password. Please try again!')
  return redirect(url_for('login'))

@app.route('/login/forgot')
def forgot_password():
  ''' Displays a form for the user to reset a forgotten password. '''
  return render_template('forgot_password.html')

@app.route('/login/forgot/submit', methods=['POST'])
def forgot_password_submit():
  ''' Handle forgotten password submission. '''

  username = request.form.get('username', None)
  email = request.form.get('email', None)

  if auth.handle_forgotten_password(username, email):
    flash("An email with a recovery link has been sent. If you no longer have access to your email (alums), please contact an IMSS rep to recover your account.")
    return redirect(url_for('login'))
  else:
    flash("Incorrect username and/or email. If you continue to have issues with account recovery, contact an IMSS rep.")
    return redirect(url_for('forgot_password'))

@app.route('/login/reset/<reset_key>')
def reset_password(reset_key):
  ''' Checks the reset key. If successful, displays the password reset prompt. '''
  username = auth.check_reset_key(reset_key)
  if username is None:
    flash('Invalid request. If your link has expired, then you will need to generate a new one.')
    return redirect(url_for('forgot_password'))
  return render_template('reset_password.html', username=username, \
      reset_key=reset_key)

@app.route('/login/reset/<reset_key>/submit', methods=['POST'])
def reset_password_submit(reset_key):
  ''' Handles a password reset request. '''
  username = auth.check_reset_key(reset_key)
  if username is None:
    # Reset key was invalid.
    flash("Someone's making it on the naughty list this year...")
    return redirect(url_for('forgot_password'))
  new_password = request.form.get('password', '')
  new_password2 = request.form.get('password2', '')
  if auth.handle_password_reset(username, new_password, new_password2):
    flash('Password reset was successful.')
    return redirect(url_for('home'))
  else:
    # Password reset handler handles error flashes.
    return redirect(url_for('reset_password', reset_key=reset_key))

@app.route('/logout')
def logout():
  session.pop('username', None)
  return redirect(url_for('home'))

@app.route('/users')
@login_required()
def show_users():
  """ Procedure to show a list of all users, with all membership details. """
  # store which columns we want, and their displaynames
  cols = ["user_id", "lname", "fname", "email", "matriculate_year", \
          "grad_year", "major", "membership_desc"]
  display = [None, "Last", "First", "Email", "Matr.", "Grad.", "Major", "Type"]
  fieldMap = dict(zip(cols, display))

  # check which table to read from
  if 'filterType' in request.args and request.args['filterType'] == 'current':
    tableName = 'members_current'
    filterType = 'current'
  elif 'filterType' in request.args and request.args['filterType'] == 'alumni':
    tableName = 'members_alumni'
    filterType = 'alumni'
  else:
    tableName = 'members'
    filterType = 'all'

  # perform query
  query = text("SELECT * FROM " + tableName + " NATURAL JOIN membership_types")
  results = g.db.execute(query)

  # put results in a dictionary
  result_cols = results.keys()
  res = []
  for result in results:
    temp_dict = {}
    for i, key in enumerate(result_cols):
      if key in cols and result[i]:
        temp_dict[key] = result[i]
    res.append(temp_dict)

  # we also want to map ids to usernames so we can link to individual pages
  query = text("SELECT user_id, username FROM users")
  results = g.db.execute(query)
  idMap = dict(list(results)) # key is id, value is username

  return render_template('userlist.html', data = res, fields = cols, \
      displays=display, idMap=idMap, fieldMap=fieldMap, filterType=filterType)

@app.route('/users/view/<username>')
@login_required()
def show_user_profile(username):
  """ Procedure to show a user's profile and membership details. """
  def get_user_info(username):
    """ Procedure to get a user's info from the database. """
    cols = [["username"], ["fname", "lname"], ["nickname"], ["bday"], \
            ["email"], ["email2"], ["status"], ["matriculate_year"], \
            ["grad_year"], ["msc"], ["phone"], ["building", "room_num"], \
            ["membership_desc"], ["major"], ["uid"], ["isabroad"]]
    display = ["Username", "Name", "Nickname", "Birthday", "Primary Email", \
               "Secondary Email", "Status", "Matriculation Year", \
               "Graduation Year", "MSC", "Phone Number", "Residence", \
               "Membership", "Major", "UID", "Is Abroad"]
    # Defines the order and mapping of displayed attributes to sql columns
    d_dict = OrderedDict(zip(display, cols))
    query = text("SELECT * FROM users NATURAL JOIN members NATURAL JOIN membership_types WHERE username=:u")
    result = g.db.execute(query, u=str(username))

    values = result.first()
    if not values:
      d_dict = None
      values = None
    else:
      if not values['usenickname']:
        d_dict.pop('Nickname')
    return (d_dict, values)

  def get_office_info(username):
    """ Procedure to get a user's officer info. """
    cols = ["office_name", "elected", "expired"]
    query = text("""
      SELECT office_name, elected, expired
      FROM office_members NATURAL JOIN users NATURAL JOIN offices
      WHERE username = :u
      ORDER BY elected, expired, office_name
    """)
    return g.db.execute(query, u=str(username))

  def can_edit(username):
    """ Returns true if user has permission to edit page. """
    if 'username' not in session:
      return False
    return session['username'] == username or \
        auth.check_permission(Permissions.UserAdmin)

  d_dict_user, q_dict_user = get_user_info(username)
  offices = get_office_info(username)
  editable = can_edit(username)

  if d_dict_user is not None and q_dict_user is not None:
    return render_template('view_user.html', display = d_dict_user, \
        info = q_dict_user, offices = list(offices), strftime = strftime,
        perm = editable)
  else:
    flash("User does not exist!")
    return redirect(url_for('home'))

@app.route('/users/edit/<username>', methods=['GET', 'POST'])
@login_required(Permissions.UserAdmin)
def change_user_settings(username):
  """ Procedure to process the login page. Also handles authentication. """
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
            u=auth.get_user_id(username), val=new_val)

        flash("%s was updated!" % tag_names[i])


  if not params:
    params = stored_params

  return render_template('edit_user.html', params = params)

@app.route('/government')
def show_gov():
  # Get current officers
  query = text("""
    SELECT CONCAT(fname, ' ', lname) AS name, username, office_name,
      office_email, office_id, is_excomm, is_ucc
    FROM office_members_current
      NATURAL JOIN offices
      NATURAL JOIN members_current
      NATURAL JOIN users
      """)
  results = g.db.execute(query)

  # Organize by type (excomm and ucc are special)
  excomm = []
  ucc = []
  other = []
  for result in results:
    # Organize by type
    if result['is_excomm']:
      excomm.append(result)
    elif result['is_ucc']:
      ucc.append(result)
    else:
      other.append(result)

  ucc.sort(key=lambda d: d['office_name'])
  other.sort(key=lambda d: d['office_name'])

  # tuple with name, email, and users, so that template can parse efficiently
  all_types = [
    ('Executive Committee', 'excomm', excomm),
    ('Upperclass Counselors', 'uccs', ucc),
    ('Other Offices', None, other)
  ]

  return render_template('government.html', all_types = all_types)

@app.route('/about_us')
def show_about_us():
  return render_template('about_us.html')

@app.route('/account/create/<create_account_key>')
def create_account(create_account_key):
  ''' Checks the key. If valid, displays the create account page. '''

  def get_user_data(user_id):
    ''' Helper to get user data. '''
    query = text("""
      SELECT fname, lname, uid, matriculate_year, grad_year, email
      FROM members
      WHERE user_id=:uid
      """)
    return g.db.execute(query, uid=user_id).first()

  user_id = auth.check_create_account_key(create_account_key)
  if user_id is None:
    flash('Invalid request. Please check your link and try again. If you continue to encounter problems, please find an IMSS rep.')
    return redirect(url_for('home'))

  user_data = get_user_data(user_id)
  if user_data is None:
    flash('An unexpected error occurred. Please find an IMSS rep.')
    return redirect(url_for('home'))
  return render_template('create_account.html', user_data=user_data,
      key=create_account_key)

@app.route('/account/create/<create_account_key>/submit', methods=['POST'])
def create_account_submit(create_account_key):
  ''' Handles a create account request. '''
  user_id = auth.check_create_account_key(create_account_key)
  if user_id is None:
    # Key is invalid.
    flash("Someone's been naughty.")
    return redirect(url_for('home'))
  username = request.form.get('username', None)
  password = request.form.get('password', None)
  password2 = request.form.get('password2', None)
  birthday = request.form.get('birthday', None)
  if username is None or password is None or password2 is None or birthday is None:
    flash('Invalid request.')
    return redirect(url_for('home'))

  # Username and password will be checked by account creation.
  # Check birthday format.
  try:
    datetime.datetime.strptime(birthday, '%Y-%m-%d')
  except ValueError:
    flash("Invalid birthday.")
    return redirect(url_for('create_account', create_account_key=create_account_key))
  if auth.handle_create_account(user_id, username, password, password2):
    # Update birthday.
    query = text("UPDATE members SET bday=:b WHERE user_id=:uid")
    g.db.execute(query, b=birthday, uid=user_id)
    flash('Account successfully created.')
    return redirect(url_for('home'))
  else:
    # Flashes already handled.
    return redirect(url_for('create_account', create_account_key=create_account_key))

@app.route('/admin')
@login_required(Permissions.Admin)
def admin_home():
  ''' Loads a home page for admins, providing links to various tools. '''
  admin_tools = []
  if auth.check_permission(Permissions.UserAdmin):
    admin_tools.append({
      'name': 'Add new members',
      'link': url_for('add_members', _external=True)})
    admin_tools.append({
      'name': 'Send account creation reminder',
      'link': url_for('send_reminder_emails', _external=True)})
  if auth.check_permission(Permissions.HassleAdmin):
    admin_tools.append({
      'name': 'Room hassle',
      'link': url_for('run_hassle', _external=True)})
  return render_template('admin.html', tools=admin_tools)

@app.route('/admin/reminder_email', methods=['GET', 'POST'])
@login_required(Permissions.UserAdmin)
def send_reminder_emails():
  '''
  Sends a reminder email to all members who have not yet created
  an account.
  '''

  def get_members_without_accounts():
    '''
    Returns a list of dicts with the first name, last name, email, and
    user ID for everyone who hasn't made an account yet.
    '''

    query = text("SELECT fname, lname, email, uid, user_id FROM members \
        NATURAL LEFT JOIN users WHERE username IS NULL")
    r = g.db.execute(query)
    return fetch_all_results(r)

  def send_reminder_email(fname, lname, email, user_id, uid):
    user_hash = create_account_hash(user_id, uid, fname, lname)
    name = fname + ' ' + lname

    to = email
    subject = "Please create an account"
    msg = "Hey " + name + ",\n\n" + \
        "This is a reminder to create an account on the " + \
        "Ruddock House Website. You can do this by following this link:\n" + \
        url_for('create_account', k=user_hash, u=user_id, _external=True) + \
        "\n\n" + \
        "If you think this is an error or if you have any other " + \
        "questions, please contact us at imss@ruddock.caltech.edu" + \
        "\n\n" + \
        "Thanks!\n" + \
        "The Ruddock IMSS Team"

    sendEmail(to, msg, subject)

  ### END HELPER FUNCTIONS ###
  data = get_members_without_accounts()

  state = None
  if request.method == 'POST' and request.form['state']:
    state = request.form['state']

  if state == 'yes':
    for member in data:
      send_reminder_email(member['fname'], member['lname'], member['email'], \
          member['user_id'], member['uid'])

    flash('Sent reminder emails to ' + str(len(data)) + ' member(s).')
    return redirect(url_for('admin_home'))
  elif state == 'no':
    return redirect(url_for('admin_home'))
  else:
    return render_template('create_account_reminder.html', data=data)

@app.route('/admin/add_members', methods=['GET', 'POST'])
@login_required(Permissions.UserAdmin)
def add_members():
  '''
  Provides a form to add new members to the website, and then emails the
  new members a unique link to create an account.
  '''

  def convert_membership_type(membership_desc):
    '''
    This takes a membership description (full member, social member, etc)
    and converts it to the corresponding type. Expects input to be valid
    and one of (full, social, associate, RA).
    '''

    full_regex = re.compile(r'^full(| member)$', re.I)
    social_regex = re.compile(r'^social(| member)$', re.I)
    assoc_regex = re.compile(r'^associate(| member)$', re.I)
    ra_regex = re.compile(r'^(resident associate|ra)$', re.I)

    if full_regex.match(membership_desc):
      return 1
    elif social_regex.match(membership_desc):
      return 2
    elif assoc_regex.match(membership_desc):
      return 3
    elif ra_regex.match(membership_desc):
      return 4
    else:
      return False

  def validate_data(data):
    '''
    Expects data to be a dict mapping fields to values.
    '''

    # Keeps track of what errors have been found.
    errors = set()

    name_regex = re.compile(r"^[a-z][a-z '-]{0,14}[a-z]$", re.I)
    uid_regex = re.compile(r'^[0-9]{7}$')
    year_regex = re.compile(r'^(19[0-9]{2}|2(0[0-9]{2}|1[0-5][0-9]))$')
    email_regex = re.compile(r'^[a-z0-9\.\_\%\+\-]+@[a-z0-9\.\-]+\.[a-z]{2,4}$', re.I)

    try:
      # Check that all fields are valid.
      if not name_regex.match(data['fname']):
        errors.add('First Name')

      if not name_regex.match(data['lname']):
        errors.add('Last Name')

      if not uid_regex.match(data['uid']):
        errors.add('UID')

      if not year_regex.match(data['matriculate_year']):
        errors.add('Matriculation Year')

      if not year_regex.match(data['grad_year']):
        errors.add('Graduation Year')

      if not email_regex.match(data['email']):
        errors.add('Email')

      if not convert_membership_type(data['membership_type']):
        errors.add('Membership Type')

    except KeyError:
      flash("Invalid data submitted.")
      return False

    if len(errors) > 0:
      # So the errors appear in the same order every time.
      errors = list(errors)
      errors.sort()

      for field_name in errors:
        flash("Invalid " + field_name + "(s) submitted.")
      return False

    return True

  def process_data(new_members_data, field_list):
    '''
    Expects data to be a single string (with the contents of a csv file) and
    field_list to be a list of dicts describing each field. Validates the
    data before returning it as a list of dicts mapping each field to its
    value. Returns false if unsuccessful.
    '''

    # Microsoft Excel has a habit of saving csv files using just \r as
    # the newline character, not even \r\n.
    if '\r' in new_members_data and '\n' in new_members_data:
      delim = '\r\n'
    elif '\r' in new_members_data:
      delim = '\r'
    else:
      delim = '\n'

    data = []
    for line in new_members_data.split(delim):
      if line == "":
        continue
      values = line.split(',')
      if len(values) != len(field_list):
        flash("Invalid data submitted.")
        return False
      # Skip title line if present
      if values[0] == field_list[0]['name']:
        continue
      entry = {}
      for i in range(len(field_list)):
        field = field_list[i]
        entry[field['field']] = values[i]
      data.append(entry)
    for entry in data:
      if not validate_data(entry):
        return False
    return data

  def add_new_members(data):
    '''
    This adds the members to the database and them emails them with
    account creation information. Assumes data has already been validated.
    '''
    insert_query = text("""
      INSERT INTO members (fname, lname, uid, matriculate_year,
        grad_year, email, membership_type, create_account_key)
      VALUES (:fname, :lname, :uid, :matriculate_year, :grad_year,
        :email, :membership_type, :key)
        """)
    check_query = text("SELECT 1 FROM members WHERE uid=:uid")

    members_added_count = 0
    members_skipped_count = 0

    for entry in data:
      # Check if user is in database already
      result = g.db.execute(check_query, uid=entry['uid']).first()
      if result is not None:
        members_skipped_count += 1
        continue

      membership_type = convert_membership_type(entry['membership_type'])
      create_account_key = auth.generate_create_account_key()
      # Add the user to the database.
      result = g.db.execute(insert_query, fname=entry['fname'],
          lname=entry['lname'], uid=entry['uid'],
          matriculate_year=entry['matriculate_year'],
          grad_year=entry['grad_year'], email=entry['email'],
          membership_type=membership_type,
          key=create_account_key)

      entry['name'] = entry['fname'] + ' ' + entry['lname']

      # Email the user
      subject = "Welcome to the Ruddock House Website!"
      msg = email_templates.AddedToWebsiteEmail.format(entry['name'],
          url_for('create_account', create_account_key=create_account_key,
            _external=True))
      to = entry['email']
      sendEmail(to, msg, subject)
      members_added_count += 1

    flash(str(members_added_count) + " members were successfully added, and " +
        str(members_skipped_count) + " members were skipped.")

    # Remind admin to add users to mailing lists.
    flash("IMPORTANT: Don't forget to add the new members to manual email lists, like spam@ruddock!")

    # Send an email to IMSS to alert them that users have been added.
    to = "imss@ruddock.caltech.edu"
    subject = "Members were added to the Ruddock Website"
    entries = '\n'.join([entry['fname'] + ' ' + entry['lname'] for entry in data])
    msg = email_templates.MembersAddedEmail.format(entries)
    sendEmail(to, msg, subject, usePrefix=False)

  def get_raw_data(field_list):
    '''
    For processing data in add single member mode, this converts
    request data to a csv string. Returns false if unsuccessful.
    '''
    values = []
    for field in field_list:
      if request.form.has_key(field['field']):
        value = request.form[field['field']]
        if value == '':
          flash("All fields are required.")
          return False
        values.append(value)
      else:
        flash('Invalid request.')
        return False
    return ','.join(values)

  ### End helper function definitions ###

  PATH_TO_TEMPLATE = '/static/new_members_template.csv'
  TEMPLATE_FILENAME = PATH_TO_TEMPLATE.split('/')[-1]

  # Order in which fields appear in template.
  field_list = [
    { 'field':'fname',
      'name':'First Name'},
    { 'field':'lname',
      'name':'Last Name'},
    { 'field':'uid',
      'name':'UID'},
    { 'field':'matriculate_year',
      'name':'Matriculation Year'},
    { 'field':'grad_year',
      'name':'Graduation Year'},
    { 'field':'email',
      'name':'Email'},
    { 'field':'membership_type',
      'name':'Membership Type'}
  ]

  state = 'default'
  if request.method == 'POST' and request.form.has_key('state'):
    state = request.form['state']
  if state == 'preview':
    # The mode must be provided and valid.
    if request.form.has_key('mode') and \
        request.form['mode'] in ['single', 'multi']:
      mode = request.form['mode']
    else:
      flash('Invalid request.')
      state = 'default'
  if state == 'preview':
    if mode == 'single':
      raw_data = get_raw_data(field_list)
    else:
      if request.files.has_key('new_members_file'):
        new_members_file = request.files['new_members_file']
        raw_data = new_members_file.read()
      else:
        raw_data = False
    if raw_data:
      data = process_data(raw_data, field_list)
      if data:
        return render_template('new_members.html', state='preview', \
            data=data, field_list=field_list, raw_data=raw_data)
  elif state == 'confirmed':
    if request.form.has_key('raw_data'):
      raw_data = request.form['raw_data']
      data = process_data(raw_data, field_list)
      if data:
        add_new_members(data)
    else:
      flash('Invalid request.')
  return render_template('new_members.html', state='default', \
      path=PATH_TO_TEMPLATE, filename=TEMPLATE_FILENAME)

@app.route('/hassle')
@login_required(Permissions.HassleAdmin)
def run_hassle():
  ''' Logic for room hassles. '''

  available_participants = hassle.get_available_participants()
  available_rooms = hassle.get_available_rooms()
  events = hassle.get_events_with_roommates()
  alleys = [1, 2, 3, 4, 5, 6]

  return render_template('hassle.html',
      available_participants=available_participants,
      available_rooms=available_rooms,
      events=events,
      alleys=alleys)

@app.route('/hassle/event', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def hassle_event():
  ''' Submission endpoint for a new event (someone picks a room). '''

  user_id = request.form.get('user_id', None)
  room_number = request.form.get('room', None)
  roommates = request.form.getlist('roommate_id')

  if user_id == None or room_number == None:
    flash("Invalid request - try again?")
  else:
    roommates = [r for r in roommates if r != "none"]

    # Check for invalid roommate selection.
    if user_id in roommates or len(roommates) != len(set(roommates)):
      flash("Invalid roommate selection.")
    else:
      hassle.new_event(user_id, room_number, roommates)
  return redirect(url_for('run_hassle'))

@app.route('/hassle/restart', defaults={'event_id': None})
@app.route('/hassle/restart/<int:event_id>')
@login_required(Permissions.HassleAdmin)
def hassle_restart(event_id):
  if event_id == None:
    hassle.clear_events()
  else:
    hassle.clear_events(event_id)
  return redirect(url_for('run_hassle'))

@app.route('/hassle/new')
@login_required(Permissions.HassleAdmin)
def new_hassle():
  ''' Redirects to the first page to start a new room hassle. '''

  # Clear old data.
  hassle.clear_all()

  return redirect(url_for('new_hassle_participants'))

@app.route('/hassle/new/participants')
@login_required(Permissions.HassleAdmin)
def new_hassle_participants():
  ''' Select participants for the room hassle. '''

  # Get a list of all current members.
  members = hassle.get_all_members()
  return render_template('hassle_new_participants.html', members=members)

@app.route('/hassle/new/participants/submit', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def new_hassle_participants_submit():
  ''' Submission endpoint for hassle participants. Redirects to next page. '''

  # Get a list of all participants' user IDs.
  participants = map(lambda x: int(x), request.form.getlist('participants'))
  # Update database with this hassle's participants.
  hassle.set_participants(participants)
  return redirect(url_for('new_hassle_rooms'))

@app.route('/hassle/new/rooms')
@login_required(Permissions.HassleAdmin)
def new_hassle_rooms():
  ''' Select rooms available for the room hassle. '''

  # Get a list of all rooms.
  rooms = hassle.get_all_rooms()
  return render_template('hassle_new_rooms.html', rooms=rooms)

@app.route('/hassle/new/rooms/submit', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def new_hassle_rooms_submit():
  ''' Submission endpoint for hassle rooms. Redirects to next page. '''

  # Get a list of all room numbers.
  rooms = map(lambda x: int(x), request.form.getlist('rooms'))
  # Update database with participating rooms.
  hassle.set_rooms(rooms)
  return redirect(url_for('new_hassle_confirm'))

@app.route('/hassle/new/confirm')
@login_required(Permissions.HassleAdmin)
def new_hassle_confirm():
  ''' Confirmation page for new room hassle. '''

  participants = hassle.get_participants()
  rooms = hassle.get_participating_rooms()

  return render_template('hassle_new_confirm.html', rooms=rooms, \
      participants=participants)

@app.route('/hassle/new/confirm/submit', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def new_hassle_confirm_submit():
  ''' Submission endpoint for confirmation page. '''

  # Nothing to do, everything is already in the database.
  return redirect(url_for('run_hassle'))

if __name__ == "__main__":
  app.run()
