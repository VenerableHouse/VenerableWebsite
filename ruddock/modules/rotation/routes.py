import json
import flask
import io

from ruddock.resources import Permissions
from ruddock.decorators import login_required
from ruddock.modules.rotation import blueprint, helpers


@blueprint.route('/')
@login_required(Permissions.ROTATION)
def show_portal():
  dinner_list = helpers.get_dinners()
  return flask.render_template('portal.html',
    dinner_list=dinner_list)

@blueprint.route('/dinner/<dinner_id>')
@login_required(Permissions.ROTATION)
def show_dinner_list(dinner_id):
  prefrosh_list = helpers.get_prefrosh_by_dinner(dinner_id)
  return flask.render_template('directory.html',
    prefrosh_list=prefrosh_list, dinner_id=dinner_id)

@blueprint.route('/images/<prefrosh_id>')
@login_required(Permissions.ROTATION)
def serve_image(prefrosh_id):
  img_contents = helpers.get_image_contents(prefrosh_id)
  return flask.Response(io.BytesIO(img_contents), '200 OK', None, 'image/jpeg', 'image/jpeg')

@blueprint.route('/prefrosh/<prefrosh_id>')
@login_required(Permissions.ROTATION)
def show_prefrosh(prefrosh_id):
  prefrosh = helpers.get_prefrosh(prefrosh_id)
  pref = ' \"' + prefrosh['preferred_name'] + '\" ' if prefrosh['preferred_name'] else ' '
  full_name = prefrosh['first_name'] + pref + prefrosh['last_name']
  return flask.render_template('prefrosh.html', full_name=full_name, prefrosh=prefrosh)

@blueprint.route('/update_info/<prefrosh_id>', methods=['POST'])
@login_required(Permissions.ROTATION)
def update_comment(prefrosh_id):
  helpers.update_comments(prefrosh_id, flask.request.form['comments'])
  helpers.update_votes(prefrosh_id, flask.request.form)
  return flask.redirect(flask.url_for("rotation.show_prefrosh", prefrosh_id=prefrosh_id))
