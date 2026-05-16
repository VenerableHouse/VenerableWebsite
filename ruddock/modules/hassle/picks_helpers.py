"""
Helpers for the preference-based room picks hassle (/hassle/picks/).

The Secretary configures participants (with pick order and optional alley-UCC
guarantees), rooms (with optional UCC flags), and per-alley frosh quotas.
Each participant ranks up to 10 rooms. The algorithm assigns rooms greedily:
for each participant in pick order, assign their highest-ranked room that is
available and not constraint-blocked.
"""

import collections
import flask
import sqlalchemy

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default frosh quotas per alley inserted when the hassle is reset.
DEFAULT_FROSH_QUOTAS = {1: 2, 2: 3, 3: 2, 4: 2, 5: 3, 6: 3}

# Rooms that are permanently vacant (not frosh, not member-pickable).
# Excluded from all quota and adjacency calculations; no tile rendered.
PERMANENTLY_VACANT = frozenset({131})

# Rooms that are always frosh (count toward quota; included in adjacency checks).
FORCED_FROSH = frozenset({112})

# Rooms that must never end up as frosh; any pick that would cause this is blocked.
NEVER_FROSH = frozenset({114})

# Undirected adjacency graph.  Two rooms are adjacent if they are either:
#   (a) sequentially next to each other on the SAME corridor side, or
#   (b) directly across the hallway from each other (directly opposing).
# Edges to PERMANENTLY_VACANT rooms are excluded.
ROOM_ADJACENCY = {
    # Alley 1 — right side (top→bottom): 138, 136, 134, 132, 130
    #            left side (top→bottom):  133, 131(vacant — excluded)
    #            cross-hall: 132↔133; 130's cross-hall 131 is vacant
    138: [136],
    136: [138, 134],
    134: [136, 132],
    132: [134, 130, 133],
    130: [132],
    133: [132],

    # Alley 2 — rooms 119,121,123,125,127 plus extension 112,114
    #            114 NOT adjacent to 127; 112 adjacent to 110 (cross-alley)
    114: [112],
    112: [114, 110],
    127: [125],
    125: [127, 123],
    123: [125, 121],
    121: [123, 119],
    119: [121],

    # Alley 3 — right side (top→bottom): 110, 108, 106, 104
    #            left side (top→bottom):  105, 103, 101
    #            cross-hall: 106↔105, 104↔103; 101 has no cross-hall pair
    #            110 also adjacent to 112 (cross-alley boundary)
    110: [108, 112],
    108: [110, 106],
    106: [108, 104, 105],
    104: [106, 103],
    105: [103, 106],
    103: [105, 101, 104],
    101: [103],

    # Alley 4 — single corridor
    234: [236],
    236: [234, 238],
    238: [236, 240],
    240: [238, 242],
    242: [240, 244],
    244: [242],

    # Alley 5 — sub-corridors 221→229 and 216→220, joined at 220↔221
    #            216 also adjacent to 214 (cross-alley boundary with Alley 6)
    216: [218, 214],
    218: [216, 220],
    220: [218, 221],
    221: [220, 223],
    223: [221, 225],
    225: [223, 227],
    227: [225, 229],
    229: [227],

    # Alley 6 — sub-corridors 201→203→205 and 204→206→…→214,
    #            joined at 204↔205; 214 also adjacent to 216 (cross-alley)
    201: [203],
    203: [201, 205],
    205: [203, 204],
    204: [205, 206],
    206: [204, 208],
    208: [206, 210],
    210: [208, 212],
    212: [210, 214],
    214: [212, 216],
}

# Rooms per alley (excludes permanently vacant; includes forced frosh).
ROOMS_BY_ALLEY = {
    1: [130, 132, 133, 134, 136, 138],
    2: [112, 114, 119, 121, 123, 125, 127],
    3: [101, 103, 104, 105, 106, 108, 110],
    4: [234, 236, 238, 240, 242, 244],
    5: [216, 218, 220, 221, 223, 225, 227, 229],
    6: [201, 203, 204, 205, 206, 208, 210, 212, 214],
}

# Flat set of all rooms that may ever appear in hassle_picks_rooms.
ALL_PICKABLE_ROOMS = frozenset(
    r for rooms in ROOMS_BY_ALLEY.values() for r in rooms
    if r not in FORCED_FROSH
)

