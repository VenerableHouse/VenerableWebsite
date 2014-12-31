from flask import Blueprint
blueprint = Blueprint('hassle', __name__, template_folder='templates')

import modules.hassle.routes
