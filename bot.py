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
        """Clean team name by replacing underscores with spaces and handling common variations."""
        # First, replace any underscores with spaces for all inputs
        cleaned = team_name.replace('_', ' ')
        
        # Handle specific underscore replacements (for backward compatibility)
        replacements = {
            'Red_Wings': 'Red Wings',
            'Blue_Jackets': 'Blue Jackets',
            'North_Stars': 'North Stars',
            'Maple_Leafs': 'Maple Leafs',
            'Golden_Knights': 'Golden Knights'
        }
        
        # Apply underscore replacements if exact match (for backward compatibility)
        if team_name in replacements:
            cleaned = replacements[team_name]
        
        # Handle common case variations and abbreviations
        team_variations = {
            'panthers': 'Panthers',
            'rangers': 'Rangers',
            'oilers': 'Oilers',
            'flames': 'Flames',
            'canucks': 'Canucks',
            'bruins': 'Bruins',
            'leafs': 'Maple Leafs',
            'maple leafs': 'Maple Leafs',
            'kings': 'Kings',
            'ducks': 'Ducks',
            'sharks': 'Sharks',
            'jets': 'Jets',
            'blues': 'Blues',
            'wild': 'Wild',
            'avalanche': 'Avalanche',
            'stars': 'Stars',
            'blackhawks': 'Blackhawks',
            'predators': 'Predators',
            'lightning': 'Lightning',
            'capitals': 'Capitals',
            'islanders': 'Islanders',
            'devils': 'Devils',
            'flyers': 'Flyers',
            'penguins': 'Penguins',
            'senators': 'Senators',
            'sabres': 'Sabres',
            'red wings': 'Red Wings',
            'blue jackets': 'Blue Jackets',
            'golden knights': 'Golden Knights',
            'coyotes': 'Coyotes',
            'kraken': 'Kraken'
        }
        
        # Check for variations (case-insensitive)
        for variation, official_name in team_variations.items():
            if cleaned.lower() == variation.lower():
                return official_name
        
        return cleaned


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
        """Get games for a specific date. If no games found for selected_date, 
        return games from the most recent date available in the database."""
        games = DatabaseManager.execute_query(
            """SELECT VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore 
               FROM todaysgame WHERE SUBSTR(Date, 1, 10) = (%s)""",
            (selected_date,)
        )
        
        # If no games found for selected_date, get the most recent date available
        if not games:
            max_date_result = DatabaseManager.execute_query("SELECT MAX(Date) FROM todaysgame")
            max_date = max_date_result[0][0] if max_date_result else None
            
            if max_date:
                games = DatabaseManager.execute_query(
                    """SELECT VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore 
                       FROM todaysgame WHERE Date = (%s)""",
                    (max_date,)
                )
                return games, str(max_date.date())
            else:
                return [], selected_date
        
        return games, selected_date

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
                              VisitorTeamGoaler, HomeTeamGoaler """
                    "FROM todaysgame "
                    "WHERE ((VisitorTeam = %s AND HomeTeam = %s) OR (VisitorTeam = %s AND HomeTeam = %s)) "
                    "ORDER BY Date DESC LIMIT %s"""
                )
                params = (team1, team2, team2, team1, limit)
            else:
                # Show only current season head-to-head games
                query = (
                    """SELECT Date, VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore, 
                              VisitorTeamGoaler, HomeTeamGoaler """
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
                              VisitorTeamGoaler, HomeTeamGoaler """
                    "FROM todaysgame "
                    "WHERE VisitorTeam = %s OR HomeTeam = %s "
                    "ORDER BY Date DESC LIMIT %s"""
                )
                params = (team1, team1, limit)
            else:
                # Show only current season games
                query = (
                    """SELECT Date, VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore, 
                              VisitorTeamGoaler, HomeTeamGoaler """
                    "FROM todaysgame "
                    "WHERE (VisitorTeam = %s OR HomeTeam = %s) AND Season_ID = %s "
                    "ORDER BY Date DESC LIMIT %s"""
                )
                params = (team1, team1, current_season_id, limit)

        return DatabaseManager.execute_query(query, params)

    @staticmethod
    def format_games_list(games: List[Tuple], team1: str = None, team2: str = None) -> str:
        """Format a list of games into a readable string with proper alignment."""
        if not games:
            return "No games found."
        
        # Header with proper alignment
        result = "Date              Away                Home\n"
        result += "--------------------------------------------------\n"
        
        for game in games:
            # Unpack game data - now includes goalie information
            if len(game) >= 7:  # New format with goalie fields
                date_val, v_team, v_score, h_team, h_score, v_goalie, h_goalie = game
            else:  # Fallback to old format
                date_val, v_team, v_score, h_team, h_score = game
                v_goalie, h_goalie = None, None
            
            # Format date - extract just the date part if it's a timestamp
            if hasattr(date_val, 'strftime'):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                date_str = str(date_val)
                # If it's a string timestamp, extract just the date part
                if ' ' in date_str:
                    date_str = date_str.split(' ')[0]
            
            # Get team acronyms for display
            v_acronym = TEAM_ACRONYMS.get(v_team, v_team)
            h_acronym = TEAM_ACRONYMS.get(h_team, h_team)
            
            # Check if this was an overtime game
            is_ot, overtime_type = ScoresManager.is_overtime_game(v_goalie, h_goalie) if v_goalie and h_goalie else (False, "")
            
            # Debug output for display formatting
            if v_goalie and h_goalie:
                print(f"DEBUG: Display formatting - Game: {v_team} vs {h_team}, Overtime: {is_ot}, Type: {overtime_type}")
            
            # Format scores with OT indicator if applicable - convert to integers
            v_score_int = int(float(v_score))
            h_score_int = int(float(h_score))
            
            v_score_display = f"{v_acronym} {v_score_int}"
            h_score_display = f"{h_acronym} {h_score_int}"
            
            if is_ot and overtime_type:
                # Add (OT) or (SO) to the losing team's score
                if v_score_int > h_score_int:
                    h_score_display += f"({overtime_type})"
                else:
                    v_score_display += f"({overtime_type})"
            
            # Format with proper alignment
            result += f"{date_str:<16} {v_score_display:<20} {h_score_display}\n"
        
        # Add separator line
        result += "--------------------------------------------------\n"
        
        # Add head-to-head record if both teams are specified, or overall record if only one team
        if team1 and team2 and team2 != 'all':
            record = ScoresManager.calculate_head_to_head_record(games, team1, team2)
            result += f"Record: {record}\n"
        elif team1 and team2 == 'all':
            # Show overall record for the single team
            record = ScoresManager.calculate_team_overall_record(games, team1)
            result += f"Record: {record}\n"
        
        return result
    
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
        
        print(f"DEBUG: Looking for teams: '{team1}' -> cleaned to '{team1_clean}' and '{team2}' -> cleaned to '{team2_clean}'")
        print(f"DEBUG: First few games to see actual database team names:")
        for i, game in enumerate(games[:3]):
            if len(game) >= 5:
                print(f"DEBUG: Game {i+1}: '{game[1]}' vs '{game[3]}'")
        
        print(f"DEBUG: Total games to process: {len(games)}")
        
        for game in games:
            # Unpack game data - now includes goalie information
            if len(game) >= 7:  # New format with goalie fields
                date_val, v_team, v_score, h_team, h_score, v_goalie, h_goalie = game
            else:  # Fallback to old format
                date_val, v_team, v_score, h_team, h_score = game
                v_goalie, h_goalie = None, None
            
            v_score_int, h_score_int = int(v_score), int(h_score)
            
            # Clean the team names from the database for comparison
            v_team_clean = v_team.lower()
            h_team_clean = h_team.lower()
            
            print(f"DEBUG: Game: '{v_team}' vs '{h_team}' (scores: {v_score_int}-{h_score_int})")
            print(f"DEBUG: Comparing '{v_team_clean}' == '{team1_clean.lower()}' and '{h_team_clean}' == '{team2_clean.lower()}'")
            
            # Check if overtime game first
            is_ot, overtime_type = ScoresManager.is_overtime_game(v_goalie, h_goalie)
            
            # Determine which team is which (case-insensitive comparison)
            if v_team_clean == team1_clean.lower() and h_team_clean == team2_clean.lower():
                print(f"DEBUG: MATCH! team1 ({team1_clean}) is away, team2 ({team2_clean}) is home")
                # team1 is away, team2 is home
                if v_score_int > h_score_int:
                    # team1 wins, team2 loses
                    team1_wins += 1
                    if is_ot:
                        team2_otl += 1
                        print(f"DEBUG: team1 wins, team2 gets OTL ({overtime_type})")
                    else:
                        team2_losses += 1
                        print(f"DEBUG: team1 wins, team2 gets regular loss")
                elif v_score_int < h_score_int:
                    # team2 wins, team1 loses
                    team2_wins += 1
                    if is_ot:
                        team1_otl += 1
                        print(f"DEBUG: team2 wins, team1 gets OTL ({overtime_type})")
                    else:
                        team1_losses += 1
                        print(f"DEBUG: team2 wins, team1 gets regular loss")
                else:
                    # Tie - this shouldn't happen in modern NHL, but handle it as OTL
                    team1_otl += 1
                    team2_otl += 1
                    print(f"DEBUG: tie, both get OTL")
            elif v_team_clean == team2_clean.lower() and h_team_clean == team1_clean.lower():
                print(f"DEBUG: MATCH! team2 ({team2_clean}) is away, team1 ({team1_clean}) is home")
                # team2 is away, team1 is home
                if v_score_int > h_score_int:
                    # team2 wins, team1 loses
                    team2_wins += 1
                    if is_ot:
                        team1_otl += 1
                        print(f"DEBUG: team2 wins, team1 gets OTL ({overtime_type})")
                    else:
                        team1_losses += 1
                        print(f"DEBUG: team2 wins, team1 gets regular loss")
                elif v_score_int < h_score_int:
                    # team1 wins, team2 loses
                    team1_wins += 1
                    if is_ot:
                        team2_otl += 1
                        print(f"DEBUG: team1 wins, team2 gets OTL ({overtime_type})")
                    else:
                        team2_losses += 1
                        print(f"DEBUG: team1 wins, team2 gets regular loss")
                else:
                    # Tie - this shouldn't happen in modern NHL, but handle it as OTL
                    team1_otl += 1
                    team2_otl += 1
                    print(f"DEBUG: tie, both get OTL")
            else:
                print(f"DEBUG: NO MATCH for team1 ({team1_clean.lower()}) or team2 ({team2_clean.lower()})")
        
        print(f"DEBUG: Final record: team1 {team1_clean}: {team1_wins}-{team1_losses}-{team1_otl}, team2 {team2_clean}: {team2_wins}-{team2_losses}-{team2_otl}")
        
        # Format the record using NHL W-L-OTL format
        team1_acronym = TEAM_ACRONYMS.get(team1, team1)
        team2_acronym = TEAM_ACRONYMS.get(team2, team2)
        
        return f"{team1_acronym}: {team1_wins}-{team1_losses}-{team1_otl} vs {team2_acronym}: {team2_wins}-{team2_losses}-{team2_otl}"
    
    @staticmethod
    def calculate_team_overall_record(games: List[Tuple], team: str) -> str:
        """Calculate overall record for a single team from the given games using NHL W-L-OTL format."""
        wins = 0
        losses = 0
        otl = 0
        
        # Clean team name for comparison
        team_clean = TeamDataManager.clean_team_name(team.lower())
        
        print(f"DEBUG: Looking for team: '{team}' -> cleaned to '{team_clean}'")
        print(f"DEBUG: First few games to see actual database team names:")
        for i, game in enumerate(games[:3]):
            if len(game) >= 5:
                print(f"DEBUG: Game {i+1}: '{game[1]}' vs '{game[3]}'")
        
        for game in games:
            # Unpack game data - now includes goalie information
            if len(game) >= 7:  # New format with goalie fields
                date_val, v_team, v_score, h_team, h_score, v_goalie, h_goalie = game
            else:  # Fallback to old format
                date_val, v_team, v_score, h_team, h_score = game
                v_goalie, h_goalie = None, None
            
            v_score_int, h_score_int = int(float(v_score)), int(float(h_score))
            
            # Clean the team names from the database for comparison
            v_team_clean = v_team.lower()
            h_team_clean = h_team.lower()
            
            print(f"DEBUG: Game: '{v_team}' vs '{h_team}' (scores: {v_score_int}-{h_score_int})")
            print(f"DEBUG: Comparing '{v_team_clean}' == '{team_clean.lower()}' and '{h_team_clean}' == '{team_clean.lower()}'")
            
            # Check if this team is in the game
            if v_team_clean == team_clean.lower():
                print(f"DEBUG: MATCH! team ({team_clean}) is away")
                # Team is away
                if v_score_int > h_score_int:
                    wins += 1
                    print(f"DEBUG: team wins")
                elif v_score_int < h_score_int:
                    # Check if this was an OTL
                    if ScoresManager.is_overtime_game(v_goalie, h_goalie)[0]: # Check if it was OT
                        otl += 1
                        print(f"DEBUG: team loses in OT")
                    else:
                        losses += 1
                        print(f"DEBUG: team loses in regulation")
                else:
                    # Tie - treat as OTL
                    otl += 1
                    print(f"DEBUG: tie, team gets OTL")
            elif h_team_clean == team_clean.lower():
                print(f"DEBUG: MATCH! team ({team_clean}) is home")
                # Team is home
                if h_score_int > v_score_int:
                    wins += 1
                    print(f"DEBUG: team wins")
                elif h_score_int < v_score_int:
                    # Check if this was an OTL
                    if ScoresManager.is_overtime_game(v_goalie, h_goalie)[0]: # Check if it was OT
                        otl += 1
                        print(f"DEBUG: team loses in OT")
                    else:
                        losses += 1
                        print(f"DEBUG: team loses in regulation")
                else:
                    # Tie - treat as OTL
                    otl += 1
                    print(f"DEBUG: tie, team gets OTL")
            else:
                print(f"DEBUG: NO MATCH for team ({team_clean.lower()})")
        
        print(f"DEBUG: Final record: team {team_clean}: {wins}-{losses}-{otl}")
        
        # Format the record using NHL W-L-OTL format
        team_acronym = TEAM_ACRONYMS.get(team, team)
        return f"{team_acronym}: {wins}-{losses}-{otl}"

    @staticmethod
    def parse_goalie_minutes(goalie_data: str) -> int:
        """Parse goalie data string to extract minutes played."""
        if not goalie_data or goalie_data == "None":
            return 0
        
        try:
            print(f"DEBUG: Raw goalie data: '{goalie_data}'")
            
            # Look for pattern like "65:00 minutes" at the end of the string
            if "minutes" in goalie_data:
                # Find the last occurrence of "minutes" and extract everything before it
                minutes_index = goalie_data.rfind("minutes")
                if minutes_index > 0:
                    # Get the part before "minutes" and trim
                    before_minutes = goalie_data[:minutes_index].strip()
                    print(f"DEBUG: Before 'minutes': '{before_minutes}'")
                    
                    # Look for the last time pattern (MM:SS) in the string
                    # Split by spaces and find the last part that contains ":"
                    parts = before_minutes.split()
                    time_part = None
                    
                    # Look backwards through the parts to find the time
                    for part in reversed(parts):
                        if ":" in part and len(part.split(":")) == 2:
                            time_part = part
                            break
                    
                    if time_part:
                        print(f"DEBUG: Found time part: '{time_part}'")
                        minutes, seconds = time_part.split(":")
                        # Trim whitespace and convert
                        total_minutes = float(minutes.strip()) + float(seconds.strip()) / 60.0
                        print(f"DEBUG: Parsed goalie data '{goalie_data}' -> {total_minutes} minutes")
                        return total_minutes
                    else:
                        print(f"DEBUG: No time pattern found in parts: {parts}")
                else:
                    print(f"DEBUG: 'minutes' found but at position 0")
            else:
                print(f"DEBUG: No 'minutes' found in goalie data")
            
            return 0
        except Exception as e:
            print(f"DEBUG: Error parsing goalie data '{goalie_data}': {e}")
            return 0
    
    @staticmethod
    def is_overtime_game(visitor_goalie: str, home_goalie: str) -> tuple[bool, str]:
        """Check if a game went to overtime or shootout based on goalie minutes played.
        Returns (is_overtime, overtime_type) where overtime_type is 'OT' or 'SO'."""
        if not visitor_goalie or not home_goalie:
            print(f"DEBUG: Missing goalie data - visitor: '{visitor_goalie}', home: '{home_goalie}'")
            return False, ""
        
        v_minutes = ScoresManager.parse_goalie_minutes(visitor_goalie)
        h_minutes = ScoresManager.parse_goalie_minutes(home_goalie)
        
        print(f"DEBUG: Goalie minutes - visitor: {v_minutes}, home: {h_minutes}")
        print(f"DEBUG: Overtime threshold: 60 minutes")
        
        # Check if either goalie played more than 60 minutes
        max_minutes = max(v_minutes, h_minutes)
        if max_minutes > 60:  # Exactly 60:00 is regulation time, not overtime
            # Determine if it's a shootout (exactly 65:00) or overtime (more than 65:00)
            if abs(max_minutes - 65.0) < 0.01:  # Allow for small floating point differences
                print(f"DEBUG: Is shootout game: True (exactly 65 minutes)")
                return True, "SO"
            else:
                print(f"DEBUG: Is overtime game: True (more than 60 minutes)")
                return True, "OT"
        else:
            print(f"DEBUG: Is overtime game: False")
            return False, ""


