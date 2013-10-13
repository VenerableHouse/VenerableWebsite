from functools import update_wrapper
from flask import Flask, request, session, g, redirect, url_for, abort, \
        render_template, flash
from collections import OrderedDict
from sqlalchemy import create_engine, MetaData, text
import config, auth
import datetime
from room_map_dict_def import room_dict
from time import strftime
from email_utils import sendEmail
from constants import *
import re

app = Flask(__name__)
app.debug = True
app.secret_key = config.SECRET_KEY

""" Connect to the mySQL database. """
engine = create_engine(config.DB_URI, convert_unicode=True)
connection = engine.connect()

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

def display_error_msg(msg=False, redirect_location=False):
  if not msg:
    msg = "Invalid request. If you think you have received this message in \
        error, please find an IMSS rep immediately."

  if not redirect_location:
    redirect_location = "home"

  flash(msg)
  return redirect(url_for(redirect_location))

def login_required(msg='You must be logged in for that!', access_level = 1):
  """ Login required decorator. Flashes msg at the login prompt."""
  def decorator(fn):
    def wrapped_function(*args, **kwargs):
      # make sure the user is logged in
      if 'username' not in session:
        flash(msg)
        session['next'] = request.url # store url in session so not put in url
        return redirect(url_for('login'))

      if has_permissions(args = kwargs, access_level = access_level):
        return fn(*args, **kwargs)
      else:
        flash('You do not have appropriate permissions for this action.')
        session['next'] = request.url # store url in session so not put in url
        return redirect(url_for('login'))

      return fn(*args, **kwargs)
    return update_wrapper(wrapped_function, fn)
  return decorator

def has_permissions(args = {}, access_level = 1):
  """ Return true if the session's user has appropriate permissions """
  # check if the page is designated for this user
  if 'username' in args and args['username'] == session['username']:
    return True
  # otherwise, make sure user has appropriate permissions
  if 'access_level' in session and session['access_level'] >= access_level:
    return True
  else:
    return False

