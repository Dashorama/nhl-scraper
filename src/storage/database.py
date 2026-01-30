"""SQLite database storage for scraped NHL data."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker
import structlog

logger = structlog.get_logger()
Base = declarative_base()


class PlayerRecord(Base):
    """Player table."""

    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    position = Column(String(2))
    team_abbrev = Column(String(3))
    birth_date = Column(String(10))
    birth_country = Column(String(50))
    draft_year = Column(Integer)
    draft_round = Column(Integer)
    draft_pick = Column(Integer)
    raw_data = Column(Text)  # JSON blob for extra data
    updated_at = Column(DateTime, default=datetime.utcnow)


class PlayerStatsRecord(Base):
    """Player season stats table."""

    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, index=True)
    season = Column(String(8), index=True)
    team_abbrev = Column(String(3))
    games_played = Column(Integer)
    goals = Column(Integer)
    assists = Column(Integer)
    points = Column(Integer)
    plus_minus = Column(Integer)
    pim = Column(Integer)
    shots = Column(Integer)
    toi_seconds = Column(Integer)
    source = Column(String(50))  # Which scraper provided this
    raw_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TeamRecord(Base):
    """Team table."""

    __tablename__ = "teams"

    abbrev = Column(String(3), primary_key=True)
    name = Column(String(100))
    conference = Column(String(20))
    division = Column(String(20))
    raw_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


class GameRecord(Base):
    """Game table."""

    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    season = Column(String(8), index=True)
    game_date = Column(String(10), index=True)
    game_type = Column(String(2))
    home_team = Column(String(3))
    away_team = Column(String(3))
    home_score = Column(Integer)
    away_score = Column(Integer)
    game_state = Column(String(20))
    raw_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


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

    __table_args__ = (Index("ix_advanced_player_season", "player_id", "season"),)


class RosterRecord(Base):
    """Team roster assignments."""

    __tablename__ = "rosters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_abbrev = Column(String(3), index=True)
    player_id = Column(Integer, index=True)
    player_name = Column(String(100))
    season = Column(String(8), index=True)

    jersey_number = Column(Integer)
    position = Column(String(2))
    roster_status = Column(String(20), default="active")

    raw_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_roster_team_season", "team_abbrev", "season"),)


class Database:
    """SQLite database wrapper for NHL data."""

    def __init__(self, db_path: str | Path = "data/nhl.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.logger = logger.bind(component="database")

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def upsert_players(self, players: list[dict[str, Any]]) -> int:
        """Insert or update player records."""
        with self.get_session() as session:
            count = 0
            for p in players:
                player_id = p.get("id")
                if not player_id:
                    continue

                existing = session.get(PlayerRecord, player_id)
                if existing:
                    existing.first_name = p.get("first_name", existing.first_name)
                    existing.last_name = p.get("last_name", existing.last_name)
                    existing.position = p.get("position", existing.position)
                    existing.team_abbrev = p.get("team", existing.team_abbrev)
                    existing.raw_data = json.dumps(p)
                    existing.updated_at = datetime.utcnow()
                else:
                    session.add(PlayerRecord(
                        id=player_id,
                        first_name=p.get("first_name"),
                        last_name=p.get("last_name"),
                        position=p.get("position"),
                        team_abbrev=p.get("team"),
                        birth_date=p.get("birth_date"),
                        birth_country=p.get("birth_country"),
                        draft_year=p.get("draft_year"),
                        draft_round=p.get("draft_round"),
                        draft_pick=p.get("draft_pick"),
                        raw_data=json.dumps(p),
                    ))
                count += 1

            session.commit()
            self.logger.info("upserted_players", count=count)
            return count

    def upsert_teams(self, teams: list[dict[str, Any]]) -> int:
        """Insert or update team records."""
        with self.get_session() as session:
            count = 0
            for t in teams:
                abbrev = t.get("abbreviation")
                if not abbrev:
                    continue

                existing = session.get(TeamRecord, abbrev)
                if existing:
                    existing.name = t.get("name", existing.name)
                    existing.conference = t.get("conference", existing.conference)
                    existing.division = t.get("division", existing.division)
                    existing.raw_data = json.dumps(t)
                    existing.updated_at = datetime.utcnow()
                else:
                    session.add(TeamRecord(
                        abbrev=abbrev,
                        name=t.get("name"),
                        conference=t.get("conference"),
                        division=t.get("division"),
                        raw_data=json.dumps(t),
                    ))
                count += 1

            session.commit()
            self.logger.info("upserted_teams", count=count)
            return count

    def upsert_games(self, games: list[dict[str, Any]]) -> int:
        """Insert or update game records."""
        with self.get_session() as session:
            count = 0
            for g in games:
                game_id = g.get("id")
                if not game_id:
                    continue

                existing = session.get(GameRecord, game_id)
                if existing:
                    existing.home_score = g.get("home_score", existing.home_score)
                    existing.away_score = g.get("away_score", existing.away_score)
                    existing.game_state = g.get("game_state", existing.game_state)
                    existing.raw_data = json.dumps(g)
                    existing.updated_at = datetime.utcnow()
                else:
                    session.add(GameRecord(
                        id=game_id,
                        season=g.get("season"),
                        game_date=g.get("date"),
                        game_type=str(g.get("game_type")),
                        home_team=g.get("home_team"),
                        away_team=g.get("away_team"),
                        home_score=g.get("home_score"),
                        away_score=g.get("away_score"),
                        game_state=g.get("game_state"),
                        raw_data=json.dumps(g),
                    ))
                count += 1

            session.commit()
            self.logger.info("upserted_games", count=count)
            return count

    def get_stats(self) -> dict[str, int]:
        """Get counts of all records."""
        with self.get_session() as session:
            return {
                "players": session.query(PlayerRecord).count(),
                "teams": session.query(TeamRecord).count(),
                "games": session.query(GameRecord).count(),
                "contracts": session.query(ContractRecord).count(),
                "advanced_stats": session.query(AdvancedStatsRecord).count(),
                "rosters": session.query(RosterRecord).count(),
            }

    def upsert_contracts(self, contracts: list[dict[str, Any]]) -> int:
        """Insert or update contract records."""
        with self.get_session() as session:
            count = 0
            for c in contracts:
                player_name = c.get("player_name")
                team_abbrev = c.get("team_abbrev")
                if not player_name:
                    continue

                # Find existing by player name and team
                existing = (
                    session.query(ContractRecord)
                    .filter_by(player_name=player_name, team_abbrev=team_abbrev)
                    .first()
                )

                if existing:
                    existing.current_cap_hit = c.get("current_cap_hit", existing.current_cap_hit)
                    existing.current_salary = c.get("current_salary", existing.current_salary)
                    existing.aav = c.get("aav", existing.aav)
                    existing.total_years = c.get("total_years", existing.total_years)
                    existing.expiry_status = c.get("expiry_status", existing.expiry_status)
                    existing.has_nmc = c.get("has_nmc", existing.has_nmc)
                    existing.has_ntc = c.get("has_ntc", existing.has_ntc)
                    existing.raw_data = json.dumps(c)
                    existing.updated_at = datetime.utcnow()
                else:
                    session.add(
                        ContractRecord(
                            player_id=c.get("player_id"),
                            player_name=player_name,
                            team_abbrev=team_abbrev,
                            season=c.get("season"),
                            contract_type=c.get("contract_type"),
                            start_season=c.get("start_season"),
                            end_season=c.get("end_season"),
                            total_years=c.get("total_years"),
                            total_value=c.get("total_value"),
                            aav=c.get("aav"),
                            current_cap_hit=c.get("current_cap_hit"),
                            current_salary=c.get("current_salary"),
                            expiry_status=c.get("expiry_status"),
                            has_nmc=c.get("has_nmc", False),
                            has_ntc=c.get("has_ntc", False),
                            source=c.get("source"),
                            raw_data=json.dumps(c),
                        )
                    )
                count += 1

            session.commit()
            self.logger.info("upserted_contracts", count=count)
            return count

    def upsert_advanced_stats(self, stats: list[dict[str, Any]]) -> int:
        """Insert or update advanced statistics records."""
        with self.get_session() as session:
            count = 0
            for s in stats:
                player_id = s.get("player_id")
                season = s.get("season")
                situation = s.get("situation", "all")
                if not player_id:
                    continue

                # Find existing by player, season, and situation
                existing = (
                    session.query(AdvancedStatsRecord)
                    .filter_by(player_id=player_id, season=season, situation=situation)
                    .first()
                )

                if existing:
                    # Update all stats fields
                    existing.player_name = s.get("player_name", existing.player_name)
                    existing.team_abbrev = s.get("team_abbrev", existing.team_abbrev)
                    existing.position = s.get("position", existing.position)
                    existing.games_played = s.get("games_played", existing.games_played)
                    existing.toi_seconds = s.get("toi_seconds", existing.toi_seconds)
                    existing.corsi_for = s.get("corsi_for", existing.corsi_for)
                    existing.corsi_against = s.get("corsi_against", existing.corsi_against)
                    existing.corsi_pct = s.get("corsi_pct", existing.corsi_pct)
                    existing.corsi_rel = s.get("corsi_rel", existing.corsi_rel)
                    existing.fenwick_for = s.get("fenwick_for", existing.fenwick_for)
                    existing.fenwick_against = s.get("fenwick_against", existing.fenwick_against)
                    existing.fenwick_pct = s.get("fenwick_pct", existing.fenwick_pct)
                    existing.xg_for = s.get("xg_for", existing.xg_for)
                    existing.xg_against = s.get("xg_against", existing.xg_against)
                    existing.xg_pct = s.get("xg_pct", existing.xg_pct)
                    existing.goals_above_expected = s.get("goals_above_expected", existing.goals_above_expected)
                    existing.oz_start_pct = s.get("offensive_zone_start_pct", existing.oz_start_pct)
                    existing.hd_chances_for = s.get("high_danger_chances_for", existing.hd_chances_for)
                    existing.hd_chances_against = s.get("high_danger_chances_against", existing.hd_chances_against)
                    existing.raw_data = json.dumps(s)
                    existing.updated_at = datetime.utcnow()
                else:
                    session.add(
                        AdvancedStatsRecord(
                            player_id=player_id,
                            player_name=s.get("player_name"),
                            team_abbrev=s.get("team_abbrev"),
                            season=season,
                            position=s.get("position"),
                            situation=situation,
                            games_played=s.get("games_played"),
                            toi_seconds=s.get("toi_seconds"),
                            corsi_for=s.get("corsi_for"),
                            corsi_against=s.get("corsi_against"),
                            corsi_pct=s.get("corsi_pct"),
                            corsi_rel=s.get("corsi_rel"),
                            fenwick_for=s.get("fenwick_for"),
                            fenwick_against=s.get("fenwick_against"),
                            fenwick_pct=s.get("fenwick_pct"),
                            xg_for=s.get("xg_for"),
                            xg_against=s.get("xg_against"),
                            xg_pct=s.get("xg_pct"),
                            goals_above_expected=s.get("goals_above_expected"),
                            oz_start_pct=s.get("offensive_zone_start_pct"),
                            hd_chances_for=s.get("high_danger_chances_for"),
                            hd_chances_against=s.get("high_danger_chances_against"),
                            source=s.get("source"),
                            raw_data=json.dumps(s),
                        )
                    )
                count += 1

            session.commit()
            self.logger.info("upserted_advanced_stats", count=count)
            return count

    def upsert_rosters(self, rosters: list[dict[str, Any]]) -> int:
        """Insert or update roster records from team roster data."""
        with self.get_session() as session:
            count = 0

            for roster in rosters:
                team_abbrev = roster.get("team_abbrev")
                season = roster.get("season")

                # Process all player groups
                all_players = (
                    roster.get("forwards", [])
                    + roster.get("defensemen", [])
                    + roster.get("goalies", [])
                )

                for p in all_players:
                    player_id = p.get("player_id")
                    if not player_id:
                        continue

                    # Find existing by player, team, and season
                    existing = (
                        session.query(RosterRecord)
                        .filter_by(player_id=player_id, team_abbrev=team_abbrev, season=season)
                        .first()
                    )

                    player_name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()

                    if existing:
                        existing.player_name = player_name
                        existing.jersey_number = p.get("jersey_number", existing.jersey_number)
                        existing.position = p.get("position", existing.position)
                        existing.roster_status = p.get("roster_status", existing.roster_status)
                        existing.raw_data = json.dumps(p)
                        existing.updated_at = datetime.utcnow()
                    else:
                        session.add(
                            RosterRecord(
                                team_abbrev=team_abbrev,
                                player_id=player_id,
                                player_name=player_name,
                                season=season,
                                jersey_number=p.get("jersey_number"),
                                position=p.get("position"),
                                roster_status=p.get("roster_status", "active"),
                                raw_data=json.dumps(p),
                            )
                        )
                    count += 1

            session.commit()
            self.logger.info("upserted_rosters", count=count)
            return count