class TradeManager:
    """Handles trade-related data operations."""
    
    @staticmethod
    def get_trades_by_player(player_name: str, limit: int = 5) -> List[Tuple]:
        """Get all trades involving a specific player, limited to specified number."""
        # Clean player name for search (handle underscores and case)
        cleaned_name = player_name.replace('_', ' ').lower()
        
        query = """
        SELECT T_ID, DateCreated, Team1, Team2, Team1List, Team2List, 
               Team1Approved, Team2Approved, CommishApproved, FutureConsiderations
        FROM transactions 
        WHERE (LOWER(Team1List) LIKE %s OR LOWER(Team2List) LIKE %s)
        ORDER BY DateCreated DESC
        LIMIT %s
        """
        
        search_pattern = f"%{cleaned_name}%"
        return DatabaseManager.execute_query(query, (search_pattern, search_pattern, limit))
    
    @staticmethod
    def get_trades_by_team(team1: str, team2: str = 'all', limit: int = 5) -> List[Tuple]:
        """Get trades involving a specific team, optionally filtered by another team, limited to specified number."""
        # Clean team names for search
        team1_clean = TeamDataManager.clean_team_name(team1.lower())
        team2_clean = TeamDataManager.clean_team_name(team2.lower()) if team2 != 'all' else 'all'
        
        # Get team ID for team1
        team1_result = DatabaseManager.execute_query("SELECT Number FROM proteam WHERE LOWER(Name) = %s", (team1_clean.lower(),))
        if not team1_result:
            return []
        
        team1_id = team1_result[0][0]
        
        if team2 == 'all':
            # Get all trades involving team1
            query = """
            SELECT T_ID, DateCreated, Team1, Team2, Team1List, Team2List, 
                   Team1Approved, Team2Approved, CommishApproved, FutureConsiderations
            FROM transactions 
            WHERE (Team1 = %s OR Team2 = %s)
            ORDER BY DateCreated DESC
            LIMIT %s
            """
            return DatabaseManager.execute_query(query, (team1_id, team1_id, limit))
        else:
            # Get team2 ID
            team2_result = DatabaseManager.execute_query("SELECT Number FROM proteam WHERE LOWER(Name) = %s", (team2_clean.lower(),))
            if not team2_result:
                return []
            
            team2_id = team2_result[0][0]
            
            # Get trades between team1 and team2
            query = """
            SELECT T_ID, DateCreated, Team1, Team2, Team1List, Team2List, 
                   Team1Approved, Team2Approved, CommishApproved, FutureConsiderations
            FROM transactions 
            WHERE ((Team1 = %s AND Team2 = %s) OR (Team1 = %s AND Team2 = %s))
            ORDER BY DateCreated DESC
            LIMIT %s
            """
            return DatabaseManager.execute_query(query, (team1_id, team2_id, team2_id, team1_id, limit))
    
    @staticmethod
    def get_team_name(team_id: int) -> str:
        """Get team name from team ID."""
        result = DatabaseManager.execute_query("SELECT Name FROM proteam WHERE Number = %s", (team_id,))
        return result[0][0] if result else f"Team {team_id}"
    
    @staticmethod
    def format_trade_history(trades: List[Tuple], player_name: str) -> str:
        """Format trade history for display."""
        if not trades:
            return f"No trades found for {player_name.title()}."
        
        result = f"Trade History for {player_name.title()}\n"
        result += "=" * 50 + "\n\n"
        
        for trade in trades:
            t_id, date_created, team1_id, team2_id, team1_list, team2_list, \
            team1_approved, team2_approved, commish_approved, future_considerations = trade
            
            # Get team names
            team1_name = TradeManager.get_team_name(team1_id)
            team2_name = TradeManager.get_team_name(team2_id)
            
            # Format date
            date_str = str(date_created).split(' ')[0] if date_created else "Unknown"
            
            # Clean HTML tags and format trade details
            team1_clean = TradeManager.clean_html_tags(team1_list)
            team2_clean = TradeManager.clean_html_tags(team2_list)
            
            result += f"**Trade #{t_id}** - {date_str}\n"
            result += f"**{team1_name}** receives:\n"
            result += f"```{team1_clean}```\n"
            result += f"**{team2_name}** receives:\n"
            result += f"```{team2_clean}```\n"
            
            if future_considerations and future_considerations != "NULL":
                future_clean = TradeManager.clean_html_tags(future_considerations)
                result += f"**Future Considerations:** {future_clean}\n"
            
            result += "-" * 30 + "\n\n"
        
        return result
    
    @staticmethod
    def clean_html_tags(text: str) -> str:
        """Clean HTML tags from text, converting <br> to line breaks except at end of line."""
        if not text:
            return ""
        
        # Convert <br> tags to line breaks, but remove trailing <br> at end of line
        cleaned = text.replace('<br>', '\n')
        
        # Remove trailing <br> tags that would create empty lines
        cleaned = cleaned.rstrip('\n')
        
        return cleaned
    
    @staticmethod
    def format_single_trade(trade: Tuple, trade_number: int) -> str:
        """Formats a single trade into a readable string."""
        t_id, date_created, team1_id, team2_id, team1_list, team2_list, \
        team1_approved, team2_approved, commish_approved, future_considerations = trade
        
        # Debug output to see what we're getting from database
        print(f"DEBUG: Trade #{t_id} - Team1 ID: {team1_id}, Team2 ID: {team2_id}")
        print(f"DEBUG: Team1List: '{team1_list}'")
        print(f"DEBUG: Team2List: '{team2_list}'")
        
        # Get team names
        team1_name = TradeManager.get_team_name(team1_id)
        team2_name = TradeManager.get_team_name(team2_id)
        
        print(f"DEBUG: Team1 Name: '{team1_name}', Team2 Name: '{team2_name}'")
        
        # Format date
        date_str = str(date_created).split(' ')[0] if date_created else "Unknown"
        
        # Clean HTML tags and format trade details
        team1_clean = TradeManager.clean_html_tags(team1_list)
        team2_clean = TradeManager.clean_html_tags(team2_list)
        
        # Determine approval status
        approval_status = ""
        if team1_approved == 'True' and team2_approved == 'True' and commish_approved == 'True':
            approval_status = "✅ **APPROVED**"
        elif team1_approved == 'True' and team2_approved == 'True':
            approval_status = "⏳ **PENDING COMMISSIONER APPROVAL**"
        else:
            pending_teams = []
            if team1_approved != 'True':
                pending_teams.append(team1_name)
            if team2_approved != 'True':
                pending_teams.append(team2_name)
            approval_status = f"⏳ **PENDING APPROVAL** ({', '.join(pending_teams)})"
        
        result = f"**Trade #{t_id}** - {date_str} - {approval_status}\n"
        result += f"**{team1_name}** receives:\n"
        result += f"```{team2_clean}```\n"
        result += f"**{team2_name}** receives:\n"
        result += f"```{team1_clean}```\n"
        
        if future_considerations and future_considerations != "NULL":
            future_clean = TradeManager.clean_html_tags(future_considerations)
            result += f"**Future Considerations:** {future_clean}\n"
        
        result += "-" * 30
        return result


