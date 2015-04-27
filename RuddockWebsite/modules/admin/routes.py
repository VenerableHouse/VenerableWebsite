import tempfile
from flask import render_template, redirect, flash, url_for, request, g, abort
from RuddockWebsite import auth_utils
from RuddockWebsite.constants import Permissions
from RuddockWebsite.decorators import login_required
from RuddockWebsite.modules.admin import blueprint, helpers

@blueprint.route('/')
@login_required()
def admin_home():
  '''
  Loads a home page for admins, providing links to various tools.
  '''
  links = auth_utils.generate_admin_links()
  # If there are no links, they have no business being here so we return an
  # access denied error.
  if len(links) == 0:
    abort(403)
  return render_template('admin.html', links=links)

@blueprint.route('/members/add')
@login_required(Permissions.ModifyUsers)
def add_members():
  ''' Displays a form to add new members. '''
  return render_template('add_members.html')

@blueprint.route('/members/add/single/confirm', methods=['POST'])
@login_required(Permissions.ModifyUsers)
def add_members_single_confirm():
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
  if new_member_list.validate_data():
    return render_template('add_members_confirm.html',
        new_member_list=new_member_list,
        data_string = str(new_member_list))
  return redirect(url_for('admin.add_members'))

@blueprint.route('/members/add/multi/confirm', methods=['POST'])
@login_required(Permissions.ModifyUsers)
def add_members_multi_confirm():
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
      return render_template('add_members_confirm.html',
          new_member_list=new_member_list,
          data_string = str(new_member_list))
  return redirect(url_for('admin.add_members'))

@blueprint.route('/members/add/confirm/submit', methods=['POST'])
@login_required(Permissions.ModifyUsers)
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
