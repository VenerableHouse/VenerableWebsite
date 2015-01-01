from flask import g, url_for, request, flash
from sqlalchemy import text
import re

from RuddockWebsite import common_helpers, email_utils

def get_members_without_accounts():
  '''
  Returns a list of dicts with the first name, last name, email, and
  user ID for everyone who hasn't made an account yet.
  '''

  query = text("SELECT fname, lname, email, uid, user_id FROM members \
      NATURAL LEFT JOIN users WHERE username IS NULL")
  r = g.db.execute(query)
  return common_helpers.fetch_all_results(r)

def send_reminder_email(fname, lname, email, user_id, uid):
  user_hash = common_helpers.create_account_hash(user_id, uid, fname, lname)
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

  email_utils.sendEmail(to, msg, subject)

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

def add_members_validate_data(data):
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

def add_members_process_data(new_members_data, field_list):
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
    if not add_members_validate_data(entry):
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
      email_utils.sendEmail(to, msg, subject)
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
    email_utils.sendEmail(to, msg, subject, usePrefix=False)

def add_members_get_raw_data(field_list):
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
