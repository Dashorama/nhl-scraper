# NHL Scraper Expansion Design

## Overview

Expanding the NHL scraper to collect comprehensive player data including:
- Full team rosters with positions
- Complete player statistics (basic + advanced)
- Contract information (salary, cap hit, term)
- Advanced analytics (Corsi, Fenwick, xG, zone starts)

## Data Sources

### 1. NHL Official API (api-web.nhle.com)
- **Rosters**: `GET /roster/{team_abbrev}/current`
- **Player Details**: `GET /player/{player_id}/landing`
- **Season Stats**: `GET /player/{player_id}/game-log/{season}/{game_type}`
- **All Skaters Stats**: `GET /stats/rest/en/skater/summary?...` (stats.nhl.com)
- **All Goalies Stats**: `GET /stats/rest/en/goalie/summary?...`

### 2. PuckPedia (puckpedia.com)
- Contract data scraping from team pages
- Player contract details: salary, cap hit, bonuses, clauses
- Note: Requires HTML scraping as no public API

### 3. MoneyPuck (moneypuck.com)
- Advanced stats CSV exports at `/moneypuck/playerData/seasonSummary/`
- Includes: xG, Corsi, Fenwick, zone starts, scoring chances
- Direct CSV download - no scraping needed

---

## Data Models

### src/models/contract.py

```python
"""Contract and salary data models."""

from datetime import date
from decimal import Decimal
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
    contract_type: Literal["Entry-Level", "Standard", "35+", "PTO", "AHL"]
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
```

### src/models/roster.py

```python
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
    
    # Status
    roster_status: Literal["active", "injured", "IR", "LTIR", "minors", "suspended"] = "active"
    injury_note: str | None = None
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


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
```

### src/models/advanced_stats.py

```python
"""Advanced analytics models."""

from pydantic import BaseModel


class AdvancedSkaterStats(BaseModel):
    """Advanced analytics for skaters."""
    
    player_id: int
    player_name: str
    team_abbrev: str
    season: str
    situation: str = "all"  # "all", "5on5", "pp", "pk"
    
    games_played: int = 0
    toi_seconds: int = 0
    
    # Corsi (all shot attempts)
    corsi_for: int = 0
    corsi_against: int = 0
    corsi_pct: float | None = None
    corsi_for_per_60: float | None = None
    corsi_against_per_60: float | None = None
    corsi_rel: float | None = None  # Relative to team
    
    # Fenwick (unblocked shot attempts)
    fenwick_for: int = 0
    fenwick_against: int = 0
    fenwick_pct: float | None = None
    fenwick_rel: float | None = None
    
    # Expected Goals (xG)
    xg_for: float = 0.0
    xg_against: float = 0.0
    xg_pct: float | None = None
    xg_for_per_60: float | None = None
    xg_against_per_60: float | None = None
    goals_above_expected: float | None = None
    
    # Scoring Chances
    scoring_chances_for: int = 0
    scoring_chances_against: int = 0
    high_danger_chances_for: int = 0
    high_danger_chances_against: int = 0
    high_danger_goals_for: int = 0
    high_danger_goals_against: int = 0
    
    # Zone Starts
    offensive_zone_starts: int = 0
    defensive_zone_starts: int = 0
    neutral_zone_starts: int = 0
    offensive_zone_start_pct: float | None = None
    
    # On-Ice vs Off-Ice
    on_ice_sh_pct: float | None = None
    on_ice_sv_pct: float | None = None
    pdo: float | None = None  # SH% + SV%
    
    # Individual
    individual_xg: float = 0.0
    shots: int = 0
    individual_corsi_for: int = 0
    
    source: str = "moneypuck"


class AdvancedGoalieStats(BaseModel):
    """Advanced analytics for goalies."""
    
    player_id: int
    player_name: str
    team_abbrev: str
    season: str
    situation: str = "all"
    
    games_played: int = 0
    toi_seconds: int = 0
    
    # Basic
    shots_against: int = 0
    goals_against: int = 0
    saves: int = 0
    save_pct: float | None = None
    
    # Expected Goals
    xg_against: float = 0.0
    goals_saved_above_expected: float | None = None
    gsax_per_60: float | None = None
    
    # By Danger Level
    low_danger_shots: int = 0
    low_danger_goals: int = 0
    low_danger_save_pct: float | None = None
    
    medium_danger_shots: int = 0
    medium_danger_goals: int = 0
    medium_danger_save_pct: float | None = None
    
    high_danger_shots: int = 0
    high_danger_goals: int = 0
    high_danger_save_pct: float | None = None
    
    # Rebounds
    rebounds_given: int = 0
    rebound_goals_against: int = 0
    
    source: str = "moneypuck"
```

