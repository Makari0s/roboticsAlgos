from flask import Blueprint

line_sweep_bp = Blueprint('line_sweep', __name__, template_folder='templates')

from . import routes
