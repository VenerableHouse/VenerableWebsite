import json
import flask

from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.hassle import blueprint, helpers

@blueprint.route('/')
@login_required(Permissions.HASSLE)
def run_hassle():
  """Logic for room hassles."""
  available_participants = helpers.get_available_participants()
  available_rooms = helpers.get_available_rooms()
  rooms_remaining = helpers.get_rooms_remaining()
  events = helpers.get_events_with_roommates()

  return flask.render_template('hassle.html',
      available_participants=available_participants,
      available_rooms=available_rooms,
      events=events,
      alleys=helpers.alleys,
      rooms_remaining=rooms_remaining)

@blueprint.route('/event', methods=['POST'])
@login_required(Permissions.HASSLE)
def hassle_event():
  """Submission endpoint for a new event (someone picks a room)."""
  user_id = flask.request.form.get('user_id', None)
  room_number = flask.request.form.get('room', None)
  roommates = flask.request.form.getlist('roommate_id')

  if user_id is None or room_number is None:
    flask.flash("Invalid request - try again?")
  else:
    roommates = list(r for r in roommates if r != "none")

    # Check for invalid roommate selection.
    if user_id in roommates or len(roommates) != len(set(roommates)):
      flask.flash("Invalid roommate selection.")
    else:
      helpers.new_event(user_id, room_number, roommates)
  return flask.redirect(flask.url_for('hassle.run_hassle'))

@blueprint.route('/restart', defaults={'event_id': None})
@blueprint.route('/restart/<int:event_id>')
@login_required(Permissions.HASSLE)
def hassle_restart(event_id):
  """Handles a restart."""
  if event_id is None:
    helpers.clear_events()
  else:
    helpers.clear_events(event_id)
  return flask.redirect(flask.url_for('hassle.run_hassle'))

@blueprint.route('/new')
@login_required(Permissions.HASSLE)
def new_hassle():
  """Redirects to the first page to start a new room helpers."""
  # Clear old data.
  helpers.clear_all()
  return flask.redirect(flask.url_for('hassle.new_hassle_participants'))

@blueprint.route('/new/participants')
@login_required(Permissions.HASSLE)
def new_hassle_participants():
  """Select participants for the room helpers."""
  # Get a list of all current members.
  members = helpers.get_all_members()
  return flask.render_template('hassle_new_participants.html', members=members)

@blueprint.route('/new/participants/submit', methods=['POST'])
@login_required(Permissions.HASSLE)
def new_hassle_participants_submit():
  """Submission endpoint for hassle participants. Redirects to next page."""
  # Get a list of all participants' user IDs.
  participants = [int(x) for x in flask.request.form.getlist('participants')]
  # Update database with this hassle's participants.
  helpers.set_participants(participants)
  return flask.redirect(flask.url_for('hassle.new_hassle_rooms'))

@blueprint.route('/new/rooms')
@login_required(Permissions.HASSLE)
def new_hassle_rooms():
  """Select rooms available for the room helpers."""
  # Get a list of all rooms.
  rooms = helpers.get_all_rooms()
  return flask.render_template('hassle_new_rooms.html',
      rooms=rooms, alleys=helpers.alleys)

@blueprint.route('/new/rooms/submit', methods=['POST'])
@login_required(Permissions.HASSLE)
def new_hassle_rooms_submit():
  """Submission endpoint for hassle rooms. Redirects to next page."""
  # Get a list of all room numbers.
  rooms = [int(x) for x in flask.request.form.getlist('rooms')]
  # Update database with participating rooms.
  helpers.set_rooms(rooms)
  return flask.redirect(flask.url_for('hassle.new_hassle_confirm'))

@blueprint.route('/new/confirm')
@login_required(Permissions.HASSLE)
def new_hassle_confirm():
  """Confirmation page for new room helpers."""
  participants = helpers.get_participants()
  rooms = helpers.get_participating_rooms()
  return flask.render_template('hassle_new_confirm.html', rooms=rooms, \
      participants=participants, alleys=helpers.alleys)

@blueprint.route('/new/confirm/submit', methods=['POST'])
@login_required(Permissions.HASSLE)
def new_hassle_confirm_submit():
  """Submission endpoint for confirmation page."""
  # Nothing to do, everything is already in the database.
  return flask.redirect(flask.url_for('hassle.run_hassle'))

@blueprint.route('/ajax/rising')
@login_required(Permissions.HASSLE)
def ajax_get_rising_members():
  """AJAX endpoint that returns the user IDs of rising current members."""
  results = list(x['user_id'] for x in helpers.get_rising_members())
  return json.dumps(results)

@blueprint.route('/ajax/frosh')
@login_required(Permissions.HASSLE)
def ajax_get_frosh():
  """AJAX endpoint that returns the user IDs of current frosh."""
  results = list(x['user_id'] for x in helpers.get_frosh())
  return json.dumps(results)
