from flask import Blueprint, render_template, redirect, flash, url_for, request
from decorators import *
from constants import *
import hassle

hassle_bp = Blueprint('hassle_bp', __name__)

@hassle_bp.route('/hassle')
@login_required(Permissions.HassleAdmin)
def run_hassle():
  ''' Logic for room hassles. '''

  available_participants = hassle.get_available_participants()
  available_rooms = hassle.get_available_rooms()
  events = hassle.get_events_with_roommates()
  alleys = [1, 2, 3, 4, 5, 6]

  return render_template('hassle.html',
      available_participants=available_participants,
      available_rooms=available_rooms,
      events=events,
      alleys=alleys)

@hassle_bp.route('/hassle/event', methods=['POST'])
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
      hassle.new_event(user_id, room_number, roommates)
  return redirect(url_for('hassle_bp.run_hassle'))

@hassle_bp.route('/hassle/restart', defaults={'event_id': None})
@hassle_bp.route('/hassle/restart/<int:event_id>')
@login_required(Permissions.HassleAdmin)
def hassle_restart(event_id):
  if event_id == None:
    hassle.clear_events()
  else:
    hassle.clear_events(event_id)
  return redirect(url_for('hassle_bp.run_hassle'))

@hassle_bp.route('/hassle/new')
@login_required(Permissions.HassleAdmin)
def new_hassle():
  ''' Redirects to the first page to start a new room hassle. '''

  # Clear old data.
  hassle.clear_all()

  return redirect(url_for('hassle_bp.new_hassle_participants'))

@hassle_bp.route('/hassle/new/participants')
@login_required(Permissions.HassleAdmin)
def new_hassle_participants():
  ''' Select participants for the room hassle. '''

  # Get a list of all current members.
  members = hassle.get_all_members()
  return render_template('hassle_new_participants.html', members=members)

@hassle_bp.route('/hassle/new/participants/submit', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def new_hassle_participants_submit():
  ''' Submission endpoint for hassle participants. Redirects to next page. '''

  # Get a list of all participants' user IDs.
  participants = map(lambda x: int(x), request.form.getlist('participants'))
  # Update database with this hassle's participants.
  hassle.set_participants(participants)
  return redirect(url_for('hassle_bp.new_hassle_rooms'))

@hassle_bp.route('/hassle/new/rooms')
@login_required(Permissions.HassleAdmin)
def new_hassle_rooms():
  ''' Select rooms available for the room hassle. '''

  # Get a list of all rooms.
  rooms = hassle.get_all_rooms()
  return render_template('hassle_new_rooms.html', rooms=rooms)

@hassle_bp.route('/hassle/new/rooms/submit', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def new_hassle_rooms_submit():
  ''' Submission endpoint for hassle rooms. Redirects to next page. '''

  # Get a list of all room numbers.
  rooms = map(lambda x: int(x), request.form.getlist('rooms'))
  # Update database with participating rooms.
  hassle.set_rooms(rooms)
  return redirect(url_for('hassle_bp.new_hassle_confirm'))

@hassle_bp.route('/hassle/new/confirm')
@login_required(Permissions.HassleAdmin)
def new_hassle_confirm():
  ''' Confirmation page for new room hassle. '''

  participants = hassle.get_participants()
  rooms = hassle.get_participating_rooms()

  return render_template('hassle_new_confirm.html', rooms=rooms, \
      participants=participants)

@hassle_bp.route('/hassle/new/confirm/submit', methods=['POST'])
@login_required(Permissions.HassleAdmin)
def new_hassle_confirm_submit():
  ''' Submission endpoint for confirmation page. '''

  # Nothing to do, everything is already in the database.
  return redirect(url_for('hassle_bp.run_hassle'))

