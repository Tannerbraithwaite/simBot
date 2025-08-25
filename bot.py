import mysql.connector as mysql
from discord.ext import commands
import discord
from datetime import date
from dotenv import load_dotenv
import os
from typing import List, Dict, Any, Optional, Tuple

# Load environment variables
load_dotenv()

# Configuration constants
TOKEN = os.environ.get('DISCORD_TOKEN')
HOST = os.environ.get('HOST')
DATABASE = os.environ.get('DATABASE')
USER = os.environ.get('DBUSER')
PASSWORD = os.environ.get('DBPASSWORD')

# Team acronyms mapping
TEAM_ACRONYMS = {
    'Wild': 'MIN', 'Ducks': 'ANA', 'Maple Leafs': 'TOR', 'Blackhawks': 'CHI', 
    'Sharks': 'SJS', 'Jets': 'WPG', 'Blues': 'STL', 'Hurricanes': 'CAR', 'Predators': 'NSH', 
    'Kings': 'LAK', 'Avalanche': 'COL', 'Rangers': 'NYR', 'Oilers': 'EDM', 'Islanders': 'NYI', 
    'Senators': 'OTT', 'Devils': 'NJD', 'Flames': 'CAL', 'Capitals': 'WSH', 'Stars': 'DAL', 
    'Canucks': 'VAN', 'Sabres': 'BUF', 'Lightning': 'TBL', 'Coyotes': 'ARZ', 'Blue Jackets': 'CBJ', 
    'Golden Knights': 'VGK', 'Panthers': 'FLA', 'Canadiens': 'MON', 'Bruins': 'BOS', 'Flyers': 'PHI', 
    'Red Wings': 'DET', 'Penguins': 'PIT', 'Kraken': 'SEA', 'Mammoth': 'ARZ',
}

# Bot setup
client = discord.Client()
bot = commands.Bot(command_prefix='$')


class DatabaseManager:
    """Handles database connections and operations."""
    
    @staticmethod
    def get_connection():
        """Create and return a database connection."""
        return mysql.connect(
            host=HOST, 
            user=USER, 
            password=PASSWORD, 
            database=DATABASE
        )
    
    @staticmethod
    def execute_query(query: str, params: Tuple = None) -> List[Tuple]:
        """Execute a query and return results."""
        connection = DatabaseManager.get_connection()
        cursor = connection.cursor(buffered=True)
        
        try:
            cursor.execute("select database();")
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()
            connection.close()


class TeamDataManager:
    """Handles team-related data operations."""
    
    @staticmethod
    def get_team_id_mapping() -> Dict[int, str]:
        """Get mapping of team IDs to team names."""
        teams_data = DatabaseManager.execute_query("SELECT Number, Name FROM proteam")
        return {team[0]: team[1] for team in teams_data}
    
    @staticmethod
    def get_current_season_id() -> int:
        """Get the current season ID."""
        result = DatabaseManager.execute_query("select MAX(Season_ID) from proteamstandings")
        return result[0][0] if result else 0
    
    @staticmethod
    def clean_team_name(team_name: str) -> str:
        """Clean team name by replacing underscores with spaces."""
        replacements = {
            'Red_Wings': 'Red Wings',
            'Blue_Jackets': 'Blue Jackets',
            'North_Stars': 'North Stars',
            'Maple_Leafs': 'Maple Leafs',
            'Golden_Knights': 'Golden Knights'
        }
        return replacements.get(team_name, team_name)


class PlayerDataManager:
    """Handles player-related data operations."""
    
    @staticmethod
    def get_player_positions() -> Dict[str, List[str]]:
        """Get player positions from database."""
        players_data = DatabaseManager.execute_query(
            "SELECT Name, PosC, PosLW, PosRW, PosD FROM players"
        )
        
        positions = {}
        for player in players_data:
            name, pos_c, pos_lw, pos_rw, pos_d = player
            positions[name] = []
            
            if pos_c == 'True':
                positions[name].extend(['C', 'F'])
            if pos_lw == 'True':
                positions[name].extend(['LW', 'F'])
            if pos_rw == 'True':
                positions[name].extend(['RW', 'F'])
            if pos_d == 'True':
                positions[name].append('D')
        
        return positions
    
    @staticmethod
    def add_positions_to_players(players: List[Dict]) -> List[Dict]:
        """Add position information to player data."""
        positions = PlayerDataManager.get_player_positions()
        
        for player in players:
            player['Position'] = positions.get(player['Name'], [])
        
        return players
    
    @staticmethod
    def merge_traded_players(players: List[Dict]) -> List[Dict]:
        """Merge stats for players who were traded."""
        current_players = [p for p in players if p['currentTeam'] == 'True']
        traded_players = [p for p in players if p['currentTeam'] == 'False']
        
        merged_players = []
        
        for current_player in current_players:
            # Find if this player was traded
            traded_player = next(
                (p for p in traded_players if p['Name'] == current_player['Name']), 
                None
            )
            
            if traded_player:
                # Merge stats
                merged_player = {
                    'Name': current_player['Name'],
                    'Team': current_player['Team'],
                    'GP': current_player['GP'] + traded_player['GP'],
                    'Shots': current_player['Shots'] + traded_player['Shots'],
                    'Goals': current_player['Goals'] + traded_player['Goals'],
                    'Assists': current_player['Assists'] + traded_player['Assists'],
                    'Points': current_player['Points'] + traded_player['Points'],
                    '+/-': current_player['+/-'] + traded_player['+/-'],
                    'Pims': current_player['Pims'] + traded_player['Pims'],
                    'ShotsBlocked': current_player['ShotsBlocked'] + traded_player['ShotsBlocked'],
                    'Hits': current_player['Hits'] + traded_player['Hits'],
                    'GWG': current_player['GWG'] + traded_player['GWG'],
                    'currentTeam': current_player['currentTeam']
                }
            else:
                merged_player = current_player.copy()
            
            merged_player['P/G'] = round(merged_player['Points'] / merged_player['GP'], 2)
            merged_players.append(merged_player)
        
        return merged_players


