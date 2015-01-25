from flask import render_template, redirect, flash, url_for, request

from RuddockWebsite import constants
from RuddockWebsite.decorators import login_required
from RuddockWebsite.modules.hassle import blueprint, helpers

@blueprint.route('/')
@login_required(constants.Permissions.HassleAdmin)
def run_hassle():
  ''' Logic for room hassles. '''

  available_participants = helpers.get_available_participants()
  available_rooms = helpers.get_available_rooms()
  events = helpers.get_events_with_roommates()
  alleys = [1, 2, 3, 4, 5, 6]

  return render_template('hassle.html',
      available_participants=available_participants,
      available_rooms=available_rooms,
      events=events,
      alleys=alleys)

@blueprint.route('/event', methods=['POST'])
@login_required(constants.Permissions.HassleAdmin)
def hassle_event():
  ''' Submission endpoint for a new event (someone picks a room). '''

  user_id = request.form.get('user_id', None)
  room_number = request.form.get('room', None)
  roommates = request.form.getlist('roommate_id')

  if user_id == None or room_number == None:
    flash("Invalid request - try again?")
  else:
    roommates = [r for r in roommates if r != "none"]

    # Check for invalid roommate selection.
    if user_id in roommates or len(roommates) != len(set(roommates)):
      flash("Invalid roommate selection.")
    else:
      helpers.new_event(user_id, room_number, roommates)
  return redirect(url_for('hassle.run_hassle'))

@blueprint.route('/restart', defaults={'event_id': None})
@blueprint.route('/restart/<int:event_id>')
@login_required(constants.Permissions.HassleAdmin)
def hassle_restart(event_id):
  if event_id == None:
    helpers.clear_events()
  else:
    helpers.clear_events(event_id)
  return redirect(url_for('hassle.run_hassle'))

@blueprint.route('/new')
@login_required(constants.Permissions.HassleAdmin)
def new_hassle():
  ''' Redirects to the first page to start a new room helpers. '''

  # Clear old data.
  helpers.clear_all()

  return redirect(url_for('hassle.new_hassle_participants'))

@blueprint.route('/new/participants')
@login_required(constants.Permissions.HassleAdmin)
def new_hassle_participants():
  ''' Select participants for the room helpers. '''

  # Get a list of all current members.
  members = helpers.get_all_members()
  return render_template('hassle_new_participants.html', members=members)

@blueprint.route('/new/participants/submit', methods=['POST'])
@login_required(constants.Permissions.HassleAdmin)
def new_hassle_participants_submit():
  ''' Submission endpoint for hassle participants. Redirects to next page. '''

  # Get a list of all participants' user IDs.
  participants = map(lambda x: int(x), request.form.getlist('participants'))
  # Update database with this hassle's participants.
  helpers.set_participants(participants)
  return redirect(url_for('hassle.new_hassle_rooms'))

@blueprint.route('/new/rooms')
@login_required(constants.Permissions.HassleAdmin)
def new_hassle_rooms():
  ''' Select rooms available for the room helpers. '''

  # Get a list of all rooms.
  rooms = helpers.get_all_rooms()
  return render_template('hassle_new_rooms.html', rooms=rooms)

@blueprint.route('/new/rooms/submit', methods=['POST'])
@login_required(constants.Permissions.HassleAdmin)
def new_hassle_rooms_submit():
  ''' Submission endpoint for hassle rooms. Redirects to next page. '''

  # Get a list of all room numbers.
  rooms = map(lambda x: int(x), request.form.getlist('rooms'))
  # Update database with participating rooms.
  helpers.set_rooms(rooms)
  return redirect(url_for('hassle.new_hassle_confirm'))

@blueprint.route('/new/confirm')
@login_required(constants.Permissions.HassleAdmin)
def new_hassle_confirm():
  ''' Confirmation page for new room helpers. '''

  participants = helpers.get_participants()
  rooms = helpers.get_participating_rooms()

  return render_template('hassle_new_confirm.html', rooms=rooms, \
      participants=participants)

@blueprint.route('/new/confirm/submit', methods=['POST'])
@login_required(constants.Permissions.HassleAdmin)
def new_hassle_confirm_submit():
  ''' Submission endpoint for confirmation page. '''

  # Nothing to do, everything is already in the database.
  return redirect(url_for('hassle.run_hassle'))

