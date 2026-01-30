"""Pydantic data models for NHL entities."""

from .player import Player, PlayerStats, GoalieStats
from .team import Team, TeamStandings, TeamSeasonStats
from .game import Game, GameStats
from .contract import PlayerContract, ContractClause, ContractYear
from .roster import RosterPlayer, TeamRoster
from .advanced_stats import AdvancedSkaterStats, AdvancedGoalieStats

__all__ = [
    # Player
    "Player",
    "PlayerStats",
    "GoalieStats",
    # Team
    "Team",
    "TeamStandings",
    "TeamSeasonStats",
    # Game
    "Game",
    "GameStats",
    # Contract
    "PlayerContract",
    "ContractClause",
    "ContractYear",
    # Roster
    "RosterPlayer",
    "TeamRoster",
    # Advanced
    "AdvancedSkaterStats",
    "AdvancedGoalieStats",
]