@app.route('/')
def home():
  return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
  """ Procedure to process the login page. Also handles authentication. """
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']

    user_id = auth.authenticate(username, password, connection)
    if user_id:
      session['username'] = request.form['username']
      session['user_id'] = user_id
      session['access_level'] = auth.get_user_access_level(username, connection)

      # return to previous page if in session
      if 'next' in session:
        redirect_to = session.pop('next')
        return redirect(redirect_to)
      else:
        return redirect(url_for('home'))
    else:
      flash('Incorrect username or password. Please try again!')
      return render_template('login.html')

  return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_passwd():
  """ Procedure to allow users to reset forgotten passwords. """
  if 'username' in session:
    flash("You're already logged in!")
    return redirect(url_for('home'))

  if request.method == 'POST':
    username = request.form['username']
    email = request.form['email']
    query = text("SELECT * FROM users NATURAL JOIN members WHERE username=:u")
    result = connection.execute(query, u=str(username))
    if result.returns_rows and result.rowcount != 0:
      result_cols = result.keys()
      row = result.first()
      q_dict = dict(zip(result_cols, row))
      if q_dict['email'] == email:
        reset_key = auth.reset_key(q_dict['passwd'], q_dict['salt'], username)
        msg = "We received a request to reset this account's password.\n" \
              "If you didn't request this change, disregard this email.\n" \
              "If you do want to change your password, please go to:\n" +\
              url_for('reset_passwd', u=q_dict['user_id'], r=reset_key,
                  _external=True) + \
              "\n\nThanks,\nThe Ruddock Website"
        sendEmail(str(email), msg, "[RuddWeb] Forgotten Password")
        flash("An email has been sent.")
        redirect(url_for('home'))
      else:
        flash("Incorrect email.")
        return render_template('forgot_password.html')
    else:
      flash("Incorrect username.")
      return render_template('forgot_password.html')
  return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_passwd():
  if request.method == 'POST':
    if 'r_username' not in session:
      flash('You did something naughty')
      return redirect(url_for('forgot_passwd'))
    new_password = request.form['password']
    new_password2 = request.form['password2']

    # Get the user's email
    query = text("SELECT email FROM members NATURAL JOIN users WHERE username=:username")
    result = connection.execute(query, username=str(session['r_username']))
    email = result.first()[0]

    if new_password != new_password2:
      flash('Passwords do not match. Please try again!')
      return render_template('reset_password.html')
    elif new_password == '':
      flash('Passwords cannot be empty. Please try again!')
      return render_template('reset_password.html')
    elif auth.passwd_reset(session['r_username'], new_password, connection, \
                           email=email):
      session.pop('r_username')
      flash('Password successfully changed.')
      return redirect(url_for('home'))
    else:
      flash('An unknown problem has occured. Please contact an admin!')
      return render_template('reset_password.html')
  else:
    user_id = request.args.get('u', None)
    reset_key = request.args.get('r', None)
    if user_id == None or reset_key == None:
      flash("Missing parameter. Try generating the link again?")
      return redirect(url_for('forgot_passwd'))
    query = text("SELECT * FROM users WHERE user_id=:u")
    result = connection.execute(query, u=str(user_id))
    if result.returns_rows and result.rowcount != 0:
      result_cols = result.keys()
      row = result.first()
      q_dict = dict(zip(result_cols, row))
      if int(reset_key) == auth.reset_key(q_dict['passwd'], q_dict['salt'],
                                          q_dict['username']):
        session['r_username'] = q_dict['username']
        return render_template('reset_password.html')
      flash("Incorrect reset_key. Try generating the link again?")
    return redirect(url_for('forgot_passwd'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required()
def change_passwd():
  """ Procedure to process the password reset page. """
  if request.method == 'POST':
    username = session['username']
    old_password = request.form['old_password']
    new_password = request.form['password']
    new_password2 = request.form['password2']

    # Get the user's email
    query = text("SELECT email FROM members WHERE user_id=:id")
    result = connection.execute(query, id=str(session['user_id']))
    email = result.first()[0]

    if not auth.authenticate(username, old_password, connection):
      flash('Wrong old password. Please try again!')
      return render_template('password_change.html')
    if new_password != new_password2:
      flash('New passwords do not match. Please try again!')
      return render_template('password_change.html')
    elif new_password == '':
      flash('Passwords cannot be empty. Please try again!')
      return render_template('password_change.html')
    elif auth.passwd_reset(username, new_password, connection, email=email):
      flash('Password successfully changed.')
      return redirect(url_for('home'))
    else:
      flash('An unknown problem has occured. Please contact an admin!')
      return render_template('password_change.html')

  return render_template('password_change.html')

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
          "grad_year", "major"]
  display = [None, "Last", "First", "Email", "Matr.", "Grad.", "Major"]
  fieldMap = dict(zip(cols, display))

  # get order by information from request arguments
  if 'field' in request.args and request.args['field'] in cols:
    ordField = request.args['field']
  else:
    ordField = 'lname'
  if 'dir' in request.args and request.args['dir'] in ['ASC', 'DESC']:
    ordDirect = request.args['dir']
  else:
    ordDirect = 'ASC'

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
  query = text("SELECT * FROM " + tableName + " ORDER BY " + ordField + " " + ordDirect)
  results = connection.execute(query)

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
  results = connection.execute(query)
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
            ["membership"], ["major"], ["uid"], ["isabroad"]]
    display = ["Username", "Name", "Nickname", "Birthday", "Primary Email", \
               "Secondary Email", "Status", "Matriculation Year", \
               "Graduation Year", "MSC", "Phone Number", "Residence", \
               "Membership", "Major", "UID", "Is Abroad"]
    d_dict = OrderedDict(zip(display, cols))
    #d_dict defines the order and mapping of displayed attributes to sql columns
    query = text("SELECT * FROM users NATURAL JOIN members WHERE username=:u")
    result = connection.execute(query, u=str(username))
    if result.returns_rows and result.rowcount != 0:
      result_cols = result.keys()
      r = result.first()
      q_dict = dict(zip(result_cols, r)) #q_dict maps sql columns to values
      if not q_dict['usenickname']:
        d_dict.pop('Nickname')
      return (d_dict, q_dict)
    else:
      return (None, None)

  def get_office_info(username):
    """ Procedure to get a user's officer info. """
    cols = ["office_name", "elected", "expired"]
    query = text("SELECT * FROM office_members NATURAL JOIN users NATURAL " + \
        "JOIN offices WHERE username = :u ORDER BY elected, expired, " + \
        "office_name")
    results = connection.execute(query, u=str(username))

    # put results in a dictionary
    res = []
    result_cols = results.keys()
    for result in results:
      temp_dict = {}
      for i,key in enumerate(result_cols):
        if key in cols:
          temp_dict[key] = result[i]
      res.append(temp_dict)
    return res

  d_dict_user, q_dict_user = get_user_info(username)
  offices = get_office_info(username)

  if d_dict_user != None and q_dict_user != None:
    return render_template('view_user.html', display = d_dict_user, \
        info = q_dict_user, offices = offices, strftime = strftime,
        perm = has_permissions({'username':username}, AL_EDIT_PAGE))
  else:
    flash("User does not exist!")
    return redirect(url_for('home'))

