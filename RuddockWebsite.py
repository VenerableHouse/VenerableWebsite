from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash
from collections import OrderedDict
from sqlalchemy import create_engine, MetaData, text
from time import strftime
from email_utils import sendEmail
from constants import *
from decorators import *
from common_helpers import *
import datetime
import re
import config
import auth

# Import blueprint modules
from modules.hassle.routes import blueprint as hassle_blueprint
from modules.admin.routes import blueprint as admin_blueprint

app = Flask(__name__)
app.debug = False
app.secret_key = config.SECRET_KEY

# Maximum file upload size, in bytes.
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Load blueprint modules
app.register_blueprint(hassle_blueprint, url_prefix='/hassle')
app.register_blueprint(admin_blueprint, url_prefix='/admin')

# Create database engine object.
engine = create_engine(config.DB_URI, convert_unicode=True)

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

@app.route('/login', methods=['GET', 'POST'])
def login():
  """ Procedure to process the login page. Also handles authentication. """
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']

    user_id = auth.authenticate(username, password)
    if user_id:
      permissions = auth.get_permissions(username)
      session['username'] = request.form['username']
      session['user_id'] = user_id
      session['permissions'] = permissions
      # True if there's any reason to show a link to the admin interface.
      session['show_admin'] = auth.check_permission(Permissions.Admin)

      # Update last login time.
      auth.update_last_login(username)

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
    result = g.db.execute(query, u=str(username))
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
        sendEmail(str(email), msg, "Forgotten Password")
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
    result = g.db.execute(query, username=str(session['r_username']))
    email = result.first()[0]

    if new_password != new_password2:
      flash('Passwords do not match. Please try again!')
      return render_template('reset_password.html')
    elif new_password == '':
      flash('Passwords cannot be empty. Please try again!')
      return render_template('reset_password.html')
    elif auth.passwd_reset(session['r_username'], new_password, email=email):
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
    result = g.db.execute(query, u=str(user_id))
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
    result = g.db.execute(query, id=str(session['user_id']))
    email = result.first()[0]

    if not auth.authenticate(username, old_password):
      flash('Wrong old password. Please try again!')
      return render_template('password_change.html')
    if new_password != new_password2:
      flash('New passwords do not match. Please try again!')
      return render_template('password_change.html')
    elif new_password == '':
      flash('Passwords cannot be empty. Please try again!')
      return render_template('password_change.html')
    elif auth.passwd_reset(username, new_password, email=email):
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

  if d_dict_user != None and q_dict_user != None:
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
    r = g.db.execute(query, username=data['username'])
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
    r = g.db.execute(query, user_id=user_id)
    result = fetch_all_results(r)

    return result[0]

  def check_key_id_pair(key, user_id):
    # Check that the user_id is valid.
    query = text("SELECT COUNT(*) FROM members WHERE user_id=:user_id")
    r = g.db.execute(query, user_id=user_id)
    result = fetch_all_results(r)
    count = result[0]['COUNT(*)']

    if count != 1:
      return False

    # Make sure an account does not already exist for that user_id.
    query = text("SELECT COUNT(*) FROM users WHERE user_id=:user_id")
    r = g.db.execute(query, user_id=user_id)
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
    g.db.execute(query, user_id=user_id, username=username, \
        password='')

    # Use the password reset function to set the password, to ensure
    # consistent salting.
    auth.passwd_reset(username, password, salt=True, email=False)

    # Email the user to let them know an account has been created.
    subject = "Thanks for creating an account!"
    msg = "You have just created an account on the Ruddock website with " + \
        "the username \"" + username + "\".\n" + \
        "If this was not you, please email imss@ruddock.caltech.edu immediately.\n\n" + \
        "Thanks!\n" + \
        "The Ruddock IMSS Team"
    to = email
    sendEmail(to, msg, subject)

  def update_birthday(user_id, birthday):
    query = text("UPDATE members SET bday=:bday WHERE user_id=:user_id")
    g.db.execute(query, bday=birthday, user_id=user_id)

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

if __name__ == "__main__":
  app.run()