class FormattingUtils:
    """Utility functions for formatting data."""
    
    @staticmethod
    def replace_team_names(text: str) -> str:
        """Replace full team names with acronyms."""
        for full_name, acronym in TEAM_ACRONYMS.items():
            text = text.replace(full_name, acronym)
        return text
    
    @staticmethod
    def format_standings_row(rank: int, team: Dict, is_division: bool = False) -> str:
        """Format a single standings row."""
        wins = str(int(team['W'] + team['OTW'] + team['SOW']))
        otl = str(int(team['OTL'] + team['SOL']))
        
        if is_division and rank == 4:
            return f"{rank}.  {team['teamName']}{str(int(team['GP'])).rjust(5)}{wins.rjust(5)}{str(int(team['L'])).rjust(5)}{otl.rjust(5)}{str(int(team['points'])).rjust(5)}\n"
        
        if rank < 10:
            return f"{rank}.  {team['teamName']}{str(int(team['GP'])).rjust(5)}{wins.rjust(5)}{str(int(team['L'])).rjust(5)}{otl.rjust(5)}{str(int(team['points'])).rjust(5)}\n"
        else:
            return f"{rank}. {team['teamName']}{str(int(team['GP'])).rjust(5)}{wins.rjust(5)}{str(int(team['L'])).rjust(5)}{otl.rjust(5)}{str(int(team['points'])).rjust(5)}\n"


class StandingsManager:
    """Handles standings-related operations."""
    
    @staticmethod
    def get_team_stats(season_id: int, team_numbers: Optional[Tuple] = None) -> List[Dict]:
        """Get team statistics for standings."""
        team_mapping = TeamDataManager.get_team_id_mapping()
        
        if team_numbers:
            query = """SELECT Number, Point, GP, W, L, OTW, OTL, SOW, SOL, GF, GA 
                      FROM proteamstandings WHERE Season_ID = (%s) AND Number IN ({})""".format(
                ','.join(['%s'] * len(team_numbers))
            )
            params = (season_id,) + team_numbers
        else:
            query = """SELECT Number, Point, GP, W, L, OTW, OTL, SOW, SOL, GF, GA 
                      FROM proteamstandings WHERE Season_ID = (%s)"""
            params = (season_id,)
        
        results = DatabaseManager.execute_query(query, params)
        
        team_stats = []
        for team in results:
            team_stats.append({
                'teamName': team_mapping[team[0]],
                'points': team[1], 'GP': team[2], 'W': team[3], 'L': team[4],
                'OTW': team[5], 'OTL': team[6], 'SOW': team[7], 'SOL': team[8],
                'GF': team[9], 'GA': team[10]
            })
        
        return team_stats
    
    @staticmethod
    def sort_standings(teams: List[Dict]) -> List[Dict]:
        """Sort teams by standings criteria."""
        return sorted(teams, key=lambda k: (
            -int(k['points']), 
            int(k['GP']), 
            int(k['W']) + int(k['OTW']), 
            int(k['W']) + int(k['OTW']) + int(k['SOW'])
        ))
    
    @staticmethod
    def format_league_standings(teams: List[Dict]) -> Tuple[str, str]:
        """Format league standings into two parts."""
        standings1 = '\n    Team' + 'GP'.rjust(4) + "W".rjust(5) + "L".rjust(5) + "OTL".rjust(5) + "P".rjust(5) + '\n'
        standings2 = ''
        
        for i, team in enumerate(teams, 1):
            row = FormattingUtils.format_standings_row(i, team)
            if i <= 16:
                standings1 += row
            else:
                standings2 += row
        
        return standings1, standings2
    
    @staticmethod
    def format_division_standings(teams: List[Dict], is_conference: bool = False) -> str:
        """Format division/conference standings."""
        standings = '\n    Team' + 'GP'.rjust(4) + "W".rjust(5) + "L".rjust(5) + "OTL".rjust(5) + "P".rjust(5) + '\n'
        
        for i, team in enumerate(teams, 1):
            if is_conference and i == 10:
                standings += '----------------------\n'
            elif not is_conference and i == 4:
                standings += '----------------------\n'
            
            row = FormattingUtils.format_standings_row(i, team, not is_conference)
            standings += row
        
        return standings