@app.route('/users/edit/<username>', methods=['GET', 'POST'])
@login_required(access_level = AL_EDIT_PAGE)
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
  result = connection.execute(query, u=str(username))
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
        results = connection.execute(query, \
            u=auth.get_user_id(username, connection), val=new_val)

        flash("%s was updated!" % tag_names[i])


  if not params:
    params = stored_params

  return render_template('edit_user.html', params = params)

@app.route('/government')
def show_gov():
  # Get current officers
  # Note: A "current" officer has already started, and hasn't expired yet.
  query = "SELECT CONCAT(fname, ' ', lname) AS name, username, \
                  office_name, office_email, office_id, is_excomm \
           FROM office_members_current NATURAL JOIN offices NATURAL JOIN members_current \
                NATURAL JOIN users"
  results = connection.execute(query)
  result_cols = results.keys()

  # desired fields
  cols = ["office_name", "name", "office_email"]

  # organize by type (excomm and ucc are special)
  excomm = []
  ucc = []
  other = []
  for result in results:
    # filter fields
    temp_dict = {}
    for i,key in enumerate(result_cols):
      if key in cols:
        temp_dict[key] = result[i]
      temp_dict['username'] = result['username'] # force username in dict

    # organize by type
    if result['is_excomm']: excomm.append(temp_dict)
    elif re.match('UCC', result['office_name']): ucc.append(temp_dict)
    else: other.append(temp_dict)

  ucc.sort(key=lambda d: d['office_name'])
  other.sort(key=lambda d: d['office_name'])

  # map the types to their names, so that template can parse efficiently
  all_types = OrderedDict([
    ('Executive Committee', excomm),
    ('Upperclass Counselors', ucc),
    ('Other Offices', other)
  ])

  return render_template('government.html', all_types = all_types)

@app.route('/about_us')
def show_about_us():
  return render_template('about_us.html')

@app.route('/news')
def show_news():
  # TODO: Implement this.
  return render_template('news.html')

@app.route('/calendar')
def show_calendar():
  # TODO: Implement this.
  return render_template('calendar.html')

@app.route('/map')
def show_map():
  return render_template('map.html', room_dict=room_dict, hl=0)

@app.route('/map/<room>')
@login_required()
def show_map_room(room):
  '''Shows the map with a specific room highlighted'''

  # Figure out who lives there
  query = text("SELECT fname, lname, nickname, usenickname, username  \
     FROM members NATURAL JOIN users WHERE room_num=:id \
    AND building LIKE '%ruddock%'")
  results = connection.execute(query, id=room)

  # Make these tuples of ('name', 'username')
  people = []
  for person in results:
    if person[3]:
      people.append(('%s %s' % (person[2], person[1]), person[4]))
    else:
      people.append(('%s %s' % (person[0], person[1]), person[4]))

  return render_template('map.html', room_dict=room_dict, hl=room, \
    people=people)

