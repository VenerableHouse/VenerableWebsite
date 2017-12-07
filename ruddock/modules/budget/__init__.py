import flask
blueprint = flask.Blueprint('budget', __name__,
  template_folder='templates', static_folder='static')

import ruddock.modules.budget.routes