class ScoresManager:
    """Handles scores-related operations."""
    
    @staticmethod
    def get_games_for_date(selected_date: str) -> Tuple[List[Tuple], str]:
        """Get games for a specific date."""
        today = str(date.today())
        
        if selected_date != today:
            games = DatabaseManager.execute_query(
                """SELECT VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore 
                   FROM todaysgame WHERE SUBSTR(Date, 1, 10) = (%s)""",
                (selected_date,)
            )
            game_date = selected_date
        else:
            # Get current date
            max_date_result = DatabaseManager.execute_query("SELECT MAX(Date) FROM todaysgame")
            max_date = max_date_result[0][0] if max_date_result else None
            
            if max_date:
                games = DatabaseManager.execute_query(
                    """SELECT VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore 
                       FROM todaysgame WHERE Date = (%s)""",
                    (max_date,)
                )
                game_date = max_date.date()
            else:
                games = []
                game_date = today
        
        return games, str(game_date)

    # NEW METHOD
    @staticmethod
    def get_recent_games_for_team(team1: str, team2: str = "all", limit: int = 10, force_all_seasons: bool = False) -> List[Tuple]:
        """Return most recent games for team1 (optionally against team2) limited to `limit` games.
        
        Args:
            team1: Primary team to get games for
            team2: Secondary team filter ('all' for any opponent)
            limit: Maximum number of games to return
            force_all_seasons: If True, ignore season filter (for when user specifies exact count)
        
        Returns list ordered newest -> oldest with fields (Date, VisitorTeam, VisitorScore, HomeTeam, HomeScore).
        """
        # Clean names (handle underscores)
        team1 = TeamDataManager.clean_team_name(team1)
        team2 = TeamDataManager.clean_team_name(team2)

        # Get current season ID for filtering
        current_season_id = TeamDataManager.get_current_season_id()
        
        if team2 != "all":
            # Head-to-head games
            if force_all_seasons:
                # Show all-time head-to-head games
                query = (
                    """SELECT Date, VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore, 
                              VisitorOT, HomeOT, VisitorSO, HomeSO """
                    "FROM todaysgame "
                    "WHERE ((VisitorTeam = %s AND HomeTeam = %s) OR (VisitorTeam = %s AND HomeTeam = %s)) "
                    "ORDER BY Date DESC LIMIT %s"""
                )
                params = (team1, team2, team2, team1, limit)
            else:
                # Show only current season head-to-head games
                query = (
                    """SELECT Date, VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore, 
                              VisitorOT, HomeOT, VisitorSO, HomeSO """
                    "FROM todaysgame "
                    "WHERE ((VisitorTeam = %s AND HomeTeam = %s) OR (VisitorTeam = %s AND HomeTeam = %s)) "
                    "AND Season_ID = %s "
                    "ORDER BY Date DESC LIMIT %s"""
                )
                params = (team1, team2, team2, team1, current_season_id, limit)
        else:
            # All opponents
            if force_all_seasons:
                # Show all-time games
                query = (
                    """SELECT Date, VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore, 
                              VisitorOT, HomeOT, VisitorSO, HomeSO """
                    "FROM todaysgame "
                    "WHERE VisitorTeam = %s OR HomeTeam = %s "
                    "ORDER BY Date DESC LIMIT %s"""
                )
                params = (team1, team1, limit)
            else:
                # Show only current season games
                query = (
                    """SELECT Date, VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore, 
                              VisitorOT, HomeOT, VisitorSO, HomeSO """
                    "FROM todaysgame "
                    "WHERE (VisitorTeam = %s OR HomeTeam = %s) AND Season_ID = %s "
                    "ORDER BY Date DESC LIMIT %s"""
                )
                params = (team1, team1, current_season_id, limit)

        return DatabaseManager.execute_query(query, params)

    @staticmethod
    def format_games_list(games: List[Tuple], team1: str = None, team2: str = None) -> str:
        """Format list of games for display with optional head-to-head record."""
        formatted = "Date              Away                Home\n"
        formatted += "-" * 50 + "\n"  # Add separator line
        
        # Calculate head-to-head record if both teams are specified
        h2h_record = None
        if team1 and team2 and team2 != "all":
            h2h_record = ScoresManager.calculate_head_to_head_record(games, team1, team2)
        
        for game in games:
            # Unpack game data - now includes OT and SO fields
            if len(game) >= 9:  # New format with OT/SO fields
                date_val, v_team, v_score, h_team, h_score, v_ot, h_ot, v_so, h_so = game
            else:  # Fallback to old format
                date_val, v_team, v_score, h_team, h_score = game
                v_ot, h_ot, v_so, h_so = False, False, False, False
            
            date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, 'strftime') else str(date_val)[:10]
            
            # Format away team with score, ensuring proper alignment
            away_team_acronym = TEAM_ACRONYMS.get(v_team, v_team)
            away_display = f"{away_team_acronym} {int(v_score)}"
            
            # Format home team with score, ensuring proper alignment  
            home_team_acronym = TEAM_ACRONYMS.get(h_team, h_team)
            home_display = f"{home_team_acronym} {int(h_score)}"
            
            # Use fixed-width formatting to align columns
            formatted += f"{date_str}  {away_display:<20} {home_display}\n"
        
        # Add head-to-head record at the bottom if available
        if h2h_record:
            formatted += "-" * 50 + "\n"  # Add separator line
            formatted += f"Record: {h2h_record}\n"
        
        return formatted
    
    @staticmethod
    def format_game_scores(games: List[Tuple]) -> str:
        """Format game scores for display."""
        game_scores = ''
        for game in games:
            visitor_team, visitor_score, home_team, home_score = game
            game_scores += (f"{visitor_team}{str(int(visitor_score)).rjust(20 - len(visitor_team))}\n"
                          f"{home_team}{str(int(home_score)).rjust(20 - len(home_team))}\n\n")
        return game_scores

    @staticmethod
    def calculate_head_to_head_record(games: List[Tuple], team1: str, team2: str) -> str:
        """Calculate head-to-head record between two teams from the given games using NHL W-L-OTL format."""
        team1_wins = 0
        team1_losses = 0
        team1_otl = 0
        team2_wins = 0
        team2_losses = 0
        team2_otl = 0
        
        # Clean team names for comparison (handle case and underscores)
        team1_clean = TeamDataManager.clean_team_name(team1.lower())
        team2_clean = TeamDataManager.clean_team_name(team2.lower())
        
        for game in games:
            # Unpack game data - now includes OT and SO fields
            if len(game) >= 9:  # New format with OT/SO fields
                date_val, v_team, v_score, h_team, h_score, v_ot, h_ot, v_so, h_so = game
            else:  # Fallback to old format
                date_val, v_team, v_score, h_team, h_score = game
                v_ot, h_ot, v_so, h_so = False, False, False, False
            
            v_score_int, h_score_int = int(v_score), int(h_score)
            
            # Clean the team names from the database for comparison
            v_team_clean = v_team.lower()
            h_team_clean = h_team.lower()
            
            # Determine which team is which (case-insensitive comparison)
            if v_team_clean == team1_clean and h_team_clean == team2_clean:
                # team1 is away, team2 is home
                if v_score_int > h_score_int:
                    team1_wins += 1
                    team2_losses += 1
                elif v_score_int < h_score_int:
                    team2_wins += 1
                    # Check if this was an OTL for team1
                    if v_ot or v_so:
                        team1_otl += 1
                    else:
                        team1_losses += 1
                else:
                    # Tie - this shouldn't happen in modern NHL, but handle it as OTL
                    team1_otl += 1
                    team2_otl += 1
            elif v_team_clean == team2_clean and h_team_clean == team1_clean:
                # team2 is away, team1 is home
                if v_score_int > h_score_int:
                    team2_wins += 1
                    # Check if this was an OTL for team1
                    if h_ot or h_so:
                        team1_otl += 1
                    else:
                        team1_losses += 1
                elif v_score_int < h_score_int:
                    team1_wins += 1
                    team2_losses += 1
                else:
                    # Tie - this shouldn't happen in modern NHL, but handle it as OTL
                    team1_otl += 1
                    team2_otl += 1
        
        # Format the record using NHL W-L-OTL format
        team1_acronym = TEAM_ACRONYMS.get(team1, team1)
        team2_acronym = TEAM_ACRONYMS.get(team2, team2)
        
        return f"{team1_acronym}: {team1_wins}-{team1_losses}-{team1_otl} vs {team2_acronym}: {team2_wins}-{team2_losses}-{team2_otl}"


