from flask import Blueprint

quad_tree_bp = Blueprint('quadtree', __name__, template_folder='templates')

from . import routes