def create_account_hash(user_id, uid, fname, lname):
  '''
  Creates a unique hash for users trying to create an account.
  '''
  return hash(str(user_id) + str(uid) + str(fname) + str(lname))

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
  ''' 
  Allows the user to create an account. The user should have receieved 
  an email when the secretary imported him/her into the database with
  a unique link to create the account with. 
  '''

  def validate_data(data):
    ''' 
    Checks that the provided username, password, and birthday are valid.
    '''

    # Check username
    username_regex = re.compile(r'^[a-zA-Z0-9\-\_]{1,32}$')
    if not username_regex.match(data['username']):
      flash("Invalid username.")
      return False

    query = text("SELECT COUNT(*) FROM users WHERE username=:username")
    r = connection.execute(query, username=data['username'])
    result = fetch_all_results(r)
    count = result[0]['COUNT(*)']

    if count != 0:
      flash("Username already in use.")
      return False

    # Check password
    if data['password'] != data['password2']:
      flash("Passwords do not match.")
      return False

    pwd_length = len(data['password'])
    if pwd_length < 8:
      flash("Password is too short.")
      return False

    if not re.compile(r'.*[a-zA-Z]').match(data['password']) or not \
        re.compile(r'.*[0-9]').match(data['password']):
          flash("Password should contain both numbers and letters.")
          return False

    # Check birthday
    try:
      datetime.datetime.strptime(data['birthday'], '%Y-%m-%d')
    except ValueError:
      flash("Invalid birthday.")
      return False

    return True

  def get_user_data(user_id):
    query = text("SELECT fname, lname, uid, matriculate_year, grad_year, \
        email FROM members WHERE user_id=:user_id")
    r = connection.execute(query, user_id=user_id)
    result = fetch_all_results(r)

    return result[0]

  def check_key_id_pair(key, user_id):
    # Check that the user_id is valid.
    query = text("SELECT COUNT(*) FROM members WHERE user_id=:user_id")
    r = connection.execute(query, user_id=user_id)
    result = fetch_all_results(r)
    count = result[0]['COUNT(*)']

    if count != 1:
      return False

    # Make sure an account does not already exist for that user_id.
    query = text("SELECT COUNT(*) FROM users WHERE user_id=:user_id")
    r = connection.execute(query, user_id=user_id)
    result = fetch_all_results(r)
    count = result[0]['COUNT(*)']

    if count != 0:
      return False

    # Check the key.
    user_data = get_user_data(user_id)
    true_hash = create_account_hash(user_id, user_data['uid'], \
        user_data['fname'], user_data['lname'])

    if str(true_hash) != str(key):
      return False

    return True

  def create_new_user(user_id, username, password, email):
    '''
    Creates a new account with the given parameters. Assumes that all 
    parameters have already been validated.
    '''

    query = text("INSERT INTO users (user_id, username, passwd) VALUES \
        (:user_id, :username, :password)")

    # Creates the account with an empty password.
    connection.execute(query, user_id=user_id, username=username, \
        password='')

    # Use the password reset function to set the password, to ensure
    # consistent salting.
    auth.passwd_reset(username, password, connection, salt=True, \
        email=False)

    # Email the user to let them know an account has been created.
    subject = "[RuddWeb] Thanks for creating an account!"
    msg = "You have just created an account on the Ruddock website with " + \
        "the username \"" + username + "\".\n" + \
        "If this was not you, please email imss@ruddock.caltech.edu immediately.\n\n" + \
        "Thanks!\n" + \
        "The Ruddock IMSS Team"
    to = email
    sendEmail(to, msg, subject)

  def update_birthday(user_id, birthday):
    query = text("UPDATE members SET bday=:bday WHERE user_id=:user_id")
    connection.execute(query, bday=birthday, user_id=user_id)

  ### End helper functions ###
  
  if request.method == 'POST':
    key = request.form['k']
    user_id = request.form['u']

    if not key or not user_id or not check_key_id_pair(key, user_id):
      return display_error_msg()

    user_data = get_user_data(user_id)

    data = {}
    data['username'] = request.form['username']
    data['password'] = request.form['password']
    data['password2'] = request.form['password2']
    data['birthday'] = request.form['birthday']

    if validate_data(data):
      create_new_user(user_id, data['username'], data['password'], \
          user_data['email'])
      update_birthday(user_id, data['birthday'])

      flash('Account successfully created.')
      return redirect(url_for('home'))
    
  key = request.args.get('k', default=None)
  user_id = request.args.get('u', default=None)

  if not key or not user_id or not check_key_id_pair(key, user_id):
    return display_error_msg()

  user_data = get_user_data(user_id)
  
  return render_template('create_account.html', user_data=user_data, \
      key=key, user_id=user_id)

