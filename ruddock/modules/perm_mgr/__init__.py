import flask
blueprint = flask.Blueprint('perm_mgr', __name__,
                template_folder='templates', static_folder='static')

import ruddock.modules.perm_mgr.routes
