import flask

from RuddockWebsite import office_utils
from RuddockWebsite.modules.government import blueprint

@blueprint.route('/')
def government_home():
  # Get current assignments
  assignments = office_utils.get_current_assignments()

  # Organize by type (excomm and ucc are special)
  excomm = []
  ucc = []
  other = []
  for assignment in assignments:
    # Organize by type
    if assignment['is_excomm']:
      excomm.append(assignment)
    elif assignment['is_ucc']:
      ucc.append(assignment)
    else:
      other.append(assignment)

  ucc.sort(key=lambda x: x['office_name'])
  other.sort(key=lambda x: x['office_name'])

  # Tuple with name, email, and users, so that template can parse efficiently
  assignment_data = [
    ('Executive Committee', 'excomm', excomm),
    ('Upperclass Counselors', 'uccs', ucc),
    ('Other Offices', None, other)
  ]
  return flask.render_template('government.html',
      assignment_data=assignment_data)
