from flask import Blueprint, render_template, redirect, flash, url_for, request, g
from decorators import *
from constants import *
from helpers import *

# TODO: Shouldn't need these lines once move helper functions
from sqlalchemy import text
from email_utils import sendEmail

blueprint = Blueprint('admin', __name__, template_folder='templates')

@blueprint.route('/admin', methods=['GET', 'POST'])
@login_required(Permissions.Admin)
def admin_home():
  '''
  Loads a home page for admins, providing links to various tools.
  '''

  admin_tools = []

  if auth.check_permission(Permissions.UserAdmin):
    admin_tools.append({
      'name': 'Add new members',
      'link': url_for('admin.add_members', _external=True)})
    admin_tools.append({
      'name': 'Send account creation reminder',
      'link': url_for('admin.send_reminder_emails', _external=True)})

  if auth.check_permission(Permissions.HassleAdmin):
    admin_tools.append({
      'name': 'Room hassle',
      'link': url_for('hassle.run_hassle', _external=True)})
  return render_template('admin.html', tools=admin_tools)

@blueprint.route('/admin/reminder_email', methods=['GET', 'POST'])
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
    return redirect(url_for('admin.admin_home'))
  elif state == 'no':
    return redirect(url_for('admin.admin_home'))
  else:
    return render_template('create_account_reminder.html', data=data)

@blueprint.route('/admin/add_members', methods=['GET', 'POST'])
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
    and one of (full, social, associate).
    '''

    full_regex = re.compile(r'^full(| member)$', re.I)
    social_regex = re.compile(r'^social(| member)$', re.I)
    assoc_regex = re.compile(r'^associate(| member)$', re.I)

    if full_regex.match(membership_desc):
      return 1
    elif social_regex.match(membership_desc):
      return 2
    elif assoc_regex.match(membership_desc):
      return 3
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

    insert_query = text("INSERT INTO members (fname, lname, uid, \
        matriculate_year, grad_year, email, membership_type) \
        VALUES (:fname, :lname, :uid, :matriculate_year, :grad_year, \
        :email, :membership_type)")
    check_query = text("SELECT COUNT(*) FROM members WHERE uid=:uid")
    last_insert_id_query = text("SELECT LAST_INSERT_ID()")

    members_added_count = 0
    members_skipped_count = 0
    members_errors_count = 0

    for entry in data:
      # Check if user is in database already
      r = g.db.execute(check_query, uid=entry['uid'])
      result = fetch_all_results(r)
      count = result[0]['COUNT(*)']

      if count != 0:
        members_skipped_count += 1
        continue

      membership_type = convert_membership_type(entry['membership_type'])

      # Add the user to the database.
      result = g.db.execute(insert_query, fname=entry['fname'], \
          lname=entry['lname'], uid=entry['uid'], \
          matriculate_year=entry['matriculate_year'], \
          grad_year=entry['grad_year'], email=entry['email'], \
          membership_type=membership_type)

      # Get the id of the inserted row (used to create unique hash).
      r = g.db.execute(last_insert_id_query)
      result = fetch_all_results(r)
      user_id = result[0]["LAST_INSERT_ID()"]

      user_hash = create_account_hash(user_id, entry['uid'], entry['fname'], \
          entry['lname'])
      entry['name'] = entry['fname'] + ' ' + entry['lname']

      # Email the user
      subject = "Welcome to the Ruddock House Website!"
      msg = "Hey " + entry['name'] + ",\n\n" + \
          "You have been added to the Ruddock House Website. In order to " + \
          "access private areas of our site, please complete " + \
          "registration by creating an account here:\n" + \
          url_for('create_account', k=user_hash, u=user_id, _external=True) + \
          "\n\n" + \
          "Thanks!\n" + \
          "The Ruddock IMSS Team\n\n" + \
          "PS: If you have any questions or concerns, please contact us " + \
          "at imss@ruddock.caltech.edu"
      to = entry['email']

      try:
        sendEmail(to, msg, subject)
        members_added_count += 1

      except Exception as e:
        sendEmail("imss@ruddock.caltech.edu",
            "Something went wrong when trying to email " + entry['name'] + \
            ". You should look into this.\n\n" + \
            "Exception: " + str(e),
            "Add members email error")

        members_errors_count += 1

    flash(str(members_added_count) + " members were successfully added, " +
        str(members_skipped_count) + " members were skipped, and " +
        str(members_errors_count) + " members encountered errors.")

    # Remind admin to add users to mailing lists.
    flash("IMPORTANT: Don't forget to add the new members to manual " + \
        "email lists, like spam@ruddock!")

    # Send an email to IMSS to alert them that users have been added.
    to = "imss@ruddock.caltech.edu"
    subject = "Members were added to the Ruddock Website"
    msg = "Hey,\n\n" + \
        "The following members have been added to the Ruddock Website:\n\n"
    for entry in data:
      msg += entry['name'] + '\n'

    msg += "\nYou should run the email update script to add the new " + \
        "members.\n\n" + \
        "Thanks!\n" + \
        "The Ruddock Website"
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