class AwardsManager:
    """Handles award-related data operations."""
    
    @staticmethod
    def get_award_winners(award_name: str = None, season_id: str = None) -> List[Tuple]:
        """Get award winners for a specific award and season, or all awards for a season."""
        if season_id == "all" and award_name:
            # Get all historical winners for a specific award
            query = """
            SELECT T_ID, PlayoffMVP, TopScorer, MVP, GoalieOfTheYear, DefensemanOfTheYear, 
                   RookieOfTheYear, BestDefensiveForward, MostSportsmanlikePlayer, CoachOfTheYear, 
                   TopGoalScorer, LowestGAA, LowestPIM, GeneralManager, FarmPlayoffMVP, FarmTopScorer, 
                   FarmMVP, FarmGoalieOfTheYear, FarmDefensemanOfTheYear, FarmRookieOfTheYear, 
                   FarmBestDefensiveForward, FarmMostSportsmanlikePlayer, FarmCoachOfTheYear, 
                   FarmTopGoalScorer, FarmLowestGAA, FarmLowestPIM, Team, Season_ID
            FROM trophywinners 
            WHERE Season_ID IS NOT NULL
            ORDER BY Season_ID DESC
            """
            return DatabaseManager.execute_query(query)
        elif season_id and season_id != "all":
            # Get all awards for a specific season
            query = """
            SELECT T_ID, PlayoffMVP, TopScorer, MVP, GoalieOfTheYear, DefensemanOfTheYear, 
                   RookieOfTheYear, BestDefensiveForward, MostSportsmanlikePlayer, CoachOfTheYear, 
                   TopGoalScorer, LowestGAA, LowestPIM, GeneralManager, FarmPlayoffMVP, FarmTopScorer, 
                   FarmMVP, FarmGoalieOfTheYear, FarmDefensemanOfTheYear, FarmRookieOfTheYear, 
                   FarmBestDefensiveForward, FarmMostSportsmanlikePlayer, FarmCoachOfTheYear, 
                   FarmTopGoalScorer, FarmLowestGAA, FarmLowestPIM, Team, Season_ID
            FROM trophywinners 
            WHERE Season_ID = %s
            """
            return DatabaseManager.execute_query(query, (season_id,))
        else:
            # Get the most recent season ID if not provided
            season_result = DatabaseManager.execute_query("SELECT MAX(Season_ID) FROM trophywinners")
            season_id = season_result[0][0] if season_result else 0
            
            # Get all awards for the most recent season
            query = """
            SELECT T_ID, PlayoffMVP, TopScorer, MVP, GoalieOfTheYear, DefensemanOfTheYear, 
                   RookieOfTheYear, BestDefensiveForward, MostSportsmanlikePlayer, CoachOfTheYear, 
                   TopGoalScorer, LowestGAA, LowestPIM, GeneralManager, FarmPlayoffMVP, FarmTopScorer, 
                   FarmMVP, FarmGoalieOfTheYear, FarmDefensemanOfTheYear, FarmRookieOfTheYear, 
                   FarmBestDefensiveForward, FarmMostSportsmanlikePlayer, FarmCoachOfTheYear, 
                   FarmTopGoalScorer, FarmLowestGAA, FarmLowestPIM, Team, Season_ID
            FROM trophywinners 
            WHERE Season_ID = %s
            """
            return DatabaseManager.execute_query(query, (season_id,))
    
    @staticmethod
    def get_player_name(player_id: int) -> str:
        """Get player name from player ID."""
        if player_id == 0 or player_id is None:
            return "No Award Given"
        
        result = DatabaseManager.execute_query("SELECT Name FROM playerstats WHERE Number = %s LIMIT 1", (player_id,))
        return result[0][0] if result else f"Player #{player_id}"
    
    @staticmethod
    def get_team_name(team_id: int) -> str:
        """Get team name from team ID."""
        result = DatabaseManager.execute_query("SELECT Name FROM proteam WHERE Number = %s", (team_id,))
        return result[0][0] if result else f"Team {team_id}"
    
    @staticmethod
    def format_awards(awards: List[Tuple], award_name: str = None, season_id: str = None) -> str:
        """Format awards for display."""
        if not awards:
            if season_id == "all":
                return f"No historical data found for {award_name}."
            else:
                return f"No awards found for season {season_id}."
        
        if season_id == "all" and award_name:
            # Format historical award winners
            result = f"**Historical Winners: {award_name}**\n"
            result += "=" * 50 + "\n\n"
            
            for award in awards:
                t_id, playoff_mvp, top_scorer, mvp, goalie_of_year, defenseman_of_year, \
                rookie_of_year, best_defensive_forward, most_sportsmanlike, coach_of_year, \
                top_goal_scorer, lowest_gaa, lowest_pim, general_manager, farm_playoff_mvp, \
                farm_top_scorer, farm_mvp, farm_goalie_of_year, farm_defenseman_of_year, \
                farm_rookie_of_year, farm_best_defensive_forward, farm_most_sportsmanlike, \
                farm_coach_of_year, farm_top_goal_scorer, farm_lowest_gaa, farm_lowest_pim, \
                team, season_id = award
                
                # Get team name
                team_name = AwardsManager.get_team_name(team) if team else "Unknown Team"
                
                # Find the specific award winner
                winner_id = None
                if award_name.upper() == "MVP" and mvp:
                    winner_id = mvp
                elif award_name.upper() == "PLAYOFFMVP" and playoff_mvp:
                    winner_id = playoff_mvp
                elif award_name.upper() == "TOPSCORER" and top_scorer:
                    winner_id = top_scorer
                elif award_name.upper() == "GOALIEOFTHEYEAR" and goalie_of_year:
                    winner_id = goalie_of_year
                elif award_name.upper() == "DEFENSEMANOFTHEYEAR" and defenseman_of_year:
                    winner_id = defenseman_of_year
                elif award_name.upper() == "ROOKIEOFTHEYEAR" and rookie_of_year:
                    winner_id = rookie_of_year
                elif award_name.upper() == "BESTDEFENSIVEFORWARD" and best_defensive_forward:
                    winner_id = best_defensive_forward
                elif award_name.upper() == "MOSTSPORTSMANLIKEPLAYER" and most_sportsmanlike:
                    winner_id = most_sportsmanlike
                elif award_name.upper() == "COACHOFTHEYEAR" and coach_of_year:
                    winner_id = coach_of_year
                elif award_name.upper() == "TOPGOALSCORER" and top_goal_scorer:
                    winner_id = top_goal_scorer
                elif award_name.upper() == "LOWESTGAA" and lowest_gaa:
                    winner_id = lowest_gaa
                elif award_name.upper() == "LOWESTPIM" and lowest_pim:
                    winner_id = lowest_pim
                elif award_name.upper() == "GENERALMANAGER" and general_manager:
                    winner_id = general_manager
                
                if winner_id and winner_id != 0:
                    winner_name = AwardsManager.get_player_name(winner_id)
                    result += f"**Season {season_id}:** {winner_name} ({team_name})\n"
                
            return result
        else:
            # Format all awards for a season
            award = awards[0]  # We expect one row per season
            t_id, playoff_mvp, top_scorer, mvp, goalie_of_year, defenseman_of_year, \
            rookie_of_year, best_defensive_forward, most_sportsmanlike, coach_of_year, \
            top_goal_scorer, lowest_gaa, lowest_pim, general_manager, farm_playoff_mvp, \
            farm_top_scorer, farm_mvp, farm_goalie_of_year, farm_defenseman_of_year, \
            farm_rookie_of_year, farm_best_defensive_forward, farm_most_sportsmanlike, \
            farm_coach_of_year, farm_top_goal_scorer, farm_lowest_gaa, farm_lowest_pim, \
            team, season_id = award
            
            # Get team name
            team_name = AwardsManager.get_team_name(team) if team else "Unknown Team"
            
            result = f"**Awards for Season {season_id}**\n"
            result += f"**Team:** {team_name}\n"
            result += "=" * 50 + "\n\n"
            
            # NHL Awards
            result += "**🏆 NHL Awards:**\n"
            if playoff_mvp and playoff_mvp != 0:
                result += f"**Playoff MVP:** {AwardsManager.get_player_name(playoff_mvp)}\n"
            if mvp and mvp != 0:
                result += f"**MVP:** {AwardsManager.get_player_name(mvp)}\n"
            if top_scorer and top_scorer != 0:
                result += f"**Top Scorer:** {AwardsManager.get_player_name(top_scorer)}\n"
            if goalie_of_year and goalie_of_year != 0:
                result += f"**Goalie of the Year:** {AwardsManager.get_player_name(goalie_of_year)}\n"
            if defenseman_of_year and defenseman_of_year != 0:
                result += f"**Defenseman of the Year:** {AwardsManager.get_player_name(defenseman_of_year)}\n"
            if rookie_of_year and rookie_of_year != 0:
                result += f"**Rookie of the Year:** {AwardsManager.get_player_name(rookie_of_year)}\n"
            if best_defensive_forward and best_defensive_forward != 0:
                result += f"**Best Defensive Forward:** {AwardsManager.get_player_name(best_defensive_forward)}\n"
            if most_sportsmanlike and most_sportsmanlike != 0:
                result += f"**Most Sportsmanlike Player:** {AwardsManager.get_player_name(most_sportsmanlike)}\n"
            if coach_of_year and coach_of_year != 0:
                result += f"**Coach of the Year:** {AwardsManager.get_player_name(coach_of_year)}\n"
            if top_goal_scorer and top_goal_scorer != 0:
                result += f"**Top Goal Scorer:** {AwardsManager.get_player_name(top_goal_scorer)}\n"
            if lowest_gaa and lowest_gaa != 0:
                result += f"**Lowest GAA:** {AwardsManager.get_player_name(lowest_gaa)}\n"
            if lowest_pim and lowest_pim != 0:
                result += f"**Lowest PIM:** {AwardsManager.get_player_name(lowest_pim)}\n"
            if general_manager and general_manager != 0:
                result += f"**General Manager:** {AwardsManager.get_player_name(general_manager)}\n"
            
            result += "\n**🏆 Farm Team Awards:**\n"
            if farm_playoff_mvp and farm_playoff_mvp != 0:
                result += f"**Farm Playoff MVP:** {AwardsManager.get_player_name(farm_playoff_mvp)}\n"
            if farm_mvp and farm_mvp != 0:
                result += f"**Farm MVP:** {AwardsManager.get_player_name(farm_mvp)}\n"
            if farm_top_scorer and farm_top_scorer != 0:
                result += f"**Farm Top Scorer:** {AwardsManager.get_player_name(farm_top_scorer)}\n"
            if farm_goalie_of_year and farm_goalie_of_year != 0:
                result += f"**Farm Goalie of the Year:** {AwardsManager.get_player_name(farm_goalie_of_year)}\n"
            if farm_defenseman_of_year and farm_defenseman_of_year != 0:
                result += f"**Farm Defenseman of the Year:** {AwardsManager.get_player_name(farm_defenseman_of_year)}\n"
            if farm_rookie_of_year and farm_rookie_of_year != 0:
                result += f"**Farm Rookie of the Year:** {AwardsManager.get_player_name(farm_rookie_of_year)}\n"
            if farm_best_defensive_forward and farm_best_defensive_forward != 0:
                result += f"**Farm Best Defensive Forward:** {AwardsManager.get_player_name(farm_best_defensive_forward)}\n"
            if farm_most_sportsmanlike and farm_most_sportsmanlike != 0:
                result += f"**Farm Most Sportsmanlike Player:** {AwardsManager.get_player_name(farm_most_sportsmanlike)}\n"
            if farm_coach_of_year and farm_coach_of_year != 0:
                result += f"**Farm Coach of the Year:** {AwardsManager.get_player_name(farm_coach_of_year)}\n"
            if farm_top_goal_scorer and farm_top_goal_scorer != 0:
                result += f"**Farm Top Goal Scorer:** {AwardsManager.get_player_name(farm_top_goal_scorer)}\n"
            if farm_lowest_gaa and farm_lowest_gaa != 0:
                result += f"**Farm Lowest GAA:** {AwardsManager.get_player_name(farm_lowest_gaa)}\n"
            if farm_lowest_pim and farm_lowest_pim != 0:
                result += f"**Farm Lowest PIM:** {AwardsManager.get_player_name(farm_lowest_pim)}\n"
            
            return result


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
        
        embed = discord.Embed(title=title_score, url='http://mrfhl.com/pro_scores.php', color=0xeee657)
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


