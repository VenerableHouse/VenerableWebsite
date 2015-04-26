from flask import Blueprint
blueprint = Blueprint('hassle', __name__, template_folder='templates',
    static_folder='static')

import RuddockWebsite.modules.hassle.routes
