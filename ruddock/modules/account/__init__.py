import flask
blueprint = flask.Blueprint('account', __name__, template_folder='templates')

import ruddock.modules.account.routes
