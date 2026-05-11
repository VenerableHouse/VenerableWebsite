import json
import flask

from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.hassle import blueprint, helpers, picks_helpers
import ruddock.auth_utils as auth_utils

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


# ---------------------------------------------------------------------------
# Preference-based picks hassle routes (/hassle/picks/)
# ---------------------------------------------------------------------------

@blueprint.route('/picks/')
@login_required()
def picks_index():
  """Overview page: shows current algorithm state for all participants."""
  participants = picks_helpers.get_picks_participants()
  rooms_rows = picks_helpers.get_picks_rooms()
  rooms_info = {row['room_number']: row for row in rooms_rows}
  frosh_quotas = picks_helpers.get_frosh_quotas()
  all_prefs = picks_helpers.get_all_picks_preferences()

  assignments, blocked = picks_helpers.run_picks_algorithm()

  # Build per-participant summary rows.
  summary = []
  for p in participants:
    uid = p['user_id']
    room = assignments.get(uid)
    if room is None:
      prefs = all_prefs.get(uid, [])
      status = 'No preferences' if not prefs else 'No valid room'
    else:
      status = 'Assigned'
    summary.append({
      'user_id': uid,
      'name': p['name'],
      'pick_position': p['pick_position'],
      'ucc_alley': p['ucc_alley'],
      'pair_id': p['pair_id'],
      'room': room,
      'status': status,
    })

  statuses = {}
  for rn, row in rooms_info.items():
    if rn in picks_helpers.PERMANENTLY_VACANT:
      statuses[rn] = 'vacant'
    elif rn in assignments.values():
      statuses[rn] = 'assigned'
    elif rn in blocked or rn in picks_helpers.FORCED_FROSH:
      statuses[rn] = 'blocked'
    elif row['is_ucc']:
      statuses[rn] = 'ucc'
    else:
      statuses[rn] = 'available'

  return flask.render_template('hassle_picks.html',
      summary=summary,
      rooms_info=rooms_info,
      assignments=assignments,
      blocked=blocked,
      frosh_quotas=frosh_quotas,
      statuses=statuses,
      all_prefs=all_prefs,
      configured=picks_helpers.picks_configured(),
      is_secretary=auth_utils.check_permission(Permissions.HASSLE),
      ROOMS_BY_ALLEY=picks_helpers.ROOMS_BY_ALLEY,
      PERMANENTLY_VACANT=picks_helpers.PERMANENTLY_VACANT,
      FORCED_FROSH=picks_helpers.FORCED_FROSH)


@blueprint.route('/picks/setup')
@login_required(Permissions.HASSLE)
def picks_setup():
  """Secretary setup page: upload pick-order CSV and configure frosh quotas."""
  frosh_quotas = picks_helpers.get_frosh_quotas()
  if not frosh_quotas:
    frosh_quotas = dict(picks_helpers.DEFAULT_FROSH_QUOTAS)

  has_participants = picks_helpers.picks_configured()
  has_rooms = flask.g.db.execute(sqlalchemy.text(
      "SELECT 1 FROM hassle_picks_rooms LIMIT 1")).first() is not None

  return flask.render_template('hassle_picks_setup.html',
      frosh_quotas=frosh_quotas,
      has_participants=has_participants,
      has_rooms=has_rooms)


