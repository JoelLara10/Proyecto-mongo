from flask import Blueprint

pdf_med = Blueprint('pdf_med', __name__)

from .notas_med import *
