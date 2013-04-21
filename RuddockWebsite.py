from flask import Flask, request, session, g, redirect, url_for, abort, \
        render_template, flash
from sqlalchemy import create_engine, MetaData
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
      return render_template('login.html', msg='Incorrect username or ' + \
              ' password. Please try again!')

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
      return render_template('password_change.html', msg='Wrong old password!')
    if new_password != new_password2:
      return render_template('password_change.html', msg='Passwords mismatch!')
    elif auth.passwd_reset(username, new_password, connection):
      return redirect(url_for('home'))
    else:
      return render_template('password_change.html', msg='Unknown problem' + \
              ' occured. Please contact an admin!')

  return render_template('password_change.html')

@app.route('/logout')
def logout():
  session.pop('username', None)
  return redirect(url_for('home'))

@app.route('/users')
def show_users():
  """ Procedure to show a list of all users, with all membership details. """
  return render_template('userlist.html')

@app.route('/users/view/<username>')
def show_user_profile():
  """ Procedure to show a user's profile and membership details. """
  return render_template('view_user.html')

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