class PlayerStatsManager:
    """Handles player statistics operations."""
    
    @staticmethod
    def get_player_stats(season_id: int) -> List[Dict]:
        """Get all player statistics."""
        team_mapping = TeamDataManager.get_team_id_mapping()
        
        players_data = DatabaseManager.execute_query(
            """SELECT Name, Team, ProGP, ProShots, ProG, ProA, ProPoint, ProPlusMinus, 
                      ProPim, ProShotsBlock, ProHits, ProGW, Active 
               FROM playerstats WHERE Season_ID = (%s) AND proGP > 0""",
            (season_id,)
        )
        
        cleaned_stats = []
        for player in players_data:
            cleaned_stats.append({
                'Name': player[0],
                'Team': team_mapping[int(player[1])],
                'GP': player[2], 'Shots': player[3], 'Goals': player[4],
                'Assists': player[5], 'Points': player[6], '+/-': player[7],
                'Pims': player[8], 'ShotsBlocked': player[9], 'Hits': player[10],
                'GWG': player[11], 'currentTeam': player[12]
            })
        
        return cleaned_stats
    
    @staticmethod
    def filter_players_by_team_and_position(players: List[Dict], team: str, position: str) -> List[Dict]:
        """Filter players by team and position."""
        if team != 'all':
            players = [p for p in players if p['Team'] == team]
        
        if position != 'all':
            players = [p for p in players if position in p['Position']]
        
        return players
    
    @staticmethod
    def sort_players_by_stat(players: List[Dict], stat: str) -> List[Dict]:
        """Sort players by specified statistic."""
        stat_mapping = {
            'P/G': 'P/G', 'Goals': 'Goals', 'Assists': 'Assists', 'Points': 'Points',
            'Shots': 'Shots', '+/-': '+/-', 'Pims': 'Pims', 'Shots_blocked': 'ShotsBlocked',
            'GWG': 'GWG', 'Hits': 'Hits'
        }
        
        sort_key = stat_mapping.get(stat, 'Points')
        reverse = sort_key != 'P/G'  # GAA sorts in ascending order
        
        return sorted(players, key=lambda k: (-k[sort_key] if reverse else k[sort_key]))
    
    @staticmethod
    def format_player_leaders(players: List[Dict], stat: str) -> str:
        """Format player leaders for display."""
        leaders = 'Team' + 'Name'.rjust(7) + stat.rjust(22) + '\n'
        
        for player in players:
            leaders += (f"{TEAM_ACRONYMS[player['Team']]}    {player['Name']}"
                      f"{str(player[stat]).rjust(26 - len(str(player['Name'])))}\n")
        
        return leaders