@bot.command(name='trades_by_player', help="Usage: $trades_by_player <player_name> [limit]. Examples:\n$trades_by_player Mikael_backlund\n$trades_by_player Mikael_backlund 1")
async def trades_by_player(ctx, player_name: str, limit: int = 5):
    """Display trade history for a specific player."""
    try:
        # Clamp limit to reasonable range
        limit = min(max(int(limit), 1), 50)
        
        trades = TradeManager.get_trades_by_player(player_name, limit)
        if not trades:
            await ctx.send(f"No trade history found for {player_name.title()}.")
            return
        
        # Send header message
        await ctx.send(f"**Trade History for {player_name.title()}** ({len(trades)} trades found)")
        
        # Send each trade as a separate message
        for i, trade in enumerate(trades, 1):
            trade_message = TradeManager.format_single_trade(trade, i)
            await ctx.send(trade_message)
            
    except Exception as e:
        await ctx.send(f"Error retrieving trade history: {str(e)}")


@bot.command(name='trades_by_team', help="Usage: $trades_by_team <team1> [team2|limit] [limit]. Examples:\n$trades_by_team Oilers\n$trades_by_team Oilers Canucks\n$trades_by_team Oilers 5\n$trades_by_team Oilers Canucks 5")
async def trades_by_team(ctx, team1: str, team2: str = 'all', limit: int = 5):
    """Display trade history for a specific team, optionally filtered by another team."""
    try:
        # Handle case where second argument is numeric (limit)
        if isinstance(team2, str) and team2.isdigit():
            limit = int(team2)
            team2 = 'all'
        
        # Clamp limit to reasonable range
        limit = min(max(int(limit), 1), 50)
        
        trades = TradeManager.get_trades_by_team(team1, team2, limit)
        if not trades:
            if team2 == 'all':
                await ctx.send(f"No trade history found for {team1.title()}.")
            else:
                await ctx.send(f"No trade history found between {team1.title()} and {team2.title()}.")
            return
        
        # Send header message
        if team2 == 'all':
            await ctx.send(f"**Trade History for {team1.title()}** ({len(trades)} trades found)")
        else:
            await ctx.send(f"**Trade History between {team1.title()} and {team2.title()}** ({len(trades)} trades found)")
        
        # Send each trade as a separate message
        for i, trade in enumerate(trades, 1):
            trade_message = TradeManager.format_single_trade(trade, i)
            await ctx.send(trade_message)
            
    except Exception as e:
        await ctx.send(f"Error retrieving trade history: {str(e)}")


