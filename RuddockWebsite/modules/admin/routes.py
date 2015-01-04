import tempfile
from flask import render_template, redirect, flash, url_for, request, g
from RuddockWebsite import auth_utils, constants
from RuddockWebsite.decorators import login_required
from RuddockWebsite.modules.admin import blueprint, helpers

@blueprint.route('/', methods=['GET', 'POST'])
@login_required(constants.Permissions.Admin)
def admin_home():
  '''
  Loads a home page for admins, providing links to various tools.
  '''
  admin_tools = []
  if auth_utils.check_permission(constants.Permissions.UserAdmin):
    admin_tools.append({
      'name': 'Add new members',
      'link': url_for('admin.add_members', _external=True)})
    admin_tools.append({
      'name': 'Send account creation reminder',
      'link': url_for('admin.send_reminder_emails', _external=True)})

  if auth_utils.check_permission(constants.Permissions.HassleAdmin):
    admin_tools.append({
      'name': 'Room hassle',
      'link': url_for('hassle.run_hassle', _external=True)})
  return render_template('admin.html', tools=admin_tools)

@login_required(constants.Permissions.UserAdmin)
@blueprint.route('/members/add')
def add_members():
  ''' Displays a form to add new members. '''
  return render_template('add_members.html')

@login_required(constants.Permissions.UserAdmin)
@blueprint.route('/members/add/single/submit', methods=['POST'])
def add_members_single_submit():
  ''' Submission endpoint for adding a single member. '''
  fname = request.form.get('fname', '')
  lname = request.form.get('lname', '')
  matriculate_year = request.form.get('matriculate_year', '')
  grad_year = request.form.get('grad_year', '')
  uid = request.form.get('uid', '')
  email = request.form.get('email', '')
  membership_desc = request.form.get('membership_desc', '')

  # Check that data was valid.
  new_member = helpers.NewMember(fname, lname, matriculate_year, grad_year,
      uid, email, membership_desc)
  new_member_list = helpers.NewMemberList([new_member])
  if not new_member_list.validate_data():
    return redirect(url_for('admin.add_members'))

  # Pass along request data in the g object, and then redirect to the
  # confirmation page.
  g.new_member_list = new_member_list
  return redirect(url_for('admin.add_members_confirm'))

@login_required(constants.Permissions.UserAdmin)
@blueprint.route('/members/add/multi/submit', methods=['POST'])
def add_members_multi_submit():
  ''' Submission endpoint for adding multiple members at a time. '''
  new_members_file = request.files.get('new_members_file', None)
  if new_members_file is None:
    flash("You must upload a file!")
    return redirect(url_for('admin.add_members'))
  # Save the file to a tempfile so we can parse it.
  f = tempfile.NamedTemporaryFile()
  f.write(new_members_file.read())
  f.flush()
  # Parse and validate the data.
  new_member_list = helpers.NewMemberList()
  if new_member_list.parse_csv_file(f.name):
    if new_member_list.validate_data():
      # Pass along request data in the g object and redirect to the
      # confirmation page.
      g.new_member_list = new_member_list
      return redirect(url_for('admin.add_members_confirm'))
  # Errors were found.
  return redirect(url_for('admin.add_members'))

@login_required(constants.Permissions.UserAdmin)
@blueprint.route('/members/add/confirm')
def add_members_confirm():
  '''
  Displays a confirmation page for adding new members. This endpoint MUST be
  called as a redirect from one of the submit endpoints above and cannot be
  called from the URL alone.

  Expects g.new_member_list to be a NewMemberList object with valid data.
  '''
  new_member_list = getattr(g, 'new_member_list', None)
  print new_member_list
  if new_member_list is None:
    # This is the case if someone tries to manually go to the URL for this
    # endpoint.
    flash("Invalid request.")
    return redirect(url_for('home'))
  return render_template('add_members_confirm.html',
      new_member_list=new_member_list)

@login_required(constants.Permissions.UserAdmin)
@blueprint.route('/members/add/confirm/submit', methods=['POST'])
def add_members_confirm_submit():
  ''' Handles new member creation. '''
  # Expects new member data to be passed as a CSV string.
  new_member_data = request.form.get('new_member_data', None)
  # Silently verify data. There shouldn't be any errors if everything is being
  # used as intended.
  new_member_list = helpers.NewMemberList()
  if new_member_list.parse_csv_string(new_member_data):
    if new_member_list.validate_data(flash_errors=False):
      new_member_list.add_members()
      return redirect(url_for('admin.add_members'))
  # An error happened somewhere.
  flash("An unexpected error was encountered. Please find an IMSS rep.")
  return redirect(url_for('admin.add_members'))

@blueprint.route('/reminder_email', methods=['GET', 'POST'])
@login_required(constants.Permissions.UserAdmin)
def send_reminder_emails():
  '''
  Sends a reminder email to all members who have not yet created
  an account.
  '''
  data = helpers.get_members_without_accounts()
  state = None
  if request.method == 'POST' and request.form['state']:
    state = request.form['state']
  if state == 'yes':
    for member in data:
      helpers.send_reminder_email(member['fname'], \
          member['lname'], member['email'], member['user_id'], member['uid'])
    flash('Sent reminder emails to ' + str(len(data)) + ' member(s).')
    return redirect(url_for('admin.admin_home'))
  elif state == 'no':
    return redirect(url_for('admin.admin_home'))
  else:
    return render_template('create_account_reminder.html', data=data)
