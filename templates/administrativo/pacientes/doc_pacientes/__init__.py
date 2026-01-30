from flask import Blueprint

pdf = Blueprint('pdf', __name__)

from .routes import *


