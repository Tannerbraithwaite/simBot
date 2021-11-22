import mysql.connector as mysql
from discord.ext import commands
import discord
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

#server IP
HOST = os.getenv('HOST')

#database name
DATABASE = os.getenv('DATABASE')

#database user
USER = os.getenv('DBUSER')

#database password
PASSWORD = os.getenv('DBPASSWORD')


teamAcronyms = {'North Stars': 'MIN', 'Ducks': 'ANA', 'Maple Leafs': 'TOR', 'Blackhawks': 'CHI', 'Savage': 'SJS', 'Jets': 'WPG', 'Blues': 'STL', 'Whalers': 'CAR', 'Predators': 'NSH', 'Kings': 'LAK', 'Avalanche': 'COL', 'Rangers': 'NYR',
                'Oilers': 'EDM', 'Islanders': 'NYI', 'Senators': 'OTT', 'Devils': 'NJD', 'Flames': 'CAL', 'Capitals': 'WSH', 'Stars': 'DAL', 'Canucks': 'VAN', 'Sabres': 'BUF', 'Lightning': 'TBL', 'Coyotes': 'ARZ',
                'Blue Jackets': 'CBJ', 'Golden Knights': 'VGK', 'Panthers': 'FLA', 'Canadiens': 'MON', 'Bruins': 'BOS', 'Flyers': 'PHI', 'Red Wings': 'DET', 'Penguins': 'PIT', 'Kraken': 'SEA'}
today = date.today()

#database_name = cursor.fetchone()
client = discord.Client()
bot = commands.Bot(command_prefix='$')

@client.event
async def on_ready():
    await print(f'{client.user} has connected to Discord!')


def replace_words(s, words):
    for k, v in words.items():
        s = s.replace(k, v)
    return s


def add_position_to_skater(listOfPlayers):
    db_connection = mysql.connect(host=HOST, user=USER, password=PASSWORD, database=DATABASE)
    cursor = db_connection.cursor(buffered=True)
    cursor.execute("select database();")
    cursor.execute("""SELECT Name, PosC, PosLW, PosRW, PosD FROM players""")
    playersByPosition = cursor.fetchall()

    for player in listOfPlayers:
        player['Position'] = []
        for positionplayer in playersByPosition:
            if player['Name'] == positionplayer[0]:
                if positionplayer[1] == 'True':
                    player['Position'].append('C')
                    player['Position'].append('F')
                if positionplayer[2] == 'True':
                    player['Position'].append('LW')
                    player['Position'].append('F')
                if positionplayer[3] == 'True':
                    player['Position'].append('RW')
                    player['Position'].append('F')
                if positionplayer[4] == 'True':
                    player['Position'].append('D')
    cursor.close()
    db_connection.close()
    return listOfPlayers


@bot.command(name='scores', help="type $scores followed by the date(ie. $scores 2020/03/29) to get the scores for a specific date")
async def scoredate(ctx, selecteddate=str(today)):
    db_connection = mysql.connect(host=HOST, user=USER, password=PASSWORD, database=DATABASE)
    cursor = db_connection.cursor(buffered=True)
    cursor.execute("select database();")
    if selecteddate != str(today):
        dateInput = (selecteddate, )
        cursor.execute("""SELECT VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore FROM todaysgame where SUBSTR(Date, 1 , 10) = (%s)""", dateInput)
        todaysGames = cursor.fetchall()
        gameDates = selecteddate
    else:
        #find current date to sort games
        cursor.execute("select MAX(Date) from todaysgame")
        selectedrow = cursor.fetchall()
        #get all games from that day
        cursor.execute("""SELECT VisitorTeam, VisitorTeamScore, HomeTeam, HomeTeamScore FROM todaysgame where Date = (%s)""", selectedrow[0])
        todaysGames = cursor.fetchall()
        gameDates = selectedrow[0][0].date()
    game_scores = ''
    for game in todaysGames:

        game_scores = game_scores + game[0] + str(int(game[1])).rjust(20 - len(game[0])) + '\n' + game[2] + str(int(game[3])).rjust(20 - len(game[2])) + '\n' + '\n'
    cursor.close()
    db_connection.close()
    #create a title
    title_score = "the scores for " + str(gameDates)
    scores_formatted = "```" + game_scores + "```"
    embed = discord.Embed(title=title_score, url='http://cchlsim.com/pro_scores.php', color=0xeee657)
    embed.add_field(name="Scores", value=scores_formatted)
    await ctx.send(embed=embed)


