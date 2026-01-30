"""Contract and salary data models."""

from datetime import date
from typing import Literal

from pydantic import BaseModel


class ContractClause(BaseModel):
    """No-movement or no-trade clause details."""

    clause_type: Literal["NMC", "NTC", "M-NTC"]  # Modified NTC
    starts: date | None = None
    ends: date | None = None
    teams_protected: int | None = None  # For M-NTC


class ContractYear(BaseModel):
    """Single year of a contract."""

    season: str  # e.g., "20242025"
    base_salary: int  # In dollars
    signing_bonus: int = 0
    performance_bonus: int = 0
    cap_hit: int


class PlayerContract(BaseModel):
    """Player contract information."""

    player_id: int
    player_name: str
    team_abbrev: str

    # Contract terms
    contract_type: Literal["Entry-Level", "Standard", "35+", "PTO", "AHL", "Unknown"] = "Unknown"
    signing_date: date | None = None
    start_season: str  # e.g., "20232024"
    end_season: str
    total_years: int
    total_value: int  # Total contract value in dollars
    aav: int  # Average annual value (cap hit)

    # Current season
    current_cap_hit: int
    current_salary: int
    current_bonus: int = 0

    # Status
    expiry_status: Literal["UFA", "RFA", "10.2(c)"] | None = None
    arbitration_eligible: bool = False

    # Clauses
    clauses: list[ContractClause] = []

    # Details by year
    years: list[ContractYear] = []

    # Metadata
    source: str = "puckpedia"
    scraped_at: str | None = None

    @property
    def years_remaining(self) -> int:
        """Calculate years remaining on contract."""
        if not self.end_season:
            return 0
        try:
            end_year = int(self.end_season[:4])
            from datetime import datetime

            current_year = datetime.now().year
            # NHL season spans two calendar years
            if datetime.now().month >= 10:
                current_season_start = current_year
            else:
                current_season_start = current_year - 1
            return max(0, end_year - current_season_start)
        except (ValueError, TypeError):
            return 0

    @property
    def has_trade_protection(self) -> bool:
        """Check if player has any trade protection."""
        return len(self.clauses) > 0
