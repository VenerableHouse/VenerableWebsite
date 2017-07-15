import flask
blueprint = flask.Blueprint('birthdays', __name__,
                template_folder='templates', static_folder='static')

import ruddock.modules.birthdays.routes
