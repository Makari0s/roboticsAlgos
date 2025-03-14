from flask import Blueprint

visibility_bp = Blueprint('visibility', __name__, template_folder='templates')

from . import routes  # Importiert die Routen
