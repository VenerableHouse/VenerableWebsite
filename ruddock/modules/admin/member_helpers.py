import flask
import sqlalchemy

from ruddock import auth_utils
from ruddock import email_templates
from ruddock import email_utils
from ruddock import validation_utils

class NewMember:
  """Class containing data for adding a single new member."""
  def __init__(self, first_name, last_name, matriculation_year, graduation_year,
      uid, email, membership_desc):
    self.first_name = first_name
    self.last_name = last_name
    self.name = first_name + ' ' + last_name
    self.matriculation_year = matriculation_year
    self.graduation_year = graduation_year
    self.uid = uid
    self.email = email
    self.membership_desc = membership_desc
    # Membership type is set from the membership desc.
    self.member_type = None
    self.set_member_type()

  def __str__(self):
    """Converts to a CSV string."""
    return ','.join([self.first_name, self.last_name, self.matriculation_year, \
        self.graduation_year, self.uid, self.email, self.membership_desc])

  def validate_data(self, flash_errors=True):
    """
    Returns True if all data is valid. Otherwise, flashes error message(s) if
    requested and returns False.
    """
    # Find all errors, don't just stop at the first one found.
    is_valid = True
    if not validation_utils.validate_name(self.first_name, flash_errors):
      is_valid = False
    if not validation_utils.validate_name(self.last_name, flash_errors):
      is_valid = False
    if not validation_utils.validate_year(self.matriculation_year, flash_errors):
      is_valid = False
    if not validation_utils.validate_year(self.graduation_year, flash_errors):
      is_valid = False
    if not validation_utils.validate_uid(self.uid, flash_errors):
      is_valid = False
    if not validation_utils.validate_email(self.email, flash_errors):
      is_valid = False
    if self.member_type is None:
      if flash_errors:
        flask.flash("'{0}' is not a valid membership type. Try 'full', 'social', 'associate', or 'RA'.".format(self.membership_desc))
      is_valid = False
    return is_valid

  def add_member(self):
    """
    Adds this member to the database. Assumes data has already been validated.
    Returns True if successful, otherwise False.
    """
    # If the user is already in the database, skip this user.
    if validation_utils.check_uid_exists(self.uid):
      return False
    # Generate an account creation key.
    create_account_key = auth_utils.generate_create_account_key()
    query = sqlalchemy.text("""
      INSERT INTO members (first_name, last_name, matriculation_year, graduation_year,
        uid, email, member_type, create_account_key)
      VALUES (:first_name, :last_name, :matriculation_year, :graduation_year,
        :uid, :email, :member_type, :create_account_key)
      """)
    flask.g.db.execute(query, first_name=self.first_name,
        last_name=self.last_name,
        matriculation_year=self.matriculation_year,
        graduation_year=self.graduation_year,
        uid=self.uid,
        email=self.email,
        member_type=self.member_type,
        create_account_key=create_account_key)
    # Email the user.
    subject = "Welcome to the Ruddock House website!"
    msg = email_templates.AddedToWebsiteEmail.format(self.name,
        flask.url_for('account.create_account',
          create_account_key=create_account_key,
          _external=True))
    to = self.email
    email_utils.send_email(to, msg, subject)
    return True

  def set_member_type(self):
    """
    Takes a membership description (full, social, RA, etc) and sets the
    member_type and membership_desc attributes. If not successful, sets
    member_type to None.
    """
    query = sqlalchemy.text("""
      SELECT member_type, membership_desc_short
      FROM membership_types
      WHERE membership_desc = :d
        OR membership_desc_short = :d
      """)
    result = flask.g.db.execute(query, d=self.membership_desc).first()
    if result is not None:
      self.member_type = result['member_type']
      self.membership_desc = result['membership_desc_short']
    else:
      self.member_type = None
      # Don't set self.membership_desc, so we can print what the error was later.
    return

