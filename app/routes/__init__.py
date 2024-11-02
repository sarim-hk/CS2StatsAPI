from flask import Blueprint
from .players_panel import players_panel_bp
from .player_panel import player_panel_bp
from .matches_panel import matches_panel_bp
from .match_panel import match_panel_bp
from .live_match_panel import live_match_panel_bp

bp = Blueprint('main', __name__)

bp.register_blueprint(players_panel_bp)
bp.register_blueprint(player_panel_bp)
bp.register_blueprint(matches_panel_bp)
bp.register_blueprint(match_panel_bp)
bp.register_blueprint(live_match_panel_bp)