class GoalieStatsManager:
    """Handles goalie statistics operations."""
    
    @staticmethod
    def get_goalie_stats(season_id: int) -> List[Dict]:
        """Get all goalie statistics."""
        team_mapping = TeamDataManager.get_team_id_mapping()
        
        goalies_data = DatabaseManager.execute_query(
            """SELECT Name, Team, ProGP, ProMinPlay, ProW, ProL, ProOTL, ProShutouts, 
                      ProGA, ProSA, Active 
               FROM goaliestats WHERE Season_ID = (%s) AND proGP > 0""",
            (season_id,)
        )
        
        cleaned_stats = []
        for goalie in goalies_data:
            saves = int(goalie[9]) - int(goalie[8])  # SA - GA
            cleaned_stats.append({
                'Name': goalie[0],
                'Team': team_mapping[int(goalie[1])],
                'GP': goalie[2], 'Minutes': goalie[3], 'Wins': goalie[4],
                'Losses': goalie[5], 'OTL': goalie[6], 'SO': goalie[7],
                'GA': goalie[8], 'Saves': saves, 'SA': int(goalie[9]),
                'currentTeam': goalie[10]
            })
        
        return cleaned_stats
    
    @staticmethod
    def merge_traded_goalies(goalies: List[Dict]) -> List[Dict]:
        """Merge stats for goalies who were traded."""
        current_goalies = [g for g in goalies if g['currentTeam'] == 'True']
        traded_goalies = [g for g in goalies if g['currentTeam'] == 'False']
        
        merged_goalies = []
        
        for current_goalie in current_goalies:
            traded_goalie = next(
                (g for g in traded_goalies if g['Name'] == current_goalie['Name']), 
                None
            )
            
            if traded_goalie:
                merged_goalie = {
                    'Name': current_goalie['Name'],
                    'Team': current_goalie['Team'],
                    'GP': current_goalie['GP'] + traded_goalie['GP'],
                    'Minutes': current_goalie['Minutes'] + traded_goalie['Minutes'],
                    'Wins': current_goalie['Wins'] + traded_goalie['Wins'],
                    'Losses': current_goalie['Losses'] + traded_goalie['Losses'],
                    'OTL': current_goalie['OTL'] + traded_goalie['OTL'],
                    'SO': current_goalie['SO'] + traded_goalie['SO'],
                    'GA': current_goalie['GA'] + traded_goalie['GA'],
                    'Saves': current_goalie['Saves'] + traded_goalie['Saves'],
                    'SA': current_goalie['SA'] + traded_goalie['SA'],
                    'currentTeam': current_goalie['currentTeam']
                }
            else:
                merged_goalie = current_goalie.copy()
            
            merged_goalies.append(merged_goalie)
        
        return merged_goalies
    
    @staticmethod
    def calculate_goalie_stats(goalies: List[Dict]) -> List[Dict]:
        """Calculate additional goalie statistics."""
        for goalie in goalies:
            goalie['GP'] = int(goalie['GP'])
            total_shots = goalie['Saves'] + goalie['GA']
            goalie['SVP'] = round(goalie['Saves'] / total_shots, 3) if total_shots > 0 else 0.000
            goalie['GAA'] = round(goalie['GA'] / (goalie['Minutes'] / 3600), 2) if goalie['Minutes'] > 0 else 0.00
        
        return goalies
    
    @staticmethod
    def sort_goalies_by_stat(goalies: List[Dict], stat: str) -> List[Dict]:
        """Sort goalies by specified statistic."""
        stat_mapping = {
            'GAA': 'GAA', 'SV%': 'SVP', 'W': 'Wins', 'GP': 'GP',
            'SO': 'SO', 'L': 'Losses', 'S': 'Saves'
        }
        
        sort_key = stat_mapping.get(stat, 'SVP')
        reverse = sort_key != 'GAA'  # GAA sorts in ascending order
        
        return sorted(goalies, key=lambda k: (-k[sort_key] if reverse else k[sort_key]))
    
    @staticmethod
    def format_goalie_leaders(goalies: List[Dict], stat: str) -> str:
        """Format goalie leaders for display."""
        leaders = 'Team' + 'goalie'.rjust(10) + stat.rjust(16) + '\n'
        
        for goalie in goalies:
            leaders += (f"{TEAM_ACRONYMS[goalie['Team']]}     {goalie['Name']}"
                      f"{str(goalie[stat]).rjust(22 - len(str(goalie['Name'])))}\n")
        
        return leaders