class NewMemberList:
  """
  Class containing all data for adding one or more new members. This class is a
  wrapper for a list of NewMember objects and associated methods.
  """
  def __init__(self, new_member_list=[]):
    self.new_member_list = new_member_list

  def __str__(self):
    """Returns data formatted as a CSV string."""
    return '\n'.join(str(new_member) for new_member in self.new_member_list)

  def validate_data(self, flash_errors=True):
    """
    Returns True if all data is valid. Otherwise, flashes error message(s) if
    requested and returns False.
    """
    # Check every set of new member data, don't stop at the first error.
    is_valid = True
    for new_member in self.new_member_list:
      if not new_member.validate_data(flash_errors):
        is_valid = False
    return is_valid

  def add_members(self):
    """Adds all members to the database. Assumes data to be valid."""
    # Keep track of which members were added and which were skipped.
    members_added = []
    members_skipped = []
    for new_member in self.new_member_list:
      if new_member.add_member():
        members_added.append(new_member.name)
      else:
        members_skipped.append(new_member.name)
    flask.flash("{0} member(s) were successfully added and {1} member(s) were skipped.".format(len(members_added), len(members_skipped)))
    # Email admins about added members.

    to = "imss@ruddock.caltech.edu, secretary@ruddock.caltech.edu"
    msg = email_templates.MembersAddedEmail.format(
        '\n'.join(members_added) if len(members_added) > 0 else '(none)',
        '\n'.join(members_skipped) if len(members_skipped) > 0 else '(none)')
    subject = 'Members were added to the Ruddock Website'
    # Don't use prefix since this is being sent to IMSS/Secretary, which have
    # their own prefixes.
    email_utils.send_email(to, msg, subject, use_prefix=False)

  def parse_csv_file(self, filename):
    """
    Parses a CSV file located at filename. Returns True if successful.
    This function does NOT validate the data.

    A good way to use this for user submitted data would be to save the data in
    a tempfile and then pass the tempfile's name here.
    """
    try:
      # Use universal newlines so all newlines are \n regardless of if the file
      # was originally made on a Unix or Windows system.
      f = open(filename, 'rU')
      contents = f.read()
      f.close()
    except IOError:
      flask.flash("An unexpected error occurred when trying to open the file.")
      return False
    return self.parse_csv_string(contents)

  def parse_csv_string(self, csv_string):
    """
    Parses a CSV string. Returns True if successful.
    This function does NOT validate the data.

    Expects newlines to be the standard Unix \n. Use universal newlines support
    if reading from a file.
    """
    # Get the template file's first line so we can skip it if encountered.
    template_filename = 'ruddock/static/admin/add_members_template.csv'
    try:
      template_file = open(template_filename, 'rU')
      template_header = template_file.readlines()[0].strip()
      template_file.close()
    except IOError, IndexError:
      # Something weird happened, but this shouldn't be fatal.
      template_header = ''

    # List of NewMember objects parsed.
    new_member_list = []
    for line in csv_string.split('\n'):
      # If this is the template's header, then we can safely skip it.
      # Also skip if the line is empty (newlines at the end, most likely).
      if line == template_header or line == '':
        continue
      # Split each line by commas, and then strip leading/trailing whitespace.
      data = [s.strip() for s in line.split(',')]
      try:
        first_name = data[0]
        last_name = data[1]
        matriculation_year = data[2]
        graduation_year = data[3]
        uid = data[4]
        email = data[5]
        membership_desc = data[6]
        # Ignore any additional columns. This is possible if Excel (or other
        # program) thought more columns were used than were actually touched,
        # and inserts extra commas at the end of the line.
      except IndexError:
        # Not enough columns.
        flask.flash("File does not seem to be in the same format as the template.")
        return False
      new_member = NewMember(first_name, last_name, matriculation_year, graduation_year, \
          uid, email, membership_desc)
      new_member_list.append(new_member)
    self.new_member_list = new_member_list
    return True
