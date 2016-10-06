import flask
blueprint = flask.Blueprint('rotation', __name__,
                template_folder='templates', static_folder='static')

import ruddock.modules.rotation.routes