@blueprint.route('/picks/setup/submit', methods=['POST'])
@login_required(Permissions.HASSLE)
def picks_setup_submit():
  """Save frosh quota configuration. Participants are set via CSV upload."""
  import sqlalchemy
  form = flask.request.form

  quotas = {}
  for alley in range(1, 7):
    val = form.get('quota_{}'.format(alley), '')
    try:
      quotas[alley] = max(0, int(val))
    except (ValueError, TypeError):
      quotas[alley] = picks_helpers.DEFAULT_FROSH_QUOTAS.get(alley, 0)

  room_numbers = list(picks_helpers.ALL_PICKABLE_ROOMS | picks_helpers.FORCED_FROSH)

  with flask.g.db.begin():
    flask.g.db.execute(sqlalchemy.text("DELETE FROM hassle_picks_rooms"))
    flask.g.db.execute(sqlalchemy.text("DELETE FROM hassle_picks_frosh_quotas"))
    for alley, quota in quotas.items():
      flask.g.db.execute(sqlalchemy.text(
          "INSERT INTO hassle_picks_frosh_quotas (alley, quota) VALUES (:a, :q)"),
          a=alley, q=quota)
    for rn in room_numbers:
      flask.g.db.execute(sqlalchemy.text(
          "INSERT INTO hassle_picks_rooms (room_number, is_ucc) VALUES (:r, :u)"),
          r=rn, u=False)

  flask.flash('Frosh quotas saved.')
  return flask.redirect(flask.url_for('hassle.picks_setup'))


@blueprint.route('/picks/preferences')
@login_required()
def picks_preferences():
  """Member preference page: view/edit up to 10 room preferences."""
  user_id = auth_utils.get_user_id(flask.session['username'])
  if user_id is None:
    flask.abort(403)

  if not picks_helpers.is_participant(user_id):
    return flask.render_template('hassle_picks_preferences.html',
        not_participant=True)

  participants = picks_helpers.get_picks_participants()
  rooms_rows = picks_helpers.get_picks_rooms()
  rooms_info = {row['room_number']: row for row in rooms_rows}
  all_prefs = picks_helpers.get_all_picks_preferences()
  my_prefs = [rn for rn in all_prefs.get(user_id, [])]

  assignments, blocked = picks_helpers.run_picks_algorithm()
  my_room = assignments.get(user_id)

  statuses = picks_helpers.get_room_statuses(
      user_id, assignments, blocked, rooms_info, all_prefs, participants)

  partner_id = picks_helpers.get_pair_partner_id(user_id, participants)
  partner_name = None
  if partner_id is not None:
    for p in participants:
      if p['user_id'] == partner_id:
        partner_name = p['name']
        break

  return flask.render_template('hassle_picks_preferences.html',
      not_participant=False,
      my_prefs=my_prefs,
      my_room=my_room,
      statuses=statuses,
      rooms_info=rooms_info,
      partner_name=partner_name,
      ROOMS_BY_ALLEY=picks_helpers.ROOMS_BY_ALLEY,
      PERMANENTLY_VACANT=picks_helpers.PERMANENTLY_VACANT,
      FORCED_FROSH=picks_helpers.FORCED_FROSH)


@blueprint.route('/picks/preferences/submit', methods=['POST'])
@login_required()
def picks_prefs_submit():
  """Save preferences for the current user and re-run algorithm."""
  user_id = auth_utils.get_user_id(flask.session['username'])
  if user_id is None:
    flask.abort(403)

  if not picks_helpers.is_participant(user_id):
    flask.flash('You are not a participant in this hassle.')
    return flask.redirect(flask.url_for('hassle.picks_preferences'))

  ordered_rooms = []
  for rn_str in flask.request.form.getlist('pref_rooms[]'):
    try:
      ordered_rooms.append(int(rn_str))
    except (ValueError, TypeError):
      pass

  picks_helpers.set_preferences(user_id, ordered_rooms)

  assignments, _ = picks_helpers.run_picks_algorithm()
  my_room = assignments.get(user_id)
  if my_room:
    flask.flash('Preferences saved. Your current assignment: Room {}.'.format(my_room))
  else:
    flask.flash('Preferences saved. No room currently assigned — check back after others submit.')
  return flask.redirect(flask.url_for('hassle.picks_preferences'))


@blueprint.route('/picks/reset')
@login_required(Permissions.HASSLE)
def picks_reset():
  """Reset all picks data (Secretary only)."""
  picks_helpers.clear_picks_all()
  flask.flash('Picks hassle data cleared.')
  return flask.redirect(flask.url_for('hassle.picks_setup'))


