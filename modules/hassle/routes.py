from flask import Blueprint, render_template, redirect, flash, url_for, request
from decorators import *
from constants import *

import helpers as hassle_helpers

blueprint = Blueprint('hassle', __name__)

@blueprint.route('/hassle')
@login_required(Permissions.HassleAdmin)
def run_hassle():
  ''' Logic for room hassles. '''

  available_participants = hassle_helpers.get_available_participants()
  available_rooms = hassle_helpers.get_available_rooms()
  events = hassle_helpers.get_events_with_roommates()
  alleys = [1, 2, 3, 4, 5, 6]

  return render_template('hassle.html',
      available_participants=available_participants,
      available_rooms=available_rooms,
      events=events,
      alleys=alleys)

@blueprint.route('/hassle/event', methods=['POST'])
@login_required(Permissions.HassleAdmin)
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
      hassle_helpers.new_event(user_id, room_number, roommates)
  return redirect(url_for('hassle.run_hassle'))

@blueprint.route('/hassle/restart', defaults={'event_id': None})
@blueprint.route('/hassle/restart/<int:event_id>')
@login_required(Permissions.HassleAdmin)
def hassle_restart(event_id):
  if event_id == None:
    hassle_helpers.clear_events()
  else:
    hassle_helpers.clear_events(event_id)
  return redirect(url_for('hassle.run_hassle'))

@blueprint.route('/hassle/new')
@login_required(Permissions.HassleAdmin)
def new_hassle():
  ''' Redirects to the first page to start a new room hassle_helpers. '''

  # Clear old data.
  hassle_helpers.clear_all()

  return redirect(url_for('hassle.new_hassle_participants'))

@blueprint.route('/hassle/new/participants')
@login_required(Permissions.HassleAdmin)
def new_hassle_participants():
  ''' Select participants for the room hassle_helpers. '''

  # Get a list of all current members.
  members = hassle_helpers.get_all_members()
  return render_template('hassle_new_participants.html', members=members)

@blueprint.route('/hassle/new/participants/submit', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def new_hassle_participants_submit():
  ''' Submission endpoint for hassle participants. Redirects to next page. '''

  # Get a list of all participants' user IDs.
  participants = map(lambda x: int(x), request.form.getlist('participants'))
  # Update database with this hassle's participants.
  hassle_helpers.set_participants(participants)
  return redirect(url_for('hassle.new_hassle_rooms'))

@blueprint.route('/hassle/new/rooms')
@login_required(Permissions.HassleAdmin)
def new_hassle_rooms():
  ''' Select rooms available for the room hassle_helpers. '''

  # Get a list of all rooms.
  rooms = hassle_helpers.get_all_rooms()
  return render_template('hassle_new_rooms.html', rooms=rooms)

@blueprint.route('/hassle/new/rooms/submit', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def new_hassle_rooms_submit():
  ''' Submission endpoint for hassle rooms. Redirects to next page. '''

  # Get a list of all room numbers.
  rooms = map(lambda x: int(x), request.form.getlist('rooms'))
  # Update database with participating rooms.
  hassle_helpers.set_rooms(rooms)
  return redirect(url_for('hassle.new_hassle_confirm'))

@blueprint.route('/hassle/new/confirm')
@login_required(Permissions.HassleAdmin)
def new_hassle_confirm():
  ''' Confirmation page for new room hassle_helpers. '''

  participants = hassle_helpers.get_participants()
  rooms = hassle_helpers.get_participating_rooms()

  return render_template('hassle_new_confirm.html', rooms=rooms, \
      participants=participants)

@blueprint.route('/hassle/new/confirm/submit', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def new_hassle_confirm_submit():
  ''' Submission endpoint for confirmation page. '''

  # Nothing to do, everything is already in the database.
  return redirect(url_for('hassle.run_hassle'))

