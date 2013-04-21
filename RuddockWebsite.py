from flask import Flask, request, session, g, redirect, url_for, abort, \
        render_template, flash

app = Flask(__name__)

@app.route('/')
def index():
  return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        raise NotImplementedError('Database not implemented. Yell at admins.')
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out.')
    return redirect(url_for('index'))

@app.route('/users')
def show_users():
    """ Procedure to show a list of all users, with all membership details. """
    print "test"
    return engine.execute("SELECT * FROM users").first()
    # return render_template('userlist.html')

@app.route('/users/view/<username>')
def show_user_profile():
    """ Procedure to show a user's profile and membership details. """
    return render_template('view_user.html')

if __name__ == "__main__":
  app.run()