# Room type labels shown in the preference list (matches floor plan titles).
ROOM_TYPES = {
    101: 'Sky',  103: 'Loft', 104: 'Loft', 105: 'Bunk', 106: 'Sky',
    108: 'Loft', 110: 'Loft',
    112: 'Sky',  114: 'Loft', 119: 'Bunk', 121: 'Loft', 123: 'Sky',
    125: 'Loft', 127: 'Loft',
    130: 'Bunk', 132: 'Loft', 133: 'Sky',  134: 'Loft', 136: 'Sky',
    138: 'Loft',
    201: 'Loft', 203: 'Sky',  204: 'Loft', 205: 'Loft', 206: 'Bunk',
    208: 'Loft', 210: 'Sky',  212: 'Loft', 214: 'Sky',  216: 'Loft',
    218: 'Sky',  220: 'Bunk', 221: 'Loft', 223: 'Sky',  225: 'Loft',
    227: 'Loft', 229: 'Loft',
    234: 'Bunk', 236: 'Loft', 238: 'Loft', 240: 'Loft', 242: 'Sky',
    244: 'Loft',
}

# ---------------------------------------------------------------------------
# Database helpers — setup
# ---------------------------------------------------------------------------

def clear_picks_all():
  """Truncates all four picks tables inside a transaction."""
  with flask.g.db.begin():
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_preferences"))
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_rooms"))
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_participants"))
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_frosh_quotas"))


def set_picks_participants(ordered_list):
  """
  Replace participant table.

  ordered_list: [(user_id, pick_position, ucc_alley, pair_id), ...]
    pick_position 1 = first pick; ucc_alley is None or an int 1-6;
    pair_id is None for solo pickers or a shared int for roommate pairs.
  """
  with flask.g.db.begin():
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_participants"))
    for user_id, pick_position, ucc_alley, pair_id in ordered_list:
      flask.g.db.execute(sqlalchemy.text("""
        INSERT INTO hassle_picks_participants
          (user_id, pick_position, ucc_alley, pair_id)
        VALUES (:u, :p, :a, :r)
      """), u=user_id, p=pick_position, a=ucc_alley, r=pair_id)


def set_picks_rooms(room_numbers, ucc_set):
  """
  Replace room table.

  room_numbers: iterable of room numbers to include in the hassle.
  ucc_set: set of room numbers that should be flagged as UCC (orange).
  """
  with flask.g.db.begin():
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_preferences"))
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_rooms"))
    for rn in room_numbers:
      flask.g.db.execute(sqlalchemy.text("""
        INSERT INTO hassle_picks_rooms (room_number, is_ucc)
        VALUES (:r, :u)
      """), r=rn, u=(rn in ucc_set))


def set_frosh_quotas(quota_dict):
  """
  Replace frosh quota table.

  quota_dict: {alley: quota}
  """
  with flask.g.db.begin():
    flask.g.db.execute(sqlalchemy.text(
        "DELETE FROM hassle_picks_frosh_quotas"))
    for alley, quota in quota_dict.items():
      flask.g.db.execute(sqlalchemy.text("""
        INSERT INTO hassle_picks_frosh_quotas (alley, quota)
        VALUES (:a, :q)
      """), a=alley, q=quota)


def reset_to_defaults():
  """Insert default frosh quotas and all pickable rooms (no UCC flags).
  FORCED_FROSH rooms are included so they appear red in the UI."""
  set_frosh_quotas(DEFAULT_FROSH_QUOTAS)
  all_rooms = list(ALL_PICKABLE_ROOMS | FORCED_FROSH)
  set_picks_rooms(all_rooms, set())


# ---------------------------------------------------------------------------
# Database helpers — read
# ---------------------------------------------------------------------------

def get_picks_participants():
  """Returns all participants ordered by pick_position."""
  return flask.g.db.execute(sqlalchemy.text("""
    SELECT p.user_id, p.pick_position, p.ucc_alley, p.pair_id, me.name
    FROM hassle_picks_participants p
    JOIN members m ON p.user_id = m.user_id
    JOIN members_extra me ON p.user_id = me.user_id
    ORDER BY p.pick_position
  """)).fetchall()


def get_pair_partner_id(user_id, participants):
  """Returns the user_id of the pair partner, or None if solo."""
  pair_id = None
  for p in participants:
    if p['user_id'] == user_id:
      pair_id = p['pair_id']
      break
  if pair_id is None:
    return None
  for p in participants:
    if p['pair_id'] == pair_id and p['user_id'] != user_id:
      return p['user_id']
  return None


