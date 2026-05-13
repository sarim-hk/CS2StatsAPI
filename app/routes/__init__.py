from fastapi import APIRouter

from .live_match_panel import router as live_match_router
from .match_panel import router as match_router
from .matches_panel import router as matches_router
from .player_panel import router as player_router
from .playerelo_panel import router as playerelo_router
from .players_panel import router as players_router
from .playerstats_panel import router as playerstats_router

router = APIRouter()

router.include_router(players_router)
router.include_router(player_router)
router.include_router(matches_router)
router.include_router(match_router)
router.include_router(live_match_router)
router.include_router(playerstats_router)
router.include_router(playerelo_router)