@bot.command(name='standings', help="type $standings followed by the division of conference(ie. $standings Pacific, $standings Western) to get the scores for a division or conference. You can view wildcard standings with $standings Western_wildcard. Default is league standings")
async def standings(ctx, divCon=None):
    db_connection = mysql.connect(host=HOST, user=USER, password=PASSWORD, database=DATABASE)
    cursor = db_connection.cursor(buffered=True)
    cursor.execute("select database();")
    teamsIdMatchingDict = {}
    cursor.execute("""SELECT Number, Name FROM proteam""")
    teamsAndIDs = cursor.fetchall()
    cursor.execute("select MAX(Season_ID) from proteamstandings")
    Season_ID = cursor.fetchall()
    teamStats = []
    for team in teamsAndIDs:
        teamsIdMatchingDict[team[0]] = team[1]
    if divCon is None:
        cursor.execute("""SELECT Number, Point, GP, W, L, OTW, OTL, SOW, SOL, GF, GA FROM proteamstandings where Season_ID = (%s)""", Season_ID[0])
        unsortedStandings = cursor.fetchall()
        for team in unsortedStandings:
            teamStats.append({'teamName': teamsIdMatchingDict[team[0]], 'points': team[1], 'GP': team[2], 'W': team[3], 'L': team[4], 'OTW': team[5], 'OTL': team[6], 'SOW': team[7], 'SOL': team[8], 'GF': team[9], 'GA': team[10]})
        sortedStandings = sorted(teamStats, key = lambda k: (-int(k['points']), int(k['GP']), int(k['W']) + int(k['OTW']), int(k['W']) + int(k['OTW']) + int(k['SOW'])))
        standings1 = '\n' + '    ' + 'Team' + 'GP'.rjust(4) + "W".rjust(5) + "L".rjust(5) + "OTL".rjust(5) + "P".rjust(5) + '\n'
        teamcount = 1
        standings2 = ''
        for team in sortedStandings:
            if teamcount <= 16:
                if teamcount < 10:
                    wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                    OTL = str(int(team['OTL'] + team['SOL']))
                    standings1 = standings1 + str(teamcount) + '.  ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                else:
                    wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                    OTL = str(int(team['OTL'] + team['SOL']))
                    standings1 = standings1 + str(teamcount) + '. ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                teamcount += 1
            else:
                wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                OTL = str(int(team['OTL'] + team['SOL']))
                standings2 = standings2 + str(teamcount) + '. ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                teamcount += 1
        formattedStandings1 = "```" + standings1 + "```"  ##Format the data for discord
        formattedStandings1 = replace_words(formattedStandings1, teamAcronyms)
        formattedStandings2 = "```" + standings2 + "```"  ##Format the data for discord
        formattedStandings2 = replace_words(formattedStandings2, teamAcronyms)
        print(formattedStandings1+'\n'+formattedStandings2,)
        embed = discord.Embed(title="League Standings", color=0xeee657)  ##Create the Embed Object to send to Discord
        embed.add_field(name="League Standings", value=formattedStandings1, inline=False)  ##Add the top 16 teams to the embed object
        embed.add_field(name="------------------------------", value=formattedStandings2, inline=False)  ##Add the rest of the teams to the embed object
    if divCon is not None:
        divCon = divCon.capitalize()
        if divCon == "Western_wildcard" or divCon == "Eastern_wildcard":
            if divCon == "Western_wildcard":
                cursor.execute("""SELECT Number FROM proteam where Division = 'Central'""")
                division1teams = cursor.fetchall()
                cursor.execute("""SELECT Number FROM proteam where Division = 'Pacific'""")
                division2teams = cursor.fetchall()
            if divCon == "Eastern_wildcard":
                cursor.execute("""SELECT Number FROM proteam where Division = 'Northeast'""")
                division1teams = cursor.fetchall()
                cursor.execute("""SELECT Number FROM proteam where Division = 'Atlantic'""")
                division2teams = cursor.fetchall()
            div1teamsnumbers = []
            div2teamsnumbers = []
            for team in division1teams:
                div1teamsnumbers.append(team[0])
            for team in division2teams:
                div2teamsnumbers.append(team[0])
            division1teamNumbers = tuple(div1teamsnumbers)
            division2teamNumbers = tuple(div2teamsnumbers)
            unsortedDiv1Standings = []
            unsortedDiv2Standings = []
            teamStats1 = []
            teamStats2 = []
            for team in division1teamNumbers:
                cursor.execute("""SELECT Number, Point, GP, W, L, OTW, OTL, SOW, SOL, GF, GA FROM proteamstandings where Season_ID = (%s) and Number = (%s)""", (Season_ID[0][0], team))
                unsortedDiv1Standings.append(cursor.fetchall())
            for team in division2teamNumbers:
                cursor.execute("""SELECT Number, Point, GP, W, L, OTW, OTL, SOW, SOL, GF, GA FROM proteamstandings where Season_ID = (%s) and Number = (%s)""", (Season_ID[0][0], team))
                unsortedDiv2Standings.append(cursor.fetchall())
            for team in unsortedDiv1Standings:
                teamStats1.append({'teamName': teamsIdMatchingDict[team[0][0]], 'points': team[0][1], 'GP': team[0][2], 'W': team[0][3], 'L': team[0][4],'OTW': team[0][5], 'OTL': team[0][6], 'SOW': team[0][7], 'SOL': team[0][8], 'GF': team[0][9], 'GA': team[0][10]})
            for team in unsortedDiv2Standings:
                teamStats2.append({'teamName': teamsIdMatchingDict[team[0][0]], 'points': team[0][1], 'GP': team[0][2], 'W': team[0][3], 'L': team[0][4],'OTW': team[0][5], 'OTL': team[0][6], 'SOW': team[0][7], 'SOL': team[0][8], 'GF': team[0][9], 'GA': team[0][10]})
            sortedStandings1 = sorted(teamStats1, key=lambda k: (-int(k['points']), int(k['GP']), int(k['W']) + int(k['OTW']), int(k['W']) + int(k['OTW']) + int(k['SOW'])))
            sortedStandings2 = sorted(teamStats2, key=lambda k: (-int(k['points']), int(k['GP']), int(k['W']) + int(k['OTW']), int(k['W']) + int(k['OTW']) + int(k['SOW'])))
            standings = '\n' + '    ' + 'Team' + 'GP'.rjust(4) + "W".rjust(5) + "L".rjust(5) + "OTL".rjust(5) + "P".rjust(5) + '\n'
            teamcount = 1
            div1leaders = sortedStandings1[:3]
            div2leaders = sortedStandings2[:3]
            wildcardteams = sortedStandings1[3:] + sortedStandings2[3:]
            wildcardteams = sorted(wildcardteams, key=lambda k: (-int(k['points']), int(k['GP']), int(k['W']) + int(k['OTW']), int(k['W']) + int(k['OTW']) + int(k['SOW'])))
            for team in div1leaders:
                wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                OTL = str(int(team['OTL'] + team['SOL']))
                standings = standings + str(teamcount) + '.  ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                teamcount += 1
            standings = standings + '-----------------------' + '\n'
            teamcount = 1
            for team in div2leaders:
                wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                OTL = str(int(team['OTL'] + team['SOL']))
                standings = standings + str(teamcount) + '.  ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                teamcount += 1
            standings = standings + '-----------------------' + '\n'
            teamcount = 1
            for team in wildcardteams:
                if teamcount == 3:
                    standings = standings + '-----------------------' + '\n'
                if teamcount >= 10:
                    wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                    OTL = str(int(team['OTL'] + team['SOL']))
                    standings = standings + str(teamcount) + '. ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                    teamcount += 1
                else:
                    wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                    OTL = str(int(team['OTL'] + team['SOL']))
                    standings = standings + str(teamcount) + '.  ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                    teamcount += 1
            formattedStandings = "```" + standings + "```"
            formattedStandings = replace_words(formattedStandings, teamAcronyms)
            print(formattedStandings)
            embed = discord.Embed(title=divCon + " Standings", color=0xeee657)
            embed.add_field(name=divCon +" Standings", value=formattedStandings, inline=False)
        else:
            if divCon == "Western":
                cursor.execute("""SELECT Number FROM proteam where Conference = 'Western'""")
                teamNumbers = cursor.fetchall()
            if divCon == "Eastern":
                cursor.execute("""SELECT Number FROM proteam where Conference = 'Eastern'""")
                teamNumbers = cursor.fetchall()
            if divCon == "Pacific":
                cursor.execute("""SELECT Number FROM proteam where Division = 'Pacific'""")
                teamNumbers = cursor.fetchall()
            if divCon == "Northeast" or divCon == "North East" or divCon == "Metro" or divCon == "Metroplitan":
                cursor.execute("""SELECT Number FROM proteam where Division = 'Northeast'""")
                teamNumbers = cursor.fetchall()
            if divCon == "Atlantic":
                cursor.execute("""SELECT Number FROM proteam where Division = 'Atlantic'""")
                teamNumbers = cursor.fetchall()
            if divCon == "Central":
                cursor.execute("""SELECT Number FROM proteam where Division = 'Central'""")
                teamNumbers = cursor.fetchall()
            else:
                await ctx.send("We could not find that division, please check spelling(Atlantic, Central, Northeast/Metro, Pacific, Western, Eastern, Western_wildcard, Eastern_wildcard)")
            teams = []
            for team in teamNumbers:
                teams.append(team[0])
            teamNumbers = tuple(teams)
            unsortedStandings = []
            for team in teamNumbers:
                cursor.execute("""SELECT Number, Point, GP, W, L, OTW, OTL, SOW, SOL, GF, GA FROM proteamstandings where Season_ID = (%s) and Number = (%s)""", (Season_ID[0][0], team))
                unsortedStandings.append(cursor.fetchall())
            for team in unsortedStandings:
                teamStats.append({'teamName': teamsIdMatchingDict[team[0][0]], 'points': team[0][1], 'GP': team[0][2], 'W': team[0][3], 'L': team[0][4],'OTW': team[0][5], 'OTL': team[0][6], 'SOW': team[0][7], 'SOL': team[0][8], 'GF': team[0][9], 'GA': team[0][10]})
            sortedStandings = sorted(teamStats, key=lambda k: (-int(k['points']), int(k['GP']), int(k['W']) + int(k['OTW']), int(k['W']) + int(k['OTW']) + int(k['SOW'])))
            standings = '\n' + '    ' + 'Team' + 'GP'.rjust(4) + "W".rjust(5) + "L".rjust(5) + "OTL".rjust(5) + "P".rjust(5) + '\n'
            teamcount = 1
            if divCon == "Pacific" or divCon == "Central" or divCon == "Northeast" or divCon == "North East" or divCon == "Metro" or divCon == "Metropolitan" or divCon == 'Atlantic':
                for team in sortedStandings:
                    if teamcount == 4:
                        wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                        OTL = str(int(team['OTL'] + team['SOL']))
                        standings = standings + '----------------------' + '\n' + str(teamcount) + '.  ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                    else:
                        wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                        OTL = str(int(team['OTL'] + team['SOL']))
                        standings = standings + str(teamcount) + '.  ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                    teamcount += 1
            if divCon == "Eastern" or divCon == "Western":
                for team in sortedStandings:
                    if teamcount <= 9:
                        wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                        OTL = str(int(team['OTL'] + team['SOL']))
                        standings = standings + str(teamcount) + '.  ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                    else:
                        wins = str(int(team['W'] + team['OTW'] + team['SOW']))
                        OTL = str(int(team['OTL'] + team['SOL']))
                        standings = standings + str(teamcount) + '. ' + team['teamName'] + f"{str(int(team['GP']))}".rjust(5) + wins.rjust(5) + f"{str(int(team['L']))}".rjust(5) + OTL.rjust(5) + f"{str(int(team['points']))}".rjust(5) + '\n'
                    teamcount += 1
            formattedStandings = "```" + standings + "```"  ##Format the data for discord
            formattedStandings = replace_words(formattedStandings, teamAcronyms)
            print(formattedStandings)
            embed = discord.Embed(title=divCon + " Standings", color=0xeee657)  ##Create the Embed Object to send to Discord
            embed.add_field(name=divCon +" Standings", value=formattedStandings, inline=False)  ##Add the top 16 teams to the embed object
    cursor.close()
    db_connection.close()
    await ctx.send(embed=embed)  ##Send the object to discord


