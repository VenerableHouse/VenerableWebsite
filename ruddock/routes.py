import os

import flask

from ruddock import app
from ruddock import constants
from ruddock import email_utils
from ruddock.auth_utils import is_full_member
from ruddock.decorators import login_required
from ruddock.resources import ANONYMOUS_CONTACT_ROLES
try:
  from ruddock import secrets
except ImportError:
  from ruddock import default_secrets as secrets

def _resolve_anonymous_recipient_addresses(role_keys):
  """
  Map whitelisted role keys to email addresses, deduped in stable order.
  In TESTING, if PRESIDENT_MESSAGE_TO or RUDDWEB_PRESIDENT_MESSAGE_TO is set,
  replace with a single-address list for a dev sink; if unset, return None.
  """
  addrs = []
  seen = set()
  for key in role_keys:
    email_addr = ANONYMOUS_CONTACT_ROLES.get(key)
    if email_addr and email_addr not in seen:
      seen.add(email_addr)
      addrs.append(email_addr)

  if flask.current_app.config.get('TESTING'):
    env_override = (os.environ.get('RUDDWEB_PRESIDENT_MESSAGE_TO') or '').strip()
    cfg = flask.current_app.config.get('PRESIDENT_MESSAGE_TO')
    cfg_to = str(cfg).strip() if cfg is not None and str(cfg).strip() else ''
    override = env_override or cfg_to
    if override:
      return [override]
    return None
  return addrs


def _contact_form_context(form_name='', form_email='', form_message=''):
  return dict(
      message_max=constants.ANONYMOUS_CONTACT_MESSAGE_MAX_LEN,
      name_max=constants.ANONYMOUS_CONTACT_NAME_MAX_LEN,
      email_max=constants.ANONYMOUS_CONTACT_EMAIL_FIELD_MAX_LEN,
      form_name=form_name,
      form_email=form_email,
      form_message=form_message)

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
  return flask.render_template('contact.html', **_contact_form_context())

@app.route('/contact/anonymous', methods=['POST'])
def anonymous_contact_submit():
  """anonymous contact form: sends email directly to a subset of {president, excomm, hucc}."""
  name = (flask.request.form.get('name') or '').strip()
  email = (flask.request.form.get('email') or '').strip()
  message = (flask.request.form.get('message') or '').strip()
  role_keys = flask.request.form.getlist('recipients')

  ctx = _contact_form_context(name, email, message)
  errors = []

  if len(name) > constants.ANONYMOUS_CONTACT_NAME_MAX_LEN:
    errors.append('Name is too long.')
  if len(email) > constants.ANONYMOUS_CONTACT_EMAIL_FIELD_MAX_LEN:
    errors.append('Email is too long.')
  if not message:
    errors.append('Message is required.')
  elif len(message) > constants.ANONYMOUS_CONTACT_MESSAGE_MAX_LEN:
    errors.append('Message is too long.')

  unknown = [k for k in role_keys if k not in ANONYMOUS_CONTACT_ROLES]
  if unknown:
    errors.append('Invalid recipient selection.')

  resolved_keys = [k for k in role_keys if k in ANONYMOUS_CONTACT_ROLES]
  if not resolved_keys:
    errors.append('Select at least one recipient.')

  if errors:
    for err in errors:
      flask.flash(err)
    return flask.render_template('contact.html', **ctx)

  addrs = _resolve_anonymous_recipient_addresses(resolved_keys)
  if not addrs:
    flask.flash(
        'Your message could not be sent. Please contact the webmaster.')
    return flask.render_template('contact.html', **ctx)

  display_name = name if name else '(not provided)'
  display_email = email if email else '(not provided)'
  body = (
      'A message was submitted via venerable.caltech.edu/contact.\n\n'
      'Name: ' + display_name + '\n'
      'Email: ' + display_email + '\n\n'
      'Message:\n' + message + '\n')

  email_utils.send_email(
      addrs,
      body,
      constants.ANONYMOUS_CONTACT_MAIL_SUBJECT)
  flask.flash('Your message was sent.')
  return flask.redirect(flask.url_for('show_contact') + '#anonymous-contact')
