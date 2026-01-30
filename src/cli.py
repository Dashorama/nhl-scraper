"""Command-line interface for NHL scraper."""

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .scrapers import NHLAPIScraper, NHLRosterScraper, MoneyPuckScraper, PuckPediaScraper
from .storage import Database
from .utils import setup_logging

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.option("--json-logs", is_flag=True, help="Output logs as JSON")
@click.pass_context
def main(ctx: click.Context, verbose: bool, json_logs: bool) -> None:
    """NHL Analytics Scraper - Collect hockey data from multiple sources."""
    ctx.ensure_object(dict)
    setup_logging(level="DEBUG" if verbose else "INFO", json_output=json_logs)
    ctx.obj["db"] = Database()


@main.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show database statistics."""
    db: Database = ctx.obj["db"]
    counts = db.get_stats()

    table = Table(title="Database Statistics")
    table.add_column("Entity", style="cyan")
    table.add_column("Count", justify="right", style="green")

    for entity, count in counts.items():
        table.add_row(entity.title(), str(count))

    console.print(table)


@main.command()
@click.option("--season", "-s", help="Season (e.g., 20232024)")
@click.pass_context
def scrape_teams(ctx: click.Context, season: str | None) -> None:
    """Scrape team data from NHL API."""
    db: Database = ctx.obj["db"]

    async def run():
        async with NHLAPIScraper() as scraper:
            teams = await scraper.scrape_teams()
            db.upsert_teams(teams)
            console.print(f"[green]✓ Scraped {len(teams)} teams[/green]")

    asyncio.run(run())


@main.command()
@click.option("--season", "-s", help="Season (e.g., 20232024)")
@click.pass_context
def scrape_players(ctx: click.Context, season: str | None) -> None:
    """Scrape player data from NHL API."""
    db: Database = ctx.obj["db"]

    async def run():
        async with NHLAPIScraper() as scraper:
            players = await scraper.scrape_players(season)
            db.upsert_players(players)
            console.print(f"[green]✓ Scraped {len(players)} players[/green]")

    asyncio.run(run())


@main.command()
@click.option("--season", "-s", help="Season (e.g., 20232024)")
@click.pass_context
def scrape_games(ctx: click.Context, season: str | None) -> None:
    """Scrape game schedule from NHL API."""
    db: Database = ctx.obj["db"]

    async def run():
        async with NHLAPIScraper() as scraper:
            games = await scraper.scrape_games(season)
            db.upsert_games(games)
            console.print(f"[green]✓ Scraped {len(games)} games[/green]")

    asyncio.run(run())


@main.command()
@click.option("--season", "-s", help="Season (e.g., 20232024)")
@click.pass_context
def scrape_all(ctx: click.Context, season: str | None) -> None:
    """Scrape all data from NHL API."""
    db: Database = ctx.obj["db"]

    async def run():
        async with NHLAPIScraper() as scraper:
            console.print("[bold]Scraping teams...[/bold]")
            teams = await scraper.scrape_teams()
            db.upsert_teams(teams)
            console.print(f"  [green]✓ {len(teams)} teams[/green]")

            console.print("[bold]Scraping players...[/bold]")
            players = await scraper.scrape_players(season)
            db.upsert_players(players)
            console.print(f"  [green]✓ {len(players)} players[/green]")

            console.print("[bold]Scraping games...[/bold]")
            games = await scraper.scrape_games(season)
            db.upsert_games(games)
            console.print(f"  [green]✓ {len(games)} games[/green]")

            console.print("\n[bold green]All done![/bold green]")

    asyncio.run(run())


@main.command()
@click.pass_context
def standings(ctx: click.Context) -> None:
    """Show current NHL standings."""

    async def run():
        async with NHLAPIScraper() as scraper:
            data = await scraper.scrape_standings()

            for division in ["Atlantic", "Metropolitan", "Central", "Pacific"]:
                table = Table(title=f"{division} Division")
                table.add_column("Team", style="cyan")
                table.add_column("GP", justify="right")
                table.add_column("W", justify="right", style="green")
                table.add_column("L", justify="right", style="red")
                table.add_column("OT", justify="right")
                table.add_column("PTS", justify="right", style="bold")
                table.add_column("GF", justify="right")
                table.add_column("GA", justify="right")
                table.add_column("Diff", justify="right")

                div_teams = [t for t in data["teams"] if t["division"] == division]
                div_teams.sort(key=lambda t: t["points"], reverse=True)

                for t in div_teams:
                    diff = t["goal_diff"]
                    diff_str = f"+{diff}" if diff > 0 else str(diff)
                    table.add_row(
                        t["team"],
                        str(t["games_played"]),
                        str(t["wins"]),
                        str(t["losses"]),
                        str(t["ot_losses"]),
                        str(t["points"]),
                        str(t["goals_for"]),
                        str(t["goals_against"]),
                        diff_str,
                    )

                console.print(table)
                console.print()

    asyncio.run(run())


@main.command()
@click.option("--team", "-t", help="Team abbreviation (e.g., TOR)")
@click.option("--season", "-s", help="Season (e.g., 20242025)")
@click.pass_context
def scrape_rosters(ctx: click.Context, team: str | None, season: str | None) -> None:
    """Scrape full rosters from NHL API."""
    db: Database = ctx.obj["db"]

    async def run():
        async with NHLRosterScraper() as scraper:
            if team:
                console.print(f"[bold]Scraping roster for {team}...[/bold]")
                roster = await scraper.scrape_roster(team, season)
                db.upsert_rosters([roster])
                total = len(roster.get("forwards", [])) + len(roster.get("defensemen", [])) + len(roster.get("goalies", []))
                console.print(f"[green]✓ Scraped {total} players for {team}[/green]")
            else:
                console.print("[bold]Scraping all team rosters...[/bold]")
                rosters = await scraper.scrape_all_rosters(season)
                db.upsert_rosters(rosters)
                total = sum(
                    len(r.get("forwards", [])) + len(r.get("defensemen", [])) + len(r.get("goalies", []))
                    for r in rosters
                )
                console.print(f"[green]✓ Scraped {total} players across {len(rosters)} teams[/green]")

    asyncio.run(run())


@main.command()
@click.option("--season", "-s", help="Season year (e.g., 2024)")
@click.pass_context
def scrape_advanced(ctx: click.Context, season: str | None) -> None:
    """Scrape advanced stats from MoneyPuck."""
    db: Database = ctx.obj["db"]

    async def run():
        async with MoneyPuckScraper() as scraper:
            console.print("[bold]Downloading MoneyPuck skater stats...[/bold]")
            skaters = await scraper.scrape_skater_stats(season)
            db.upsert_advanced_stats(skaters)
            console.print(f"  [green]✓ {len(skaters)} skaters[/green]")

            console.print("[bold]Downloading MoneyPuck goalie stats...[/bold]")
            goalies = await scraper.scrape_goalie_stats(season)
            db.upsert_advanced_stats(goalies)
            console.print(f"  [green]✓ {len(goalies)} goalies[/green]")

            console.print("\n[bold green]Advanced stats complete![/bold green]")

    asyncio.run(run())


@main.command()
@click.option("--team", "-t", help="Team abbreviation (e.g., TOR)")
@click.pass_context
def scrape_contracts(ctx: click.Context, team: str | None) -> None:
    """Scrape contract data from PuckPedia."""
    db: Database = ctx.obj["db"]

    async def run():
        async with PuckPediaScraper() as scraper:
            if team:
                console.print(f"[bold]Scraping contracts for {team}...[/bold]")
                contracts = await scraper.scrape_team_contracts(team)
                db.upsert_contracts(contracts)
                console.print(f"[green]✓ Scraped {len(contracts)} contracts[/green]")
            else:
                console.print("[bold]Scraping all team contracts...[/bold]")
                console.print("[dim](This may take a while to be respectful to PuckPedia's servers)[/dim]")
                contracts = await scraper.scrape_all_contracts()
                db.upsert_contracts(contracts)
                console.print(f"[green]✓ Scraped {len(contracts)} contracts[/green]")

    asyncio.run(run())


@main.command()
@click.option("--season", "-s", help="Season (e.g., 20242025)")
@click.pass_context
def scrape_full(ctx: click.Context, season: str | None) -> None:
    """Scrape all data from all sources."""
    db: Database = ctx.obj["db"]

    async def run():
        # NHL API - basic data
        async with NHLAPIScraper() as scraper:
            console.print("[bold cyan]═══ NHL API ═══[/bold cyan]")
            
            console.print("  Scraping teams...")
            teams = await scraper.scrape_teams()
            db.upsert_teams(teams)
            console.print(f"  [green]✓ {len(teams)} teams[/green]")

            console.print("  Scraping players...")
            players = await scraper.scrape_players(season)
            db.upsert_players(players)
            console.print(f"  [green]✓ {len(players)} players[/green]")

        # NHL Roster API
        async with NHLRosterScraper() as scraper:
            console.print("\n[bold cyan]═══ Rosters ═══[/bold cyan]")
            rosters = await scraper.scrape_all_rosters(season)
            db.upsert_rosters(rosters)
            total = sum(
                len(r.get("forwards", [])) + len(r.get("defensemen", [])) + len(r.get("goalies", []))
                for r in rosters
            )
            console.print(f"  [green]✓ {total} roster entries[/green]")

        # MoneyPuck advanced stats
        async with MoneyPuckScraper() as scraper:
            console.print("\n[bold cyan]═══ Advanced Stats (MoneyPuck) ═══[/bold cyan]")
            skaters = await scraper.scrape_skater_stats(season)
            goalies = await scraper.scrape_goalie_stats(season)
            db.upsert_advanced_stats(skaters + goalies)
            console.print(f"  [green]✓ {len(skaters)} skaters, {len(goalies)} goalies[/green]")

        # PuckPedia contracts
        async with PuckPediaScraper() as scraper:
            console.print("\n[bold cyan]═══ Contracts (PuckPedia) ═══[/bold cyan]")
            console.print("  [dim](Slow scrape to respect their servers)[/dim]")
            contracts = await scraper.scrape_all_contracts()
            db.upsert_contracts(contracts)
            console.print(f"  [green]✓ {len(contracts)} contracts[/green]")

        console.print("\n[bold green]═══ All Done! ═══[/bold green]")

    asyncio.run(run())


@main.command()
@click.argument("team")
@click.pass_context
def show_roster(ctx: click.Context, team: str) -> None:
    """Display team roster in formatted table."""

    async def run():
        async with NHLRosterScraper() as scraper:
            roster = await scraper.scrape_roster(team.upper())

            console.print(f"\n[bold]{team.upper()} Roster[/bold]")
            console.print(f"[dim]As of {roster['as_of_date'][:10]}[/dim]\n")

            # Forwards
            if roster["forwards"]:
                table = Table(title="Forwards", show_header=True)
                table.add_column("#", style="cyan", width=3)
                table.add_column("Name", style="white")
                table.add_column("Pos", style="green")
                table.add_column("Shoots", style="dim")
                table.add_column("Country", style="dim")

                for p in sorted(roster["forwards"], key=lambda x: x.get("jersey_number") or 99):
                    table.add_row(
                        str(p.get("jersey_number", "")),
                        f"{p['first_name']} {p['last_name']}",
                        p.get("position", ""),
                        p.get("shoots_catches", ""),
                        p.get("birth_country", ""),
                    )
                console.print(table)

            # Defensemen
            if roster["defensemen"]:
                table = Table(title="Defensemen", show_header=True)
                table.add_column("#", style="cyan", width=3)
                table.add_column("Name", style="white")
                table.add_column("Shoots", style="dim")
                table.add_column("Country", style="dim")

                for p in sorted(roster["defensemen"], key=lambda x: x.get("jersey_number") or 99):
                    table.add_row(
                        str(p.get("jersey_number", "")),
                        f"{p['first_name']} {p['last_name']}",
                        p.get("shoots_catches", ""),
                        p.get("birth_country", ""),
                    )
                console.print(table)

            # Goalies
            if roster["goalies"]:
                table = Table(title="Goalies", show_header=True)
                table.add_column("#", style="cyan", width=3)
                table.add_column("Name", style="white")
                table.add_column("Catches", style="dim")
                table.add_column("Country", style="dim")

                for p in sorted(roster["goalies"], key=lambda x: x.get("jersey_number") or 99):
                    table.add_row(
                        str(p.get("jersey_number", "")),
                        f"{p['first_name']} {p['last_name']}",
                        p.get("shoots_catches", ""),
                        p.get("birth_country", ""),
                    )
                console.print(table)

    asyncio.run(run())


@main.command()
@click.argument("player_id", type=int)
@click.pass_context
def show_player(ctx: click.Context, player_id: int) -> None:
    """Show detailed info for a player by ID."""

    async def run():
        async with NHLRosterScraper() as scraper:
            player = await scraper.scrape_player_details(player_id)

            console.print(f"\n[bold]{player['first_name']} {player['last_name']}[/bold]")
            console.print(f"[dim]#{player.get('jersey_number', 'N/A')} • {player.get('position', 'N/A')} • {player.get('team_abbrev', 'N/A')}[/dim]\n")

            info_table = Table(show_header=False, box=None)
            info_table.add_column("Field", style="cyan")
            info_table.add_column("Value")

            info_table.add_row("Birth Date", player.get("birth_date", "N/A"))
            info_table.add_row("Birthplace", f"{player.get('birth_city', '')}, {player.get('birth_country', '')}")
            info_table.add_row("Height", f"{player.get('height_inches', 0) // 12}'{player.get('height_inches', 0) % 12}\"" if player.get("height_inches") else "N/A")
            info_table.add_row("Weight", f"{player.get('weight_pounds', 'N/A')} lbs")
            info_table.add_row("Shoots/Catches", player.get("shoots_catches", "N/A"))

            if player.get("draft_year"):
                info_table.add_row(
                    "Draft",
                    f"{player['draft_year']} R{player.get('draft_round', '?')}, Pick {player.get('draft_pick', '?')} (#{player.get('draft_overall', '?')} overall) by {player.get('draft_team', 'N/A')}"
                )

            console.print(info_table)

            # Career stats summary if available
            career = player.get("career_stats", {})
            if career:
                console.print("\n[bold]Career Stats[/bold]")
                reg = career.get("regularSeason", {})
                if reg:
                    console.print(f"  GP: {reg.get('gamesPlayed', 0)} | G: {reg.get('goals', 0)} | A: {reg.get('assists', 0)} | P: {reg.get('points', 0)}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
