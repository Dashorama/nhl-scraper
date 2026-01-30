"""MoneyPuck advanced stats scraper.

MoneyPuck provides free CSV downloads of advanced NHL analytics including:
- Expected Goals (xG)
- Corsi and Fenwick
- Scoring chances and high-danger chances
- Zone starts
- On-ice and individual stats

Data URL: https://moneypuck.com/moneypuck/playerData/seasonSummary/
"""

import csv
import io
from datetime import datetime
from typing import Any

from .base import BaseScraper


class MoneyPuckScraper(BaseScraper):
    """Scraper for MoneyPuck advanced stats CSV exports."""

    SOURCE_NAME = "moneypuck"
    BASE_URL = "https://moneypuck.com"
    REQUESTS_PER_SECOND = 0.5  # Very conservative - they provide free data

    async def get_current_season(self) -> str:
        """Get the current season ID (e.g., '2024')."""
        now = datetime.now()
        # MoneyPuck uses single year format (start year of season)
        return str(now.year if now.month >= 10 else now.year - 1)

    async def _fetch_csv(self, url: str) -> list[dict[str, Any]]:
        """Fetch and parse a CSV file from MoneyPuck."""
        response = await self.get(url)
        content = response.text

        reader = csv.DictReader(io.StringIO(content))
        return list(reader)

    async def scrape_skater_stats(
        self,
        season: str | None = None,
        situation: str = "all",
    ) -> list[dict[str, Any]]:
        """
        Fetch advanced skater statistics.
        
        Args:
            season: Season year (e.g., '2024' for 2024-25 season)
            situation: Game situation filter:
                - "all": All situations
                - "5on5": 5-on-5 only
                - "5on4": Power play
                - "4on5": Penalty kill
                
        Returns:
            List of advanced stat dicts for each skater
        """
        if season is None:
            season = await self.get_current_season()

        # MoneyPuck CSV URL format
        csv_url = f"/moneypuck/playerData/seasonSummary/{season}/regular/skaters.csv"

        try:
            raw_data = await self._fetch_csv(csv_url)
        except Exception as e:
            self.logger.error("moneypuck_fetch_failed", url=csv_url, error=str(e))
            return []

        # Filter by situation if needed
        if situation != "all":
            raw_data = [r for r in raw_data if r.get("situation") == situation]
        else:
            # MoneyPuck has "all" situation in the data
            raw_data = [r for r in raw_data if r.get("situation") == "all"]

        players = []
        for row in raw_data:
            try:
                players.append(self._parse_skater_row(row, season))
            except (ValueError, KeyError) as e:
                self.logger.warning(
                    "parse_skater_failed",
                    player=row.get("name"),
                    error=str(e),
                )

        self.logger.info(
            "scraped_skater_stats",
            count=len(players),
            season=season,
            situation=situation,
        )
        return players

    def _parse_skater_row(self, row: dict[str, Any], season: str) -> dict[str, Any]:
        """Parse a single row from MoneyPuck skater CSV."""
        
        def safe_int(val: Any, default: int = 0) -> int:
            try:
                return int(float(val)) if val else default
            except (ValueError, TypeError):
                return default

        def safe_float(val: Any, default: float | None = None) -> float | None:
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default

        return {
            "player_id": safe_int(row.get("playerId")),
            "player_name": row.get("name", ""),
            "team_abbrev": row.get("team", ""),
            "position": row.get("position", ""),
            "season": f"{season}{int(season)+1}",  # Convert to YYYYYYYY format
            "situation": row.get("situation", "all"),
            "games_played": safe_int(row.get("games_played")),
            "toi_seconds": safe_int(row.get("icetime")),
            # Corsi
            "corsi_for": safe_int(row.get("onIce_corsiPercentage")) if row.get("onIce_corsiPercentage") else safe_int(row.get("I_F_shotAttempts", 0)) + safe_int(row.get("OnIce_F_shotAttempts", 0)),
            "corsi_against": safe_int(row.get("OnIce_A_shotAttempts")),
            "corsi_pct": safe_float(row.get("onIce_corsiPercentage")),
            "corsi_rel": safe_float(row.get("offIce_corsiPercentage")),
            # Fenwick
            "fenwick_for": safe_int(row.get("OnIce_F_unblockedShotAttempts")),
            "fenwick_against": safe_int(row.get("OnIce_A_unblockedShotAttempts")),
            "fenwick_pct": safe_float(row.get("onIce_fenwickPercentage")),
            # xG
            "xg_for": safe_float(row.get("OnIce_F_xGoals"), 0.0),
            "xg_against": safe_float(row.get("OnIce_A_xGoals"), 0.0),
            "xg_pct": safe_float(row.get("onIce_xGoalsPercentage")),
            "individual_xg": safe_float(row.get("I_F_xGoals"), 0.0),
            "goals_above_expected": safe_float(row.get("I_F_xGoals_with_rebounds_normalized_per_game")),
            # Scoring Chances
            "scoring_chances_for": safe_int(row.get("OnIce_F_scoringChances")),
            "scoring_chances_against": safe_int(row.get("OnIce_A_scoringChances")),
            "high_danger_chances_for": safe_int(row.get("OnIce_F_highDangerShotAttempts")),
            "high_danger_chances_against": safe_int(row.get("OnIce_A_highDangerShotAttempts")),
            "high_danger_goals_for": safe_int(row.get("OnIce_F_highDangerGoals")),
            "high_danger_goals_against": safe_int(row.get("OnIce_A_highDangerGoals")),
            # Zone Starts
            "offensive_zone_starts": safe_int(row.get("I_F_oZoneShiftStarts")),
            "defensive_zone_starts": safe_int(row.get("I_F_dZoneShiftStarts")),
            "neutral_zone_starts": safe_int(row.get("I_F_neutralZoneShiftStarts")),
            "offensive_zone_start_pct": safe_float(row.get("offensiveZoneStartPct")),
            # On-Ice
            "on_ice_sh_pct": safe_float(row.get("onIce_F_shootingPct")),
            "on_ice_sv_pct": safe_float(row.get("onIce_A_savePct")),
            "pdo": safe_float(row.get("PDO")),
            # Individual
            "shots": safe_int(row.get("I_F_shotsOnGoal")),
            "goals": safe_int(row.get("I_F_goals")),
            "primary_assists": safe_int(row.get("I_F_primaryAssists")),
            "secondary_assists": safe_int(row.get("I_F_secondaryAssists")),
            "individual_corsi_for": safe_int(row.get("I_F_shotAttempts")),
            "source": "moneypuck",
        }

    async def scrape_goalie_stats(self, season: str | None = None) -> list[dict[str, Any]]:
        """
        Fetch advanced goalie statistics.
        
        Args:
            season: Season year (e.g., '2024' for 2024-25 season)
            
        Returns:
            List of advanced stat dicts for each goalie
        """
        if season is None:
            season = await self.get_current_season()

        csv_url = f"/moneypuck/playerData/seasonSummary/{season}/regular/goalies.csv"

        try:
            raw_data = await self._fetch_csv(csv_url)
        except Exception as e:
            self.logger.error("moneypuck_fetch_failed", url=csv_url, error=str(e))
            return []

        # Filter to "all" situation
        raw_data = [r for r in raw_data if r.get("situation") == "all"]

        goalies = []
        for row in raw_data:
            try:
                goalies.append(self._parse_goalie_row(row, season))
            except (ValueError, KeyError) as e:
                self.logger.warning(
                    "parse_goalie_failed",
                    player=row.get("name"),
                    error=str(e),
                )

        self.logger.info("scraped_goalie_stats", count=len(goalies), season=season)
        return goalies

    def _parse_goalie_row(self, row: dict[str, Any], season: str) -> dict[str, Any]:
        """Parse a single row from MoneyPuck goalie CSV."""
        
        def safe_int(val: Any, default: int = 0) -> int:
            try:
                return int(float(val)) if val else default
            except (ValueError, TypeError):
                return default

        def safe_float(val: Any, default: float | None = None) -> float | None:
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default

        shots_against = safe_int(row.get("shotsOnGoal"))
        goals_against = safe_int(row.get("goals"))
        saves = shots_against - goals_against

        return {
            "player_id": safe_int(row.get("playerId")),
            "player_name": row.get("name", ""),
            "team_abbrev": row.get("team", ""),
            "season": f"{season}{int(season)+1}",
            "situation": row.get("situation", "all"),
            "games_played": safe_int(row.get("games_played")),
            "toi_seconds": safe_int(row.get("icetime")),
            # Basic
            "shots_against": shots_against,
            "goals_against": goals_against,
            "saves": saves,
            "save_pct": safe_float(row.get("onGoalSavePercentage")),
            # xG
            "xg_against": safe_float(row.get("xGoals"), 0.0),
            "goals_saved_above_expected": safe_float(row.get("goalsAboveExpected")),
            # By danger
            "low_danger_shots": safe_int(row.get("lowDangerShotsOnGoal")),
            "low_danger_goals": safe_int(row.get("lowDangerGoals")),
            "low_danger_save_pct": safe_float(row.get("lowDangerSavePercentage")),
            "medium_danger_shots": safe_int(row.get("mediumDangerShotsOnGoal")),
            "medium_danger_goals": safe_int(row.get("mediumDangerGoals")),
            "medium_danger_save_pct": safe_float(row.get("mediumDangerSavePercentage")),
            "high_danger_shots": safe_int(row.get("highDangerShotsOnGoal")),
            "high_danger_goals": safe_int(row.get("highDangerGoals")),
            "high_danger_save_pct": safe_float(row.get("highDangerSavePercentage")),
            # Rebounds
            "rebounds_given": safe_int(row.get("reboundsCreated")),
            "rebound_goals_against": safe_int(row.get("reboundGoals")),
            # Play style
            "freeze_pct": safe_float(row.get("freezePct")),
            "source": "moneypuck",
        }

    # Abstract method implementations required by BaseScraper
    async def scrape_players(self, season: str | None = None) -> list[dict[str, Any]]:
        """Scrape all player advanced stats."""
        skaters = await self.scrape_skater_stats(season)
        goalies = await self.scrape_goalie_stats(season)
        return skaters + goalies

    async def scrape_teams(self) -> list[dict[str, Any]]:
        """Not applicable for MoneyPuck."""
        return []

    async def scrape_games(
        self,
        season: str | None = None,
        team_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Not applicable for MoneyPuck."""
        return []