def get_picks_rooms():
  """Returns all rooms in the hassle with their alley and UCC flag."""
  return flask.g.db.execute(sqlalchemy.text("""
    SELECT pr.room_number, r.alley, pr.is_ucc, r.coords
    FROM hassle_picks_rooms pr
    JOIN rooms r ON pr.room_number = r.room_number
    ORDER BY pr.room_number
  """)).fetchall()


def get_frosh_quotas():
  """Returns {alley: quota} dict."""
  rows = flask.g.db.execute(sqlalchemy.text(
      "SELECT alley, quota FROM hassle_picks_frosh_quotas")).fetchall()
  return {row['alley']: row['quota'] for row in rows}


def get_picks_preferences(user_id):
  """Returns [(room_number, rank), ...] ordered by rank for one user."""
  return flask.g.db.execute(sqlalchemy.text("""
    SELECT room_number, rank
    FROM hassle_picks_preferences
    WHERE user_id = :u
    ORDER BY rank
  """), u=user_id).fetchall()


def get_all_picks_preferences():
  """Returns {user_id: [room_number, ...]} ordered by rank."""
  rows = flask.g.db.execute(sqlalchemy.text("""
    SELECT user_id, room_number
    FROM hassle_picks_preferences
    ORDER BY user_id, rank
  """)).fetchall()
  result = collections.defaultdict(list)
  for row in rows:
    result[row['user_id']].append(row['room_number'])
  return dict(result)


def set_preferences(user_id, ordered_rooms):
  """
  Replace preferences for one user and sync to their pair partner if they have one.

  ordered_rooms: list of room_numbers in preference order (index 0 = rank 1).
  Silently truncates to 10.
  """
  ordered_rooms = ordered_rooms[:10]
  participants = get_picks_participants()
  partner_id = get_pair_partner_id(user_id, participants)

  user_ids_to_update = [user_id]
  if partner_id is not None:
    user_ids_to_update.append(partner_id)

  with flask.g.db.begin():
    for uid in user_ids_to_update:
      flask.g.db.execute(sqlalchemy.text(
          "DELETE FROM hassle_picks_preferences WHERE user_id = :u"), u=uid)
      for rank, room_number in enumerate(ordered_rooms, start=1):
        flask.g.db.execute(sqlalchemy.text("""
          INSERT INTO hassle_picks_preferences (user_id, room_number, rank)
          VALUES (:u, :r, :k)
        """), u=uid, r=room_number, k=rank)


def is_participant(user_id):
  """Returns True if the user is registered as a picks participant."""
  row = flask.g.db.execute(sqlalchemy.text("""
    SELECT 1 FROM hassle_picks_participants WHERE user_id = :u
  """), u=user_id).first()
  return row is not None


def picks_configured():
  """Returns True if setup has been run (at least one participant exists)."""
  row = flask.g.db.execute(sqlalchemy.text(
      "SELECT 1 FROM hassle_picks_participants LIMIT 1")).first()
  return row is not None


def get_all_members():
  """Returns all current members for use in the setup page."""
  return flask.g.db.execute(sqlalchemy.text("""
    SELECT m.user_id, me.name, m.graduation_year,
           m.member_type, mt.membership_desc,
           o.office_name IS NOT NULL AS is_ucc_office,
           o.office_name
    FROM members m
    JOIN members_extra me ON m.user_id = me.user_id
    JOIN members_current mc ON m.user_id = mc.user_id
    JOIN membership_types mt ON m.member_type = mt.member_type
    LEFT JOIN (
      SELECT oa.user_id, o2.office_name
      FROM office_assignments oa
      JOIN office_assignments_current oac ON oa.assignment_id = oac.assignment_id
      JOIN offices o2 ON oa.office_id = o2.office_id
      WHERE o2.is_ucc = TRUE
      LIMIT 1
    ) o ON m.user_id = o.user_id
    ORDER BY m.member_type, m.graduation_year, me.name
  """)).fetchall()


# ---------------------------------------------------------------------------
# Constraint algorithm
# ---------------------------------------------------------------------------

def _connected_components(nodes, adjacency):
  """
  Returns a list of frozensets, each being one connected component,
  given a set of node IDs and an adjacency dict.
  """
  visited = set()
  components = []
  for node in nodes:
    if node in visited:
      continue
    component = set()
    queue = collections.deque([node])
    while queue:
      n = queue.popleft()
      if n in visited:
        continue
      visited.add(n)
      if n in nodes:
        component.add(n)
        for nb in adjacency.get(n, []):
          if nb not in visited and nb in nodes:
            queue.append(nb)
    if component:
      components.append(frozenset(component))
  return components


