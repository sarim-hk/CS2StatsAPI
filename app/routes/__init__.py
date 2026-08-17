from fastapi import APIRouter
from .match_panel import router as match_router
from .matches_panel import router as matches_router
from .player_panel import router as player_router
from .playerelo_panel import router as playerelo_router
from .players_panel import router as players_router
from .playerstats_panel import router as playerstats_router
from .team_panel import router as team_router
from .teamelo_panel import router as teamelo_router
from .upload_match import router as upload_match_router
from .upload_player import router as upload_player_router

router = APIRouter()

router.include_router(players_router)
router.include_router(player_router)
router.include_router(matches_router)
router.include_router(match_router)
router.include_router(playerstats_router)
router.include_router(playerelo_router)
router.include_router(team_router)
router.include_router(teamelo_router)
router.include_router(upload_match_router)
router.include_router(upload_player_router)