@bot.command(name='scoring_leaders',help="type $scoring_leaders followed by the team you want to filter by, then the position, then the stat for example $scoring_leaders Flames D Goals will give you the flames Defence Goal leaders, $scoring_leaders all F Hits will give you the forward hit leaders for the entire league. positions are C, RW, LW, D. available stats are Points, Goals, Assists, Hits, Pims, +/-, Shots, ShotsBlocked, and GWG. If a team has a space in it's name it requires an underscore ie. $scoring_leaders Golden_Knights")
async def scoring_leaders(ctx, teamselected='all', position='all', stat='Points'):
    db_connection = mysql.connect(host=HOST, user=USER, password=PASSWORD, database=DATABASE)
    cursor = db_connection.cursor(buffered=True)
    cursor.execute("select database();")
    teamsIdMatchingDict = {}
    cursor.execute("""SELECT Number, Name FROM proteam""")
    teamsAndIDs = cursor.fetchall()
    cursor.execute("select MAX(Season_ID) from proteamstandings")
    Season_ID = cursor.fetchall()
    for team in teamsAndIDs:
        teamsIdMatchingDict[team[0]] = team[1]
    cleanedPlayersStats = []
    tradedPlayersList = []
    mergedplayerList = []
    cursor.execute(
        """SELECT Name, Team, ProGP, ProShots, ProG, ProA, ProPoint, ProPlusMinus, ProPim, ProShotsBlock, ProHits, ProGW, Active from playerstats where Season_ID = (%s) and proGP > 0""",
        Season_ID[0])
    allPlayerstats = cursor.fetchall()
    for player in allPlayerstats:
        cleanedPlayersStats.append(
            {'Name': player[0], 'Team': teamsIdMatchingDict[int(player[1])], 'GP': player[2], 'Shots': player[3],
             'Goals': player[4], 'Assists': player[5], 'Points': player[6], '+/-': player[7], 'Pims': player[8],
             'ShotsBlocked': player[9], 'Hits': player[10], 'GWG': player[11], 'currentTeam': player[12]})
    for player in cleanedPlayersStats:
        if player['currentTeam'] == 'False':
            tradedPlayersList.append(player)
    for checkplayer in cleanedPlayersStats:
        for comparedplayer in tradedPlayersList:
            if checkplayer['Name'] == comparedplayer['Name']:
                combinedplayer = {'Name': checkplayer['Name'], 'Team': checkplayer['Team'],
                                  'GP': int(checkplayer['GP'] + comparedplayer['GP']),
                                  'Shots': int(checkplayer['Shots'] + comparedplayer['Shots']),
                                  'Goals': int(checkplayer['Goals'] + comparedplayer['Goals']),
                                  'Assists': int(checkplayer['Assists'] + comparedplayer['Assists']),
                                  'Points': int(checkplayer['Points'] + comparedplayer['Points']),
                                  '+/-': int(checkplayer['+/-'] + comparedplayer['+/-']),
                                  'Pims': int(checkplayer['Pims'] + comparedplayer['Pims']),
                                  'ShotsBlocked': int(checkplayer['ShotsBlocked'] + comparedplayer['ShotsBlocked']),
                                  'Hits': int(checkplayer['Hits'] + comparedplayer['Hits']),
                                  'GWG': int(checkplayer['GWG'] + comparedplayer['GWG']),
                                  'currentTeam': checkplayer['currentTeam'],
                                  'P/G': round(checkplayer['Points']/checkplayer['GP'], 2)}
            else:
                combinedplayer = checkplayer
                combinedplayer['P/G'] = round(checkplayer['Points']/checkplayer['GP'], 2)
            mergedplayerList.append(combinedplayer)
    for player in mergedplayerList:
        if player['currentTeam'] == 'False':
            mergedplayerList.remove(player)
    mergedplayerList = add_position_to_skater(mergedplayerList)
    if teamselected == 'Red_Wings':
        teamselected = 'Red Wings'
    if teamselected == 'Blue_Jackets':
        teamselected = 'Blue Jackets'
    if teamselected == "North_Stars":
        teamselected = "North Stars"
    if teamselected == "Maple_Leafs":
        teamselected = 'Maple Leafs'
    if teamselected == 'Golden_Knights':
        teamselected = 'Golden Knights'

    if teamselected == 'all':
        pass
    else:
        mergedplayerList = [x for x in mergedplayerList if x['Team'] == teamselected]
    if position == 'all':
        pass
    else:
        mergedplayerList = [x for x in mergedplayerList if position in x['Position']]
    if stat == 'P/G':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['P/G']))
        checkstat = 'P/G'
    if stat == 'Goals':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['Goals']))
        checkstat = 'Goals'
    if stat == 'Assists':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['Assists']))
        checkstat = 'Assists'
    if stat == 'Points':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['Points']))
        checkstat = 'Points'
    if stat == 'Shots':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['Shots']))
        checkstat = 'Shots'
    if stat == '+/-':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['+/-']))
        checkstat = '+/-'
    if stat == 'Pims':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['Pims']))
        checkstat = 'Pims'
    if stat == 'Shots_blocked':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['ShotsBlocked']))
        checkstat = 'ShotsBlocked'
    if stat == 'GWG':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['GWG']))
        checkstat = 'GWG'
    if stat == 'Hits':
        sortedplayerList = sorted(mergedplayerList, key=lambda k: (-k['Hits']))
        checkstat = 'Hits'

    if len(sortedplayerList) < 10:
        amountToDisplay = len(sortedplayerList)
    else:
        amountToDisplay = 10
    sortedplayerList = sortedplayerList[:amountToDisplay]
    player_leaders = 'Team' + 'Name'.rjust(7) + checkstat.rjust(22) + '\n'
    for player in sortedplayerList:
        player_leaders = player_leaders + teamAcronyms[player['Team']] + '    ' + player['Name'] + str(
            player[checkstat]).rjust(26 - len(str(player['Name']))) + '\n'
    cursor.close()
    db_connection.close()
    # create a title
    title_score = stat + " Leaders"
    playersFormatted = "```" + player_leaders + "```"
    embed = discord.Embed(title=title_score, color=0xeee657)
    embed.add_field(name="Players", value=playersFormatted)
    await ctx.send(embed=embed)