@blueprint.route('/picks/setup/csv', methods=['POST'])
@login_required(Permissions.HASSLE)
def picks_setup_csv_upload():
  """
  Upload a CSV to set the pick order and roommate pairs.

  CSV format (one row per pick unit, rows define pick order):
    Name1[, Name2[, UCC_Alley]]

  Name1 / Name2 must match member names exactly (case-insensitive).
  UCC_Alley is an optional integer 1-6 for on-campus alley UCC guarantee.

  Only hassle_picks_participants is updated; rooms and frosh quotas are unchanged.
  All previously submitted preferences are cleared (cascade).
  """
  import csv
  import io
  import sqlalchemy

  file = flask.request.files.get('csv_file')
  if not file or file.filename == '':
    flask.flash('No file selected.')
    return flask.redirect(flask.url_for('hassle.picks_setup'))

  try:
    stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
  except UnicodeDecodeError:
    flask.flash('Could not read file — make sure it is saved as UTF-8.')
    return flask.redirect(flask.url_for('hassle.picks_setup'))

  # Build name → user_id lookup (case-insensitive).
  all_members = picks_helpers.get_all_members()
  name_to_uid = {m['name'].strip().lower(): m['user_id'] for m in all_members}

  errors = []
  units = []  # list of {'uids': [uid, ...], 'ucc_alley': int|None}

  for lineno, row in enumerate(csv.reader(stream), start=1):
    row = [cell.strip() for cell in row]
    # Drop empty trailing cells.
    while row and not row[-1]:
      row.pop()
    if not row:
      continue  # blank line

    # Extract optional UCC alley from last column if it's a digit.
    ucc_alley = None
    if row and row[-1].isdigit():
      ucc_alley = int(row[-1])
      if ucc_alley not in range(1, 7):
        errors.append('Row {}: UCC alley must be 1–6, got {}'.format(lineno, ucc_alley))
        continue
      row = row[:-1]

    if len(row) == 0 or len(row) > 2:
      errors.append('Row {}: expected 1 or 2 names, got {}'.format(lineno, len(row)))
      continue

    uids = []
    for name in row:
      uid = name_to_uid.get(name.lower())
      if uid is None:
        errors.append('Row {}: unrecognized name "{}"'.format(lineno, name))
      else:
        uids.append(uid)

    if not errors:
      units.append({'uids': uids, 'ucc_alley': ucc_alley})

  if errors:
    flask.flash('CSV upload failed — fix the following errors and re-upload: '
                + ' | '.join(errors))
    return flask.redirect(flask.url_for('hassle.picks_setup'))

  # Build participant list.
  participant_list = []  # (user_id, pick_position, ucc_alley, pair_id)
  pick_pos = 1
  pair_id = 1

  for unit in units:
    current_pair_id = pair_id if len(unit['uids']) == 2 else None
    for uid in unit['uids']:
      participant_list.append((uid, pick_pos, unit['ucc_alley'], current_pair_id))
      pick_pos += 1
    if current_pair_id is not None:
      pair_id += 1

  # Commit: replace participants only (rooms + quotas unchanged).
  with flask.g.db.begin():
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_preferences"))
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_participants"))
    for uid, pos, ucc_alley, p_id in participant_list:
      flask.g.db.execute(sqlalchemy.text("""
        INSERT INTO hassle_picks_participants
          (user_id, pick_position, ucc_alley, pair_id)
        VALUES (:u, :p, :a, :r)
      """), u=uid, p=pos, a=ucc_alley, r=p_id)

  flask.flash('CSV uploaded: {} participants ({} pairs, {} solo) added. '
              'Preferences cleared.'.format(
                  len(participant_list),
                  sum(1 for u in units if len(u['uids']) == 2),
                  sum(1 for u in units if len(u['uids']) == 1)))
  return flask.redirect(flask.url_for('hassle.picks_setup'))