def _max_member_picks(alley, frosh_quota, rooms_in_hassle_by_alley):
  """
  Max member picks in an alley = pickable rooms in hassle - remaining frosh slots.
  Forced-frosh rooms count against the quota but are not pickable.
  """
  pickable = [r for r in rooms_in_hassle_by_alley.get(alley, [])
              if r not in FORCED_FROSH]
  forced_in_alley = sum(1 for r in rooms_in_hassle_by_alley.get(alley, [])
                        if r in FORCED_FROSH)
  remaining_frosh_slots = frosh_quota - forced_in_alley
  return len(pickable) - max(remaining_frosh_slots, 0)


def get_blocked_rooms(assignments, frosh_quotas, participants, rooms_info,
                       current_picker_id=None):
  """
  Returns a frozenset of room_numbers that cannot be assigned.

  assignments: {user_id: room_number} — current algorithm state.
  frosh_quotas: {alley: quota}
  participants: list of participant rows (ordered by pick_position).
  rooms_info: {room_number: row} from get_picks_rooms(), keyed by room_number.
  current_picker_id: user_id of the picker currently being processed —
    excluded from the alley-UCC protection check so they can't block
    their own last available room.
  """
  blocked = set()
  assigned_rooms = set(assignments.values())

  # FORCED_FROSH rooms are never assignable.
  blocked.update(FORCED_FROSH)

  # Build per-alley structures.
  rooms_by_alley = collections.defaultdict(list)
  for rn, row in rooms_info.items():
    rooms_by_alley[row['alley']].append(rn)

  assigned_by_alley = collections.defaultdict(int)
  for rn in assigned_rooms:
    if rn in rooms_info:
      assigned_by_alley[rooms_info[rn]['alley']] += 1

  # Unassigned participants (those who still need a room),
  # excluding the current picker so they can't block their own last room.
  assigned_users = set(assignments.keys())
  unassigned_participants = [p for p in participants
                              if p['user_id'] not in assigned_users
                              and p['user_id'] != current_picker_id]

  for rn, row in rooms_info.items():
    if rn in assigned_rooms:
      blocked.add(rn)
      continue

    alley = row['alley']
    quota = frosh_quotas.get(alley, 0)
    max_picks = _max_member_picks(alley, quota, rooms_by_alley)

    # 1. Quota full for this alley.
    if assigned_by_alley[alley] >= max_picks:
      blocked.add(rn)
      continue

    # 2. Alley UCC guarantee: ensure at least one room remains in Alley X
    #    for each unassigned alley-X UCC participant who picks after this.
    #    Only relevant when rn is IN that alley — a pick in a different alley
    #    cannot reduce availability in Alley X.
    would_block = False
    for p in unassigned_participants:
      ucc_alley = p['ucc_alley']
      if ucc_alley is None or ucc_alley != alley:
        continue
      # Assigning rn takes one slot; check post-assignment quota state.
      if assigned_by_alley[alley] + 1 >= max_picks:
        # Quota exhausted — all remaining rooms become frosh-blocked.
        would_block = True
        break
      available_in_ucc_alley = [
        r for r in rooms_by_alley.get(alley, [])
        if r not in assigned_rooms
        and r not in FORCED_FROSH
        and r != rn
      ]
      if not available_in_ucc_alley:
        would_block = True
        break
    if would_block:
      blocked.add(rn)
      continue

    # 3. Adjacency violation: if assigning rn causes alley to reach quota,
    #    check whether the remaining frosh rooms form a component >= 3.
    if assigned_by_alley[alley] + 1 >= max_picks:
      # All remaining (unassigned, non-forced-frosh) rooms in this alley
      # become forced frosh — check their adjacency.
      frosh_set = set()
      for r in rooms_by_alley.get(alley, []):
        if r == rn:
          continue  # this room is now a member room
        if r in assigned_rooms:
          continue  # already a member room
        # It's frosh (either forced or because quota is now exhausted).
        frosh_set.add(r)
      # Also include FORCED_FROSH rooms in this alley (always frosh).
      for r in FORCED_FROSH:
        if r in rooms_info and rooms_info[r]['alley'] == alley:
          frosh_set.add(r)

      components = _connected_components(frosh_set, ROOM_ADJACENCY)
      if any(len(c) >= 3 for c in components):
        blocked.add(rn)

    # 4. NEVER_FROSH protection: block any pick that would exhaust this alley's
    #    quota while a NEVER_FROSH room in the same alley is still unassigned.
    if assigned_by_alley[alley] + 1 >= max_picks:
      for protected in NEVER_FROSH:
        if (protected != rn
            and protected in rooms_info
            and rooms_info[protected]['alley'] == alley
            and protected not in assigned_rooms):
          blocked.add(rn)
          break

  return frozenset(blocked)


