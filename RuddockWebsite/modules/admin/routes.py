from flask import render_template, redirect, flash, url_for, request

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

@blueprint.route('/add_members', methods=['GET', 'POST'])
@login_required(constants.Permissions.UserAdmin)
def add_members():
  '''
  Provides a form to add new members to the website, and then emails the
  new members a unique link to create an account.
  '''

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
      raw_data = helpers.get_raw_data(field_list)
    else:
      if request.files.has_key('new_members_file'):
        new_members_file = request.files['new_members_file']
        raw_data = new_members_file.read()
      else:
        raw_data = False
    if raw_data:
      data = helpers.add_members_process_data(raw_data, field_list)
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

