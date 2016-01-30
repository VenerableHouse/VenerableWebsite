import flask
blueprint = flask.Blueprint('hassle', __name__,
    template_folder='templates', static_folder='static')

import ruddock.modules.hassle.routes
