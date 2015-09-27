import flask
blueprint = flask.Blueprint('government', __name__, template_folder='templates')

import RuddockWebsite.modules.government.routes
