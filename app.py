from flask import Flask, render_template
from line_sweep import line_sweep_bp
from quadtree import quad_tree_bp
from visibility import visibility_bp

app = Flask(__name__)

# Registriere den Line Sweep Blueprint mit dem URL-Prefix /line_sweep
app.register_blueprint(line_sweep_bp, url_prefix='/line_sweep')

app.register_blueprint(visibility_bp, url_prefix='/visibility')

app.register_blueprint(quad_tree_bp, url_prefix='/quadtree')


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