@app.route('/secretary/add_members', methods=['GET', 'POST'])
@login_required(access_level = AL_ADD_MEMBERS)
def add_members():
  ''' 
  Provides a form to add new members to the website, and then emails the
  new members a unique link to create an account.
  '''

  def validate_data(data, field_list):
    ''' 
    Expects the data to be a list of dicts mapping field names to values.
    Expects the field list to be a list of dicts containing field name and
    a regex used to validate that field.
    '''

    # Finds all errors, and then alerts the user.
    errors = set()
    for entry in data:
      for field in field_list:
        if not field['regex'].match(entry[field['field']]):
          errors.add(field['name'])
    
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
    value.
    '''

    data = []

    # HTML forms use carriage returns, apparently.
    for line in new_members_data.split('\r\n'):
      if line == "":
        continue

      values = line.split(',')
      if len(values) != len(field_list):
        flash("Invalid data submitted")
        return False

      # Skip title line if present
      if values[0] == field_list[0]['name']:
        continue

      entry = {}
      for i in range(len(field_list)):
        field = field_list[i]
        entry[field['field']] = values[i]
      data.append(entry)

    if validate_data(data, field_list):
      return data
    else:
      return False

  def add_new_members(data):
    ''' 
    This adds the members to the database and them emails them with 
    account creation information. Assumes data has already been validated. 
    '''

    insert_query = text("INSERT INTO members (fname, lname, uid, \
        matriculate_year, grad_year, email) VALUES (:fname, :lname, :uid, \
        :matriculate_year, :grad_year, :email)")
    check_query = text("SELECT COUNT(*) FROM members WHERE uid=:uid")
    last_insert_id_query = text("SELECT LAST_INSERT_ID()")

    members_added_count = 0
    members_skipped_count = 0
    members_errors_count = 0

    for entry in data:
      # Check if user is in database already
      r = connection.execute(check_query, uid=entry['uid'])
      result = fetch_all_results(r)
      count = result[0]['COUNT(*)']

      if count != 0:
        members_skipped_count += 1
        continue

      # Get the graduation year
      matriculate_year = int(entry['matriculate_year'])
      grad_year = matriculate_year + 4

      # Add the user to the database.
      result = connection.execute(insert_query, fname=entry['fname'], \
          lname=entry['lname'], uid=entry['uid'], \
          matriculate_year=matriculate_year, grad_year=grad_year, \
          email=entry['email'])

      # Get the id of the inserted row (used to create unique hash).
      r = connection.execute(last_insert_id_query)
      result = fetch_all_results(r)
      user_id = result[0]["LAST_INSERT_ID()"]

      user_hash = create_account_hash(user_id, entry['uid'], entry['fname'], \
          entry['lname'])
      name = entry['fname'] + ' ' + entry['lname']

      # Email the user
      subject = "[RuddWeb] Welcome to the Ruddock House Website!"
      msg = "Hey " + name + ",\n\n" + \
          "You have been added to the Ruddock House Website. In order to " + \
          "access private areas of our site, please complete " + \
          "registration by creating an account here:\n" + \
          url_for('create_account', k=user_hash, u=user_id, _external=True) + \
          "\n\n" + \
          "Thanks!\n" + \
          "The Ruddock IMSS Team\n\n" + \
          "PS: If you have any questions or concerns, please contact us at imss@ruddock.caltech.edu"
      to = entry['email']

      try:
        sendEmail(to, msg, subject)
        members_added_count += 1

      except Exception as e:
        sendEmail("imss@ruddock.caltech.edu",
            "Something went wrong when trying to email " + name + ". " + \
            "You should look into this.\n\n" + \
            "Exception: " + str(e), 
            "[RuddWeb] Add members email error")

        members_errors_count += 1

    flash(str(members_added_count) + " members were successfully added, " +
        str(members_skipped_count) + " members were skipped, and " +
        str(members_errors_count) + " members encountered errors.")

  ### End helper function definitions ###

  PATH_TO_TEMPLATE = "/static/new_members_template.csv"
  TEMPLATE_FILENAME = PATH_TO_TEMPLATE.split('/')[-1]

  field_list = [
    { 'field':'fname', 
      'regex':re.compile(r"^[a-zA-Z][a-zA-Z '-]{0,14}[a-zA-Z]$"),
      'name':'First Name'},
    { 'field':'lname',
      'regex':re.compile(r"^[a-zA-Z][a-zA-Z '-]{0,14}[a-zA-Z]$"),
      'name':'Last Name'},
    { 'field':'uid',
      'regex':re.compile(r'^[0-9]{7}$'),
      'name':'UID'},
    { 'field':'matriculate_year',
      # Year must be betwen 1901 and 2155 (MySQL year standard)
      'regex':re.compile(r'^(19[0-9]{2}|2(0[0-9]{2}|1[0-5][0-9]))$'),
      'name':'Matriculation Year'},
    { 'field':'email',
      'regex':re.compile(r'^[a-zA-Z0-9\.\_\%\+\-]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,4}$'),
      'name':'Email'}]

  state = 'provide_data'
  if request.method == 'POST' and request.form['state']:
    state = request.form['state']

  if state == 'preview' or state == 'confirmed':
    new_members_data = request.form['new_members_data']
    data = process_data(new_members_data, field_list)

    if data:
      if state == 'preview':
        return render_template('new_members.html', state='preview', data=data, \
            field_list=field_list, raw_data=new_members_data)
      else:
        add_new_members(data)

  query = text("SELECT * FROM members WHERE fname=:fn AND lname=:ln")
  result = connection.execute(query, fn='daniel', ln='kongasldkfjalskdfj')

  return render_template('new_members.html', state='provide_data', \
      path=PATH_TO_TEMPLATE, filename=TEMPLATE_FILENAME)

if __name__ == "__main__":
  app.debug = True
  app.run()
