import flask
blueprint = flask.Blueprint('users', __name__, template_folder='templates')

import RuddockWebsite.modules.users.routes
