from flask import Blueprint, render_template, request

estudios_bp = Blueprint('estudios', __name__)

@estudios_bp.route('/')
def estudios_home():
    vista = request.args.get('vista')
    return render_template('estudios/index.html', vista=vista)