# Bot event handlers
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


# Bot commands
@bot.command(name='scores', help="type $scores followed by the date(ie. $scores 2020/03/29) to get the scores for a specific date")
async def scoredate(ctx, selecteddate: str = str(date.today())):
    """Display scores for a specific date."""
    try:
        games, game_date = ScoresManager.get_games_for_date(selecteddate)
        
        if not games:
            await ctx.send("No games found for the specified date.")
            return
        
        game_scores = ScoresManager.format_game_scores(games)
        title_score = f"the scores for {game_date}"
        scores_formatted = f"```{game_scores}```"
        
        embed = discord.Embed(title=title_score, url='http://cchlsim.com/pro_scores.php', color=0xeee657)
        embed.add_field(name="Scores", value=scores_formatted)
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"Error retrieving scores: {str(e)}")


@bot.command(name='standings', help="type $standings followed by the division of conference(ie. $standings Pacific, $standings Western) to get the scores for a division or conference. You can view wildcard standings with $standings Western_wildcard. Default is league standings")
async def standings(ctx, div_con: Optional[str] = None):
    """Display standings for league, conference, division, or wildcard."""
    try:
        season_id = TeamDataManager.get_current_season_id()
        
        if div_con is None:
            # League standings
            team_stats = StandingsManager.get_team_stats(season_id)
            sorted_teams = StandingsManager.sort_standings(team_stats)
            standings1, standings2 = StandingsManager.format_league_standings(sorted_teams)
            
            formatted_standings1 = FormattingUtils.replace_team_names(f"```{standings1}```")
            formatted_standings2 = FormattingUtils.replace_team_names(f"```{standings2}```")
            
            embed = discord.Embed(title="League Standings", color=0xeee657)
            embed.add_field(name="League Standings", value=formatted_standings1, inline=False)
            embed.add_field(name="------------------------------", value=formatted_standings2, inline=False)
            
        else:
            div_con = div_con.capitalize()
            
            if div_con in ["Western_wildcard", "Eastern_wildcard"]:
                # Wildcard standings
                if div_con == "Western_wildcard":
                    div1_query = "SELECT Number FROM proteam WHERE Division = 'Central'"
                    div2_query = "SELECT Number FROM proteam WHERE Division = 'Pacific'"
                else:  # Eastern_wildcard
                    div1_query = "SELECT Number FROM proteam WHERE Division = 'Northeast'"
                    div2_query = "SELECT Number FROM proteam WHERE Division = 'Atlantic'"
                
                div1_teams = DatabaseManager.execute_query(div1_query)
                div2_teams = DatabaseManager.execute_query(div2_query)
                
                div1_numbers = tuple(team[0] for team in div1_teams)
                div2_numbers = tuple(team[0] for team in div2_teams)
                
                div1_stats = StandingsManager.get_team_stats(season_id, div1_numbers)
                div2_stats = StandingsManager.get_team_stats(season_id, div2_numbers)
                
                sorted_div1 = StandingsManager.sort_standings(div1_stats)
                sorted_div2 = StandingsManager.sort_standings(div2_stats)
                
                # Format wildcard standings
                standings = '\n    Team' + 'GP'.rjust(4) + "W".rjust(5) + "L".rjust(5) + "OTL".rjust(5) + "P".rjust(5) + '\n'
                
                # Division leaders
                div1_leaders = sorted_div1[:3]
                div2_leaders = sorted_div2[:3]
                
                for i, team in enumerate(div1_leaders, 1):
                    standings += FormattingUtils.format_standings_row(i, team)
                
                standings += '-----------------------\n'
                
                for i, team in enumerate(div2_leaders, 1):
                    standings += FormattingUtils.format_standings_row(i, team)
                
                standings += '-----------------------\n'
                
                # Wildcard teams
                wildcard_teams = sorted_div1[3:] + sorted_div2[3:]
                wildcard_teams = StandingsManager.sort_standings(wildcard_teams)
                
                for i, team in enumerate(wildcard_teams, 1):
                    if i == 3:
                        standings += '-----------------------\n'
                    standings += FormattingUtils.format_standings_row(i, team)
                
                formatted_standings = FormattingUtils.replace_team_names(f"```{standings}```")
                embed = discord.Embed(title=f"{div_con} Standings", color=0xeee657)
                embed.add_field(name=f"{div_con} Standings", value=formatted_standings, inline=False)
                
            else:
                # Conference/Division standings
                division_queries = {
                    "Western": "SELECT Number FROM proteam WHERE Conference = 'Western'",
                    "Eastern": "SELECT Number FROM proteam WHERE Conference = 'Eastern'",
                    "Pacific": "SELECT Number FROM proteam WHERE Division = 'Pacific'",
                    "Northeast": "SELECT Number FROM proteam WHERE Division = 'Northeast'",
                    "North East": "SELECT Number FROM proteam WHERE Division = 'Northeast'",
                    "Metro": "SELECT Number FROM proteam WHERE Division = 'Northeast'",
                    "Metropolitan": "SELECT Number FROM proteam WHERE Division = 'Northeast'",
                    "Atlantic": "SELECT Number FROM proteam WHERE Division = 'Atlantic'",
                    "Central": "SELECT Number FROM proteam WHERE Division = 'Central'"
                }
                
                if div_con not in division_queries:
                    await ctx.send("We could not find that division, please check spelling(Atlantic, Central, Northeast/Metro, Pacific, Western, Eastern, Western_wildcard, Eastern_wildcard)")
                    return
                
                team_numbers = DatabaseManager.execute_query(division_queries[div_con])
                team_numbers_tuple = tuple(team[0] for team in team_numbers)
                
                team_stats = StandingsManager.get_team_stats(season_id, team_numbers_tuple)
                sorted_teams = StandingsManager.sort_standings(team_stats)
                
                is_conference = div_con in ["Western", "Eastern"]
                standings = StandingsManager.format_division_standings(sorted_teams, is_conference)
                
                formatted_standings = FormattingUtils.replace_team_names(f"```{standings}```")
                embed = discord.Embed(title=f"{div_con} Standings", color=0xeee657)
                embed.add_field(name=f"{div_con} Standings", value=formatted_standings, inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"Error retrieving standings: {str(e)}")


