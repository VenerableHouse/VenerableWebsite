from flask import Blueprint
blueprint = Blueprint('users', __name__, template_folder='templates')

import modules.users.routes