def run_picks_algorithm():
  """
  Runs the greedy preference-based assignment algorithm.

  Returns:
    assignments: {user_id: room_number}  — may omit users with no valid room.
    blocked_snapshot: frozenset of room_numbers blocked at algorithm end.
  """
  frosh_quotas = get_frosh_quotas()
  if not frosh_quotas:
    return {}, frozenset()

  participants = get_picks_participants()
  rooms_rows = get_picks_rooms()
  rooms_info = {row['room_number']: row for row in rooms_rows}
  all_prefs = get_all_picks_preferences()

  assignments = {}

  for participant in participants:
    uid = participant['user_id']
    ucc_alley = participant['ucc_alley']

    # Skip participants already assigned (via their pair partner picking first).
    if uid in assignments:
      continue

    partner_id = get_pair_partner_id(uid, participants)

    blocked = get_blocked_rooms(
        assignments, frosh_quotas, participants, rooms_info,
        current_picker_id=uid)
    prefs = all_prefs.get(uid, [])

    for room_number in prefs:
      if room_number not in rooms_info:
        continue
      if room_number in set(assignments.values()):
        continue
      if room_number in blocked:
        continue
      if ucc_alley is not None:
        if rooms_info[room_number]['alley'] != ucc_alley:
          continue
      assignments[uid] = room_number
      # Assign partner to same room.
      if partner_id is not None:
        assignments[partner_id] = room_number
      break

  final_blocked = get_blocked_rooms(
      assignments, frosh_quotas, participants, rooms_info)
  return assignments, final_blocked


def get_room_statuses(current_user_id, assignments, blocked, rooms_info,
                       all_prefs, participants):
  """
  Returns a dict: {room_number: status_string} for rendering the room grid.

  Statuses:
    'vacant'    — permanently vacant; don't render tile
    'assigned_you' — assigned to the current viewer
    'assigned'  — assigned to someone else
    'blocked'   — frosh/constraint blocked (red)
    'ucc'       — UCC-flagged (orange)
    'wanted'    — available but in a lower-priority picker's preferences (yellow)
    'available' — available, no demand (white)
  """
  # Determine the current user's pick position, UCC alley, and pair partner.
  user_position = None
  ucc_alley = None
  partner_id = get_pair_partner_id(current_user_id, participants)
  for p in participants:
    if p['user_id'] == current_user_id:
      user_position = p['pick_position']
      ucc_alley = p['ucc_alley']
      break

  # The room assigned to this viewer (or their partner — same room for pairs).
  my_room = assignments.get(current_user_id)

  # Rooms wanted by lower-priority pickers (excluding pair partner, same list).
  wanted_rooms = set()
  if user_position is not None:
    for p in participants:
      if p['pick_position'] > user_position and p['user_id'] not in assignments:
        if partner_id is not None and p['user_id'] == partner_id:
          continue  # partner shares our prefs, don't double-count
        for rn in all_prefs.get(p['user_id'], []):
          wanted_rooms.add(rn)

  # Rooms already assigned to lower-priority pickers — hassle-able (yellow).
  hassle_rooms = set()
  if user_position is not None:
    lower_priority_users = {
        p['user_id'] for p in participants
        if p['pick_position'] > user_position
        and (partner_id is None or p['user_id'] != partner_id)
    }
    for uid in lower_priority_users:
      if uid in assignments:
        hassle_rooms.add(assignments[uid])

  statuses = {}
  for rn, row in rooms_info.items():
    if rn in PERMANENTLY_VACANT:
      statuses[rn] = 'vacant'
    elif my_room == rn:
      statuses[rn] = 'assigned_you'
    elif rn in hassle_rooms:
      statuses[rn] = 'wanted'
    elif rn in assignments.values():
      statuses[rn] = 'assigned'
    elif rn in blocked:
      statuses[rn] = 'blocked'
    elif ucc_alley is not None and row['alley'] != ucc_alley:
      statuses[rn] = 'blocked'
    elif row['is_ucc']:
      statuses[rn] = 'ucc'
    elif rn in wanted_rooms:
      statuses[rn] = 'wanted'
    else:
      statuses[rn] = 'available'

  return statuses