@bot.command(name='scoring_leaders', help="type $scoring_leaders followed by the team you want to filter by, then the position, then the stat for example $scoring_leaders Flames D Goals will give you the flames Defence Goal leaders, $scoring_leaders all F Hits will give you the forward hit leaders for the entire league. positions are C, RW, LW, D. available stats are Points, Goals, Assists, Hits, Pims, +/-, Shots, ShotsBlocked, and GWG. If a team has a space in it's name it requires an underscore ie. $scoring_leaders Golden_Knights")
async def scoring_leaders(ctx, team_selected: str = 'all', position: str = 'all', stat: str = 'Points'):
    """Display scoring leaders for specified criteria."""
    try:
        season_id = TeamDataManager.get_current_season_id()
        team_selected = TeamDataManager.clean_team_name(team_selected)
        
        # Get player stats
        player_stats = PlayerStatsManager.get_player_stats(season_id)
        merged_players = PlayerDataManager.merge_traded_players(player_stats)
        players_with_positions = PlayerDataManager.add_positions_to_players(merged_players)
        
        # Filter players
        filtered_players = PlayerStatsManager.filter_players_by_team_and_position(
            players_with_positions, team_selected, position
        )
        
        # Sort players
        sorted_players = PlayerStatsManager.sort_players_by_stat(filtered_players, stat)
        
        # Limit to top 10
        amount_to_display = min(10, len(sorted_players))
        top_players = sorted_players[:amount_to_display]
        
        if not top_players:
            await ctx.send("No players found matching the specified criteria.")
            return
        
        # Format and display
        player_leaders = PlayerStatsManager.format_player_leaders(top_players, stat)
        players_formatted = f"```{player_leaders}```"
        
        embed = discord.Embed(title=f"{stat} Leaders", color=0xeee657)
        embed.add_field(name="Players", value=players_formatted)
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"Error retrieving scoring leaders: {str(e)}")


