import flask
blueprint = flask.Blueprint('auth', __name__, template_folder='templates')

import RuddockWebsite.modules.auth.routes
