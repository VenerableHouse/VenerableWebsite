import json
import flask
import io

from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.rotation import blueprint, helpers


@blueprint.route('/')
@login_required(Permissions.ROTATION)
def show_portal():
  dinner_list = helpers.DINNERS
  buckets = helpers.BUCKETS
  return flask.render_template('portal.html',
    dinner_list=dinner_list, buckets=buckets)

@blueprint.route('/directory')
@login_required(Permissions.ROTATION)
def show_prefrosh_list():
  dinner_id = flask.request.args.get('dinner_id')
  if dinner_id is None or int(dinner_id) not in helpers.DINNERS:
    prefrosh_list = helpers.get_all_prefrosh()
  else:
    dinner_id = int(dinner_id)
    prefrosh_list = helpers.get_prefrosh_by_dinner(dinner_id)
  return flask.render_template('directory.html',
    prefrosh_list=prefrosh_list, dinner_id=dinner_id)

@blueprint.route('/images/<int:prefrosh_id>')
@login_required(Permissions.ROTATION)
def serve_image(prefrosh_id):
  """Retrieves a prefrosh's picture."""
  img_name = helpers.get_image_name(prefrosh_id)
  dir_name = flask.current_app.config["MEDIA_FOLDER"] + "/prefrosh_pics"
  return flask.send_from_directory(dir_name, img_name);

@blueprint.route('/prefrosh/<int:prefrosh_id>')
@login_required(Permissions.ROTATION)
def show_prefrosh(prefrosh_id):
  dinner_prefrosh = helpers.get_dinner_prefrosh_by_prefrosh_id(prefrosh_id)
  prefrosh, prev_id, next_id = helpers.get_prefrosh_and_adjacent(prefrosh_id, dinner_prefrosh)
  full_name = helpers.format_name(
    prefrosh['first_name'], prefrosh['last_name'], prefrosh['preferred_name'])

  return flask.render_template('prefrosh.html', full_name=full_name, prefrosh=prefrosh,
            prev_id=prev_id, next_id=next_id, vote_tuples=helpers.VOTE_TUPLES)

@blueprint.route('/update_info/<int:prefrosh_id>', methods=['POST'])
@login_required(Permissions.ROTATION)
def update_comment(prefrosh_id):
  helpers.update_comments(prefrosh_id, flask.request.form.get("comments", ""))
  helpers.update_votes(prefrosh_id, flask.request.form)
  return flask.redirect(flask.url_for("rotation.show_prefrosh", prefrosh_id=prefrosh_id))

@blueprint.route('/compute_buckets', methods=['POST'])
@login_required(Permissions.ROTATION)
def compute_buckets():
  helpers.compute_buckets()
  return flask.redirect(flask.url_for("rotation.show_portal"))

@blueprint.route('/move')
@login_required(Permissions.ROTATION)
def move():
  old_bucket_name = flask.request.args.get("old_bucket_name")
  new_bucket_name = flask.request.args.get("new_bucket_name")
  if old_bucket_name not in helpers.BUCKETS or new_bucket_name not in helpers.BUCKETS:
    flask.flash("Bad value for one of the buckets.")
    return flask.redirect(flask.url_for('rotation.show_portal'))
  elif old_bucket_name == new_bucket_name:
    flask.flash("Buckets must be distinct.")
    return flask.redirect(flask.url_for('rotation.show_portal'))
  else:
    old_bucket_prefrosh = helpers.get_prefrosh_by_bucket(old_bucket_name)
    new_bucket_prefrosh = helpers.get_prefrosh_by_bucket(new_bucket_name)
    return flask.render_template('move.html', old_bucket=old_bucket_prefrosh,
      new_bucket=new_bucket_prefrosh, old_bucket_name=old_bucket_name, new_bucket_name=new_bucket_name,
      vote_tuples=helpers.VOTE_TUPLES)

@blueprint.route('/move/change_bucket/<int:prefrosh_id>', methods=['POST'])
@login_required(Permissions.ROTATION)
def change_bucket(prefrosh_id):
  new_bucket_name = flask.request.form.get("newBucket")
  old_bucket_name = flask.request.form.get("oldBucket")
  if old_bucket_name not in helpers.BUCKETS or new_bucket_name not in helpers.BUCKETS:
    flask.flash("Bad value for one of the buckets.")
  elif old_bucket_name == new_bucket_name:
    flask.flash("Buckets must be distinct.")
  old_bucket_prefrosh = helpers.get_prefrosh_by_bucket(old_bucket_name)
  prefrosh, prev_id, next_id = helpers.get_prefrosh_and_adjacent(prefrosh_id, old_bucket_prefrosh)
  helpers.change_bucket(prefrosh_id, new_bucket_name)
  if prev_id:
    return flask.redirect(flask.url_for("rotation.move",
      _anchor=prev_id, old_bucket_name=old_bucket_name, new_bucket_name=new_bucket_name))
  else:
    return flask.redirect(flask.url_for("rotation.move",
      _anchor=next_id, old_bucket_name=old_bucket_name, new_bucket_name=new_bucket_name))