@bot.command(name='goalie_leaders', help="type $goalie_leaders followed by the stat you wish to see(ie. $goalie_leaders GAA, SV%, W, GP, SO, L, S) to get the top ten goalies by a certain stat. you can add a second argument to get more goalies, and a third argument to filter by games played. The default stat is save percentage, the default games played is 0, and the default amount of goalies is ten. For example $goalie_leaders will give you the top ten goalies in save percentage out of all goalies. $goalie_leaders GAA 15 10 will give you the top 15 goalies in GAA who have played more than 10 games")
async def goalie_leaders(ctx, stat: str = 'SV%', amount_wanted: int = 10, games_wanted: int = 0):
    """Display goalie leaders for specified criteria."""
    try:
        season_id = TeamDataManager.get_current_season_id()
        
        # Get goalie stats
        goalie_stats = GoalieStatsManager.get_goalie_stats(season_id)
        merged_goalies = GoalieStatsManager.merge_traded_goalies(goalie_stats)
        goalies_with_stats = GoalieStatsManager.calculate_goalie_stats(merged_goalies)
        
        # Filter by games played
        filtered_goalies = [g for g in goalies_with_stats if g['GP'] >= games_wanted]
        
        # Sort goalies
        sorted_goalies = GoalieStatsManager.sort_goalies_by_stat(filtered_goalies, stat)
        
        # Limit to requested amount
        amount_to_display = min(amount_wanted, len(sorted_goalies))
        top_goalies = sorted_goalies[:amount_to_display]
        
        if not top_goalies:
            await ctx.send("No goalies found matching the specified criteria.")
            return
        
        # Format and display
        goalie_leaders = GoalieStatsManager.format_goalie_leaders(top_goalies, stat)
        goalies_formatted = f"```{goalie_leaders}```"
        
        embed = discord.Embed(title=f"Goalie Leaders for {stat}", color=0xeee657)
        embed.add_field(name="Goalies", value=goalies_formatted)
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"Error retrieving goalie leaders: {str(e)}")


@bot.command(name='scores_by_team', help="Usage: $scores_by_team <team1> [team2|all] [num_games]. Examples:\n$scores_by_team Oilers\n$scores_by_team Oilers Canucks\n$scores_by_team Oilers all 20")
async def scores_by_team(ctx, team1: str, team2: str = 'all', num_games: int = 10):
    """Return recent games for a team, optionally head-to-head, limited to num_games."""
    try:
        # Convert num_games if user swapped order (team2 may be numeric)
        if team2.isdigit():
            num_games = int(team2)
            team2 = 'all'
        else:
            # third arg may override num_games
            # ctx.message.content split handled by discord.py but easier parse using *args; here we rely on signature default
            pass
        # Clamp
        num_games = min(max(int(num_games), 1), 82)

        # Determine if we should force all seasons or stick to current season
        # If user specified a specific number of games (not default 10), show all-time
        # If user specified default 10, show only current season
        force_all_seasons = (num_games != 10) or (ctx.message.content.split()[-1].isdigit())
        
        games = ScoresManager.get_recent_games_for_team(team1, team2, num_games, force_all_seasons)
        if not games:
            season_context = "this season" if not force_all_seasons else "all time"
            await ctx.send(f"No games found for {team1.title()} {season_context} matching those criteria.")
            return
        
        games_formatted = ScoresManager.format_games_list(games, team1, team2)
        
        # Create appropriate title based on context
        if force_all_seasons:
            embed_title = f"Last {len(games)} games: {team1.title()}" + (f" vs {team2.title()}" if team2 != 'all' else '') + " (all time)"
        else:
            embed_title = f"Last {len(games)} games: {team1.title()}" + (f" vs {team2.title()}" if team2 != 'all' else '') + " (this season)"
            
        embed = discord.Embed(title=embed_title, color=0xeee657)
        embed.add_field(name="Games", value=f"```{games_formatted}```", inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error retrieving games: {str(e)}")


# Run the bot
if __name__ == "__main__":
    print("Starting Discord bot... (press Ctrl+C to quit)")
    bot.run(TOKEN)
