import flask
blueprint = flask.Blueprint('users', __name__, template_folder='templates')

import ruddock.modules.users.routes