@bot.command(name='goalie_leaders',help="type $goalie_leaders followed by the stat you wish to see(ie. $goalie_leaders GAA, SV%, W, GP, SO, L, S) to get the top ten goalies by a certain stat. you can add a second argument to get more goalies, and a third argument to filter by games played. The default stat is save percentage, the default games played is 0, and the default amount of goalies is ten. For example $goalie_leaders will give you the top ten goalies in save percentage out of all goalies. $goalie_leaders GAA 15 10 will give you the top 15 goalies in GAA who have played more than 10 games")
async def goalie_leaders(ctx, stat='SV%', amountWanted=10, GamesWanted = 0):
    db_connection = mysql.connect(host=HOST, user=USER, password=PASSWORD, database=DATABASE)
    cursor = db_connection.cursor(buffered=True)
    cursor.execute("select database();")
    teamsIdMatchingDict = {}
    cursor.execute("""SELECT Number, Name FROM proteam""")
    teamsAndIDs = cursor.fetchall()
    cursor.execute("select MAX(Season_ID) from proteamstandings")
    Season_ID = cursor.fetchall()
    cleanedGoalieStats = []
    tradedGoaliesList = []
    mergedgoalieList = []
    for team in teamsAndIDs:
        teamsIdMatchingDict[team[0]] = team[1]
    cursor.execute("""SELECT Name, Team, ProGP, ProMinPlay, ProW, ProL, ProOTL, ProShutouts, ProGA, ProSA, Active from goaliestats where Season_ID = (%s) and proGP > 0""", Season_ID[0])
    allGoaliestats = cursor.fetchall()
    for goalie in allGoaliestats:
        cleanedGoalieStats.append({'Name': goalie[0], 'Team': teamsIdMatchingDict[int(goalie[1])], 'GP': goalie[2], 'Minutes': goalie[3], 'Wins': goalie[4], 'Losses': goalie[5], 'OTL': goalie[6], 'SO': goalie[7], 'GA': goalie[8], 'Saves': int(goalie[9]) - int(goalie[8]), 'SA': int(goalie[9]), 'currentTeam': goalie[10]})
    for goalie in cleanedGoalieStats:
        if goalie['currentTeam'] == 'False':
            tradedGoaliesList.append(goalie)
    for checkgoalie in cleanedGoalieStats:
        for comparedgoalie in tradedGoaliesList:
            if checkgoalie['Name'] == comparedgoalie['Name']:
                combinedGoalie = {'Name': checkgoalie['Name'], 'Team': checkgoalie['Team'], 'GP': checkgoalie['GP'] + comparedgoalie['GP'], 'Minutes': checkgoalie['Minutes'] + comparedgoalie['Minutes'], 'Wins': checkgoalie['Wins'] + comparedgoalie['Wins'], 'Losses': checkgoalie['Losses'] + comparedgoalie['Losses'], 'OTL': checkgoalie['OTL'] + comparedgoalie['OTL'], 'SO': checkgoalie['SO'] + comparedgoalie['SO'], 'GA': checkgoalie['GA'] + comparedgoalie['GA'], 'Saves': checkgoalie['Saves'] + comparedgoalie['Saves'], 'SA': checkgoalie['SA'] + comparedgoalie['SA'], 'currentTeam': checkgoalie['currentTeam']}
            else:
                combinedGoalie = checkgoalie
        mergedgoalieList.append(combinedGoalie)
    for goalie in mergedgoalieList:
        if goalie['currentTeam'] == 'False':
            mergedgoalieList.remove(goalie)
    for goalie in mergedgoalieList:
        goalie['GP'] = int(goalie['GP'])
        goalie['SVP'] = round(goalie['Saves']/(goalie['Saves'] + goalie['GA']), 3)
        goalie['GAA'] = round(goalie['GA']/(goalie['Minutes']/3600), 2)

    if stat == 'GAA':
        sortedGoalieList = sorted(mergedgoalieList, key=lambda k: (k['GAA']))
        checkstat = 'GAA'
    if stat == 'SV%':
        sortedGoalieList = sorted(mergedgoalieList, key=lambda k: (-k['SVP']))
        checkstat = 'SVP'
    if stat == 'W':
        sortedGoalieList = sorted(mergedgoalieList, key=lambda k: (-k['Wins']))
        checkstat = 'Wins'
    if stat == 'GP':
        sortedGoalieList = sorted(mergedgoalieList, key=lambda k: (-k['GP']))
        checkstat = 'GP'
    if stat == 'SO':
        sortedGoalieList = sorted(mergedgoalieList, key=lambda k: (-k['SO']))
        checkstat = 'SO'
    if stat == 'L':
        sortedGoalieList = sorted(mergedgoalieList, key=lambda k: (-k['Losses']))
        checkstat = 'Losses'
    if stat == 'S':
        sortedGoalieList = sorted(mergedgoalieList, key=lambda k: (-k['Saves']))
        checkstat = 'Saves'
    if len(sortedGoalieList) < amountWanted:
        amountWanted = len(sortedGoalieList)
    finalList = [x for x in sortedGoalieList if x['GP'] >= GamesWanted][:int(amountWanted)]
    goalie_leaders = 'Team' + 'goalie'.rjust(10) + stat.rjust(16) + '\n'
    for goalie in finalList:
        goalie_leaders = goalie_leaders + teamAcronyms[goalie['Team']] + '     ' + goalie['Name'] + str(goalie[checkstat]).rjust(22 - len(str(goalie['Name']))) + '\n'
    cursor.close()
    db_connection.close()
    #create a title
    title_score = "Goalie Leaders for " + stat
    goaliesFormatted = "```" + goalie_leaders + "```"
    embed = discord.Embed(title=title_score, color=0xeee657)
    embed.add_field(name="Goalies", value=goaliesFormatted)
    await ctx.send(embed=embed)





bot.run(TOKEN)
