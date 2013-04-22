from flask import Flask, request, session, g, redirect, url_for, abort, \
        render_template, flash
from ordereddict import OrderedDict
from sqlalchemy import create_engine, MetaData, text
import config, auth

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

    if auth.authenticate(username, password, connection):
      session['username'] = request.form['username']
      return redirect(url_for('home'))
    else:
      flash('Incorrect username or password. Please try again!')
      return render_template('login.html')

  return render_template('login.html')

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

    if not auth.authenticate(username, old_password, connection):
      flash('Wrong old password. Please try again!')
      return render_template('password_change.html')
    if new_password != new_password2:
      flash('New passwords do not match. Please try again!')
      return render_template('password_change.html')
    elif auth.passwd_reset(username, new_password, connection):
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
  results = connection.execute('select * from members')
  keys = ['user_id', 'lname', 'fname', 'nickname', 'usenickname', 'bday', 'email', \
        'email2', 'status', 'matriculate_year', 'grad_year', 'msc', 'phone', 'building', \
        'room_num', 'membership', 'major', 'uid', 'isabroad']

  res = []
  for result in results:
    temp_dict = {}
    for i,key in enumerate(keys):
      temp_dict[key] = result[i]
    res.append(temp_dict)

  # get sorting arguments
  ordr = 'ordr' in request.args
  if 'attr' in request.args:
    attr = request.args['attr']
  else:
    attr = 'lname'

  return render_template('userlist.html', res = res, attr=attr, ordr=ordr)

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
  query = text("SELECT * FROM users Natural JOIN members where username=:u")
  result = connection.execute(query, u=str(username))
  if result.returns_rows and result.rowcount != 0:
    result_cols = result.keys()
    r = result.first()
    q_dict = dict(zip(result_cols, r)) #q_dict maps sql columns to values
    if not q_dict['usenickname']:
      d_dict.pop('Nickname')
    return render_template('view_user.html', display = d_dict, info = q_dict)
  else:
    flash("User does not exist!")
    return redirect(url_for('home'))

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

if __name__ == "__main__":
  app.debug = True
  app.run()
