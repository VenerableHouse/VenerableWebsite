import flask
blueprint = flask.Blueprint('admin', __name__, template_folder='templates')

import RuddockWebsite.modules.admin.routes
