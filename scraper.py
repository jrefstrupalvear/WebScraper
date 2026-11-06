#!/usr/bin/env python3

import json
import re
import requests
import sys
import time
import unicodedata

from concurrent.futures import ThreadPoolExecutor

# Constants

LEAGUE_URL = 'https://www.fotmob.com/leagues/87/matches/laliga?season=2025-2026'
MATCH_URL  = 'https://www.fotmob.com/match/'
MIN_GAMES  = 10
TOP_LIMIT  = 10
NEXT_DATA  = r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'

# Functions

def usage(status: int=0) -> None:
    print(f'''Usage: scraper [-t TEAM -w WORKERS]
    -t TEAM     LaLiga team to look up (default: barcelona)
    -w WORKERS  Number of concurrent downloads (default: 4)
''', file=sys.stderr)
    sys.exit(status)

def fetch_props(url: str) -> dict:
    ''' Download a page and return the JSON embedded in its HTML. '''
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    found = re.search(NEXT_DATA, response.text, re.DOTALL)
    page  = json.loads(found.group(1))
    return page['props']['pageProps']

def strip_accents(text: str) -> str:
    ''' Lowercase and remove accents, so atletico finds Atlético. '''
    letters = unicodedata.normalize('NFKD', text)
    kept    = filter(lambda letter: not unicodedata.combining(letter), letters)
    return ''.join(kept).lower()

def get_teams(games: list[dict]) -> dict:
    ''' Return every team in the league as {team ID: team name}. '''
    home_teams = list(map(lambda game: game['home'], games))
    away_teams = list(map(lambda game: game['away'], games))
    return {str(team['id']): team['name'] for team in home_teams + away_teams}

def find_teams(query: str, teams: dict) -> list[tuple]:
    ''' Return the (team ID, team name) pairs that match the search. '''
    return list(filter(lambda team: strip_accents(query) in strip_accents(team[1]), teams.items()))

def is_team_game(game: dict, team_id: str) -> bool:
    ''' Return whether a game is finished and includes the team. '''
    teams = (str(game['home']['id']), str(game['away']['id']))
    return team_id in teams and game['status'].get('finished', False)

def get_rating(player: dict):
    ''' Find a player's rating, which players under 10 minutes do not have. '''
    for group in player.get('stats') or []:
        stats = group.get('stats') or {}
        if 'FotMob rating' in stats:
            return stats['FotMob rating']['stat'].get('value')
    return None

def fetch_ratings(match_id: str, team_id: str) -> list[dict]:
    ''' Return the ratings of the team's players in one game. '''
    props   = fetch_props(MATCH_URL + match_id)
    players = props['content']['playerStats'].values()

    team_players = filter(lambda player: str(player.get('teamId')) == team_id, players)
    rated        = filter(lambda player: get_rating(player) is not None, team_players)
    return list(map(lambda player: {
        'id':     str(player['id']),
        'name':   player['name'],
        'rating': get_rating(player),
    }, rated))

def summarize_player(player_id: str, ratings: list[dict]) -> dict:
    ''' Combine one player's ratings into a summary. '''
    games  = list(filter(lambda rating: rating['id'] == player_id, ratings))
    scores = list(map(lambda rating: rating['rating'], games))

    return {
        'name':    games[0]['name'],
        'games':   len(games),
        'average': sum(scores) / len(scores),
    }

def print_table(team_name: str, players: list[dict]) -> None:
    print(f'\n{team_name}: highest average ({MIN_GAMES}+ games)')
    print(f'{"Player":<24}{"Avg rating":>12}{"Games":>7}')

    for player in players[:TOP_LIMIT]:
        name    = player['name']
        average = player['average']
        games   = player['games']
        print(f'{name:<24}{average:>12.2f}{games:>7}')

# Main Execution

def main(arguments: list[str]=sys.argv[1:]) -> None:
    ''' Looks up a LaLiga team and displays its best rated players. '''
    # Parse command line arguments
    team    = 'barcelona'
    workers = 4
    stack   = arguments[::-1]

    while stack:
        arg = stack.pop()
        if arg == '-h':
            usage(0)
        elif arg == '-t' and stack:
            team = stack.pop()
        elif arg == '-w' and stack and stack[-1].isnumeric() and int(stack[-1]) > 0:
            workers = int(stack.pop())
        else:
            usage(1)

    # Look up the team
    props   = fetch_props(LEAGUE_URL)
    games   = props['fixtures']['allMatches']
    matches = find_teams(team, get_teams(games))

    if not matches:
        print(f'No LaLiga team found for {team}', file=sys.stderr)
        sys.exit(1)

    if len(matches) > 1:
        names = ', '.join(map(lambda match: match[1], matches))
        print(f'{team} matches more than one team: {names}', file=sys.stderr)
        sys.exit(1)

    team_id, team_name = matches[0]

    # Download the team's games
    team_games = filter(lambda game: is_team_game(game, team_id), games)
    match_ids  = list(map(lambda game: str(game['id']), team_games))

    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(lambda match_id: fetch_ratings(match_id, team_id), match_ids)
        ratings = [rating for result in results for rating in result]
    elapsed = time.perf_counter() - start_time

    print(f'{len(match_ids)} games in {elapsed:.1f}s with {workers} worker(s)')

    # Display the best players
    player_ids = set(map(lambda rating: rating['id'], ratings))
    players    = map(lambda player_id: summarize_player(player_id, ratings), player_ids)
    eligible   = filter(lambda player: player['games'] >= MIN_GAMES, players)
    by_average = sorted(eligible, key=lambda player: player['average'], reverse=True)

    print_table(team_name, by_average)

if __name__ == '__main__':
    main()