---

## Database Schema Updates

### src/storage/database.py additions

```python
class ContractRecord(Base):
    """Player contract table."""
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, index=True)
    player_name = Column(String(100))
    team_abbrev = Column(String(3), index=True)
    season = Column(String(8), index=True)
    
    contract_type = Column(String(20))
    start_season = Column(String(8))
    end_season = Column(String(8))
    total_years = Column(Integer)
    total_value = Column(Integer)
    aav = Column(Integer)
    current_cap_hit = Column(Integer)
    current_salary = Column(Integer)
    
    expiry_status = Column(String(10))
    has_nmc = Column(Boolean, default=False)
    has_ntc = Column(Boolean, default=False)
    
    source = Column(String(50))
    raw_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AdvancedStatsRecord(Base):
    """Advanced player statistics table."""
    __tablename__ = "advanced_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, index=True)
    player_name = Column(String(100))
    team_abbrev = Column(String(3))
    season = Column(String(8), index=True)
    position = Column(String(2))
    situation = Column(String(10), default="all")
    
    games_played = Column(Integer)
    toi_seconds = Column(Integer)
    
    # Corsi
    corsi_for = Column(Integer)
    corsi_against = Column(Integer)
    corsi_pct = Column(Float)
    corsi_rel = Column(Float)
    
    # Fenwick
    fenwick_for = Column(Integer)
    fenwick_against = Column(Integer)
    fenwick_pct = Column(Float)
    
    # xG
    xg_for = Column(Float)
    xg_against = Column(Float)
    xg_pct = Column(Float)
    goals_above_expected = Column(Float)
    
    # Zone starts
    oz_start_pct = Column(Float)
    
    # High danger
    hd_chances_for = Column(Integer)
    hd_chances_against = Column(Integer)
    
    source = Column(String(50))
    raw_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


class RosterRecord(Base):
    """Team roster assignments."""
    __tablename__ = "rosters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_abbrev = Column(String(3), index=True)
    player_id = Column(Integer, index=True)
    season = Column(String(8), index=True)
    
    jersey_number = Column(Integer)
    position = Column(String(2))
    roster_status = Column(String(20))
    
    raw_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_roster_team_season", "team_abbrev", "season"),
    )
```

---

## Scraper Modules

### src/scrapers/nhl_roster.py

Extends NHL API scraper for full roster data:
- `/roster/{team}/current` - Current roster
- `/roster/{team}/{season}` - Historical rosters  
- `/player/{id}/landing` - Full player details

### src/scrapers/puckpedia.py

HTML scraping from puckpedia.com:
- Team cap pages: `puckpedia.com/team/{team}`
- Player pages: `puckpedia.com/player/{name}`
- Requires BeautifulSoup parsing

### src/scrapers/moneypuck.py

CSV download and parsing:
- Base URL: `https://moneypuck.com/moneypuck/playerData/seasonSummary/`
- Files: `all_skaters.csv`, `all_goalies.csv` per season
- Direct pandas/csv parsing

---

## CLI Commands

```
nhl-stats scrape-rosters [--team ABBREV]
    Scrape full rosters from NHL API for all or specific team

nhl-stats scrape-contracts [--team ABBREV]
    Scrape contract data from PuckPedia

nhl-stats scrape-advanced [--season SEASON]
    Download and parse MoneyPuck advanced stats

nhl-stats scrape-all [--season SEASON]
    Run all scrapers in sequence

nhl-stats show-roster TEAM
    Display team roster in formatted table

nhl-stats show-contracts TEAM
    Display team contracts and cap situation

nhl-stats show-player PLAYER_ID
    Show all data for a player (stats, contract, advanced)
```

---

## Implementation Priority

1. **Phase 1**: NHL API roster scraper (most reliable, official data)
2. **Phase 2**: MoneyPuck advanced stats (simple CSV parsing)
3. **Phase 3**: PuckPedia contracts (complex HTML scraping)

Each phase delivers working, testable functionality.