# @bot.command(name='awards', help="Usage: $awards [award_name] [season_id]. Examples:\n$awards (current season)\n$awards 2015 (all awards for 2015)\n$awards MVP 2015 (MVP from 2015)\n$awards MVP all (all historical MVPs)\n\nAvailable Awards:\n🏆 NHL: MVP, PlayoffMVP, TopScorer, GoalieOfTheYear, DefensemanOfTheYear, RookieOfTheYear, BestDefensiveForward, MostSportsmanlikePlayer, CoachOfTheYear, TopGoalScorer, LowestGAA, LowestPIM, GeneralManager\n🏆 Farm: FarmMVP, FarmPlayoffMVP, FarmTopScorer, FarmGoalieOfTheYear, FarmDefensemanOfTheYear, FarmRookieOfTheYear, FarmBestDefensiveForward, FarmMostSportsmanlikePlayer, FarmCoachOfTheYear, FarmTopGoalScorer, FarmLowestGAA, FarmLowestPIM")
# async def awards(ctx, arg1: str = None, arg2: str = None):
#     """Display award winners for a specific season and award."""
#     try:
#         # Parse arguments
#         if arg1 is None:
#             # $awards - show current season
#             season_id = None
#             award_name = None
#         elif arg2 is None:
#             # $awards 2015 - show all awards for season 2015
#             if arg1.isdigit():
#                 season_id = arg1
#                 award_name = None
#             else:
#                 # $awards MVP - show MVP for current season
#                 award_name = arg1
#                 season_id = None
#         else:
#             # $awards MVP 2015 or $awards MVP all
#             if arg1.isdigit():
#                 # $awards 2015 MVP (old format, still supported)
#                 season_id = arg1
#                 award_name = arg2
#             else:
#                 # $awards MVP 2015 (new format)
#                 award_name = arg1
#                 season_id = arg2
#         
#         # Get award winners
#         award_winners = AwardsManager.get_award_winners(award_name, season_id)
#         
#         if not award_winners:
#             if season_id == "all":
#                 await ctx.send(f"No historical data found for {award_name}.")
#             else:
#                 await ctx.send(f"No awards found for season {season_id}.")
#             return
#         
#         # Format and display
#         awards_formatted = AwardsManager.format_awards(award_winners, award_name, season_id)
#         
#         # Check if we need to split into multiple messages due to Discord limits
#         if len(awards_formatted) > 1900:
#             await ctx.send(f"```{awards_formatted}```")
#         else:
#             if season_id == "all":
#                 title = f"Historical Winners: {award_name}"
#             elif award_name:
#                 title = f"{award_name} Winner - Season {season_id}"
#             else:
#                 title = f"Awards for Season {season_id}"
#             
#             embed = discord.Embed(title=title, color=0xeee657)
#             embed.add_field(name="Awards", value=awards_formatted, inline=False)
#             await ctx.send(embed=embed)
#             
#     except Exception as e:
#         await ctx.send(f"Error retrieving awards: {str(e)}")


# Run the bot
if __name__ == "__main__":
    print("Starting Discord bot... (press Ctrl+C to quit)")
    bot.run(TOKEN)