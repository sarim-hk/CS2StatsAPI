from flask import Blueprint
from .match_routes import match_bp
from .player_routes import player_bp
from .playerstat_routes import playerstat_bp
from .team_routes import team_bp

bp = Blueprint('main', __name__)

bp.register_blueprint(match_bp)
bp.register_blueprint(player_bp)
bp.register_blueprint(playerstat_bp)
bp.register_blueprint(team_bp)
