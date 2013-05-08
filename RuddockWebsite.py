from flask import Flask, request, session, g, redirect, url_for, abort, \
        render_template, flash
from ordereddict import OrderedDict
from sqlalchemy import create_engine, MetaData, text
import config, auth
import datetime
from time import strftime
from email_utils import sendEmail

app = Flask(__name__)
app.debug = True
app.secret_key = config.SECRET_KEY

""" Connect to the mySQL database. """
engine = create_engine(config.DB_URI, convert_unicode=True)
connection = engine.connect()

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
    if 'username' not in session:
      flash('You did something naughty')
      return redirect(url_for('forgot_passwd'))
    new_password = request.form['password']
    new_password2 = request.form['password2']

    # Get the user's email
    query = text("SELECT email FROM members WHERE user_id=:id")
    result = connection.execute(query, id=str(session['user_id']))
    email = result.first()[0]

    if new_password != new_password2:
      flash('Passwords do not match. Please try again!')
      return render_template('reset_password.html')
    elif auth.passwd_reset(session['username'], new_password, connection, \
                           email=email):
      session.pop('username')
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
        session['username'] = q_dict['username']
        return render_template('reset_password.html')
      flash("Incorrect reset_key. Try generating the link again?")
    return redirect(url_for('forgot_passwd'))

@app.route('/change-password', methods=['GET', 'POST'])
def change_passwd():
  """ Procedure to process the password reset page. """
  if 'username' not in session:
    flash('You must be logged in for that.')
    return redirect(url_for('login'))

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
def show_users():
  """ Procedure to show a list of all users, with all membership details. """
  # store which columns we want, and their displaynames
  cols = ["user_id", "lname", "fname", "email", "matriculate_year", \
          "grad_year", "major"]
  display = ["ID", "Last", "First", "Email", "Matr.", "Grad.", "Major"]
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

  # perform query
  query = text("SELECT * FROM members ORDER BY " + ordField + " " + ordDirect)
  results = connection.execute(query)

  # put results in a dictionary
  result_cols = results.keys()
  res = []
  for result in results:
    temp_dict = {}
    for i,key in enumerate(result_cols):
      if key in cols:
        temp_dict[key] = result[i]
    res.append(temp_dict)

  # we also want to map ids to usernames so we can link to individual pages
  query = text("SELECT user_id, username FROM users")
  results = connection.execute(query)
  idMap = dict(list(results)) # key is id, value is username

  return render_template('userlist.html', data = res, fields = cols, \
      displays = display, idMap=idMap, fieldMap=fieldMap)

@app.route('/users/view/<username>')
def show_user_profile(username):
  """ Procedure to show a user's profile and membership details. """
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
    return render_template('view_user.html', display = d_dict, info = q_dict, \
      strftime = strftime)
  else:
    flash("User does not exist!")
    return redirect(url_for('home'))

@app.route('/users/edit/<username>', methods=['GET', 'POST'])
def change_user_settings(username):
  """ Procedure to process the login page. Also handles authentication. """

  if 'username' not in session:
    flash('You must be logged in for that.')
    return redirect(url_for('login'))

  if session['username'] != username:
    flash('You cannot edit this user\'s information.')
    return redirect(url_for('show_user_profile', username=username))


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


    for (i, tag) in enumerate(tags):
      if str(params[tag]) != str(stored_params[tag]):

        new_val = str(params[tag])
        if tag in ['usenickname', 'msc', 'room_num', 'isabroad']:
          new_val = int(new_val)

        query = text("UPDATE members SET %s = :val WHERE user_id = :u" % tag)
        results = connection.execute(query, u=session['user_id'], val=new_val)

        flash("%s was updated!" % tag_names[i])


  if not params:
    params = stored_params

  return render_template('edit_user.html', params = params)

@app.route('/government')
def show_gov():
  return render_template('government.html')

@app.route('/about_us')
def show_about_us():
  return render_template('about_us.html')

@app.route('/news')
def show_news():
  return render_template('news.html')

@app.route('/calendar')
def show_calendar():
  return render_template('calendar.html')

@app.route('/map')
def show_map():
  return render_template('map.html')

if __name__ == "__main__":
  app.debug = True
  app.run()
