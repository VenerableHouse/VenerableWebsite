import os
import flask

from ruddock import app
from ruddock import constants
from ruddock import email_utils
from ruddock.auth_utils import is_full_member
from ruddock.decorators import login_required
try:
  from ruddock import secrets
except ImportError:
  from ruddock import default_secrets as secrets

def _president_message_recipient():
  # FOR TESTING
  return "asharma3@caltech.edu"
  
  """Resolve outbound address: env override, then config, else webmaster, except test."""
  env_to = (os.environ.get('RUDDWEB_PRESIDENT_MESSAGE_TO') or '').strip()
  if env_to:
    return env_to
  cfg = flask.current_app.config.get('PRESIDENT_MESSAGE_TO')
  if cfg is not None and str(cfg).strip():
    return str(cfg).strip()
  if flask.current_app.config.get('TESTING'):
    return None
  return 'imss@venerable.caltech.edu'

@app.route('/')
def home():
  """The homepage of the site."""
  return flask.render_template('index.html')

@app.route('/info')
@login_required()
def show_info():
  """Shows info page on door combos, printers, etc."""
  return flask.render_template('info.html',
    full_member=is_full_member(flask.session['username']),
    secrets=secrets)

@app.route('/contact')
def show_contact():
  """Shows Contact Us page."""
  return flask.render_template('contact.html')

@app.route('/contact/president-message', methods=['GET', 'POST'])
@login_required()
def president_message():
  """Anonymous message to the House President (login required; email only)."""
  if flask.request.method == 'POST':
    subject = (flask.request.form.get('subject') or '').strip()
    body = (flask.request.form.get('body') or '').strip()
    errors = []
    if not subject:
      errors.append('Subject is required.')
    elif len(subject) > constants.PRESIDENT_MESSAGE_SUBJECT_MAX_LEN:
      errors.append('Subject is too long.')
    if not body:
      errors.append('Message is required.')
    elif len(body) > constants.PRESIDENT_MESSAGE_BODY_MAX_LEN:
      errors.append('Message is too long.')
    if errors:
      for err in errors:
        flask.flash(err)
      return flask.render_template('president_message.html',
          subject=subject, body=body,
          subject_max=constants.PRESIDENT_MESSAGE_SUBJECT_MAX_LEN,
          body_max=constants.PRESIDENT_MESSAGE_BODY_MAX_LEN)

    to = _president_message_recipient()
    if not to:
      flask.flash(
          'Your message could not be sent. Please contact the webmaster.')
      return flask.render_template('president_message.html',
          subject=subject, body=body,
          subject_max=constants.PRESIDENT_MESSAGE_SUBJECT_MAX_LEN,
          body_max=constants.PRESIDENT_MESSAGE_BODY_MAX_LEN)

    msg = (
        'An anonymous message was submitted via venerable.caltech.edu/contact/president-message:\n\n'
        'Subject: ' + subject + '\n\n' + body + '\n')
    email_utils.send_email(to, msg, subject)
    flask.flash('Your message was sent.')
    return flask.redirect(flask.url_for('president_message'))

  return flask.render_template('president_message.html', subject='', body='',
      subject_max=constants.PRESIDENT_MESSAGE_SUBJECT_MAX_LEN,
      body_max=constants.PRESIDENT_MESSAGE_BODY_MAX_LEN)
