import requests
import time
import datetime

from tl_info import tlInfo

# TODO:
# -display stats of the winner?
# -display information about TL games which cause [Demote] and [Promote]
# -sometimes if games_played_change > 1, it messes up for some reason (says 2nd set was upset for 2nd player even though 1st player was higher ranked)
# -add countdown until next activity log update

# How the dictionaries are organized:
# username --> rank, gamesplayed

# Debug that prints all keys and values in a user dictionary
def print_current_top_players_info(top_players_dict):
    for key in top_players_dict:
        print(f"name: {key}, info: {top_players_dict[key]}")

# Fetches recent Tetra League history for a specific user and returns a
# json object if successful
def fetch_recent_tl_data(username):
    response = requests.get(f"https://ch.tetr.io/api/users/{username}/records/league/recent")

    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch data")
        return None

# Populates a list with tlInfo objects, which contain information needed for output
# Note: We use replayid because it doesn't change depending on the user. The ID of the set is user
# specific, and will be different depending on which user we are looking at the set from.
def recent_tl_game_results(tl_data_json, number_of_games):
    res = []

    for i in range(number_of_games):
        res.append(tlInfo(tl_data_json['data']['entries'][i]['results']['leaderboard'][0]['username'], # Player one username
                            tl_data_json['data']['entries'][i]['results']['leaderboard'][0]['wins'], # Player one win count
                            tl_data_json['data']['entries'][i]['results']['leaderboard'][1]['username'], # Player two username
                            tl_data_json['data']['entries'][i]['results']['leaderboard'][1]['wins'], # Player two wincount
                            tl_data_json['data']['entries'][i]['replayid'])) # Unique identifier of the set to avoid redundancy in output
    
    return res

# Takes json object returned by API and creates a dictionary which maps
# from the username of a player to their rank and amount of games played
def create_top_players_dict(top_players):
    res = {}

    for i, player in enumerate(top_players['data']['entries']):
        res[player['username']] = [i + 1, player['league']['gamesplayed']]
    return res

# Fetches information about the current top 50 players in Tetra League, and returns a
# json object if successful
def fetch_current_leaderboard():
    response = requests.get("https://ch.tetr.io/api/users/by/league?limit=50")

    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch data")
        return None

# Compares old and new data to determine activity in the specified rank range
def document_changes(cur_top_players_dict, new_top_players_dict):
    res = []
    unique_ids = []

    for key in cur_top_players_dict:
        if key in new_top_players_dict: # If player is still in rank range
            rank_change = cur_top_players_dict[key][0] - new_top_players_dict[key][0]
            games_played_change = new_top_players_dict[key][1] - cur_top_players_dict[key][1]

            if games_played_change != 0:
                tl_data_json = fetch_recent_tl_data(key)
                tl_results = recent_tl_game_results(tl_data_json, games_played_change)

                for tl_game in tl_results:
                    if tl_game.replay_id not in unique_ids:
                        if tl_game.player_one_name == key:
                            rank = cur_top_players_dict[tl_game.player_one_name][0]
                            res.append(f"[Normal] {tl_game.player_one_name} (#{rank}) beat {tl_game.player_two_name} with a score of {tl_game.player_one_score}-{tl_game.player_two_score}. They have gone up {rank_change} rank(s).")
                        else: # Upset
                            rank = cur_top_players_dict[tl_game.player_two_name][0]
                            res.append(f"[Upset] {tl_game.player_two_name} (#{rank}) lost to {tl_game.player_one_name} with a score of {tl_game.player_two_score}-{tl_game.player_one_score}. They have lost {-(rank_change)} rank(s).")
                        unique_ids.append(tl_game.replay_id)

        elif key not in new_top_players_dict: # If player fell out of rank range recently
            res.append(f"[Demotion] {key} fell out of the specified rank range.")

    for key in new_top_players_dict: # If player got into range range recently
        if key not in cur_top_players_dict:
            res.append(f"[Promotion] {key} just got into the specified rank range.")

    return res

# Returns current time in AM/PM format
def get_current_time():
    return datetime.datetime.now().strftime("%B %d, %Y %I:%M %p")

# Prints 75 hyphens to seperate different sections of text
def print_seperator():
    print(f"{'-'*75}")

# Prints welcome message
def print_welcome():
    print_seperator()
    print(f"""
    Welcome to the Tetra league top player activity log! 
    
    Some things to note:
    1. This log updates every 10 minutes. The current date and time is:
        {get_current_time()}.
        The first activity log will appear 10 minutes from now.
    2. All shown ranks in the log are what the user's rank was
        BEFORE the event occured.
    3. Tags:
        a. [Normal] - A player beat an opponent with a lower rank
            than them.
        b. [Upset] - A player lost to an opponent with a lower rank
            than them.
        c. [Promotion] - A player recently entered the specified rank
            range.
        d. [Demotion] - A player recently fell out of the specified
            rank range.
    4. To reduce API calls, I wouldn't set the specified rank range to
        more than 100. (50 is the default)

    Thanks! c:
    """)
    print_seperator()

def main_loop(cur_top_players_dict):
    while True:
        # Wait 10 minutes before calling API again
        time.sleep(600)

        print(f"Update at {get_current_time()}.")

        new_top_players_json = fetch_current_leaderboard()

        if new_top_players_json is not None:
            new_top_players_dict = create_top_players_dict(new_top_players_json)

            changelog = document_changes(cur_top_players_dict, new_top_players_dict)
            if changelog:
                for change in changelog:
                    print(change)
            else:
                print("No reported changes in the specified rank range.")

            print_seperator()

            cur_top_players_dict = new_top_players_dict
        else:
            print("Failed to fetch new leaderboard data. :SadCat:")
            return None

print_welcome()

# Initialize what the specified rank range looks like
top_players_json = fetch_current_leaderboard()

if top_players_json is not None:
    top_players_dict = create_top_players_dict(top_players_json)
    main_loop(top_players_dict)
else:
    print("Failed to fetch initial leaderboard data. :SadCat:")
