"""Team roster models."""

from datetime import date
from typing import Literal

from pydantic import BaseModel


class RosterPlayer(BaseModel):
    """A player on a team roster."""

    player_id: int
    first_name: str
    last_name: str
    jersey_number: int | None = None
    position: Literal["C", "L", "R", "D", "G"]
    shoots_catches: Literal["L", "R"] | None = None

    # Physical
    height_inches: int | None = None
    weight_pounds: int | None = None
    birth_date: date | None = None
    age: int | None = None
    birth_country: str | None = None
    nationality: str | None = None

    # Status
    roster_status: Literal["active", "injured", "IR", "LTIR", "minors", "suspended"] = "active"
    injury_note: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_goalie(self) -> bool:
        return self.position == "G"

    @property
    def is_forward(self) -> bool:
        return self.position in ("C", "L", "R")

    @property
    def is_defenseman(self) -> bool:
        return self.position == "D"


class TeamRoster(BaseModel):
    """Complete team roster."""

    team_abbrev: str
    team_name: str
    season: str
    as_of_date: str

    forwards: list[RosterPlayer] = []
    defensemen: list[RosterPlayer] = []
    goalies: list[RosterPlayer] = []

    # Cap info
    cap_space: int | None = None
    cap_ceiling: int | None = None
    total_cap_hit: int | None = None

    @property
    def total_players(self) -> int:
        return len(self.forwards) + len(self.defensemen) + len(self.goalies)

    @property
    def all_players(self) -> list[RosterPlayer]:
        """Get all players as a flat list."""
        return self.forwards + self.defensemen + self.goalies

    def get_player_by_id(self, player_id: int) -> RosterPlayer | None:
        """Find a player by ID."""
        for player in self.all_players:
            if player.player_id == player_id:
                return player
        return None

    def get_player_by_number(self, number: int) -> RosterPlayer | None:
        """Find a player by jersey number."""
        for player in self.all_players:
            if player.jersey_number == number:
                return player
        return None
