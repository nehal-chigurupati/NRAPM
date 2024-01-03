import pandas as pd
import numpy as np
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
from pbpstats.client import Client
import pbpstats

"""
Need to retool this - instead of surrounding players, surround all games this season. 
"""

class Preprocessing:
    def find_consecutive_indices(input_list):
        if not input_list:
            return []

        result = []
        start = 0
        for i in range(1, len(input_list)):
            if input_list[i] != input_list[start]:
                result.append([start, i])
                start = i
        
        result.append([start, len(input_list)-1])
        return result
    
    def get_player_id(player_name):
        return [player for player in players.get_players() if player["full_name"] == player_name][0]['id']

    def get_all_player_games(player_id, season):
        return playergamelog.PlayerGameLog(player_id=player_id, season=season).get_data_frames()[0]['Game_ID'].tolist()

    def get_play_by_play_data(game_id):
        settings = {
        "Possessions": {"source": "web", "data_provider": "stats_nba"},
        }
        pbp_client = Client(settings)

        game_data = pbp_client.Game(game_id)

        return game_data.possessions
    
    def get_lineup(possession_data):
        #Accepts possession.items
        lineup_ids = possession_data.possession_stats[0]["lineup_id"].split("-")
        opp_lineup_ids = possession_data.possession_stats[0]["opponent_lineup_id"].split("-")
        return lineup_ids + opp_lineup_ids

    def get_player_team_id(player_id, possession_data):
        possession_data = possession_data.items
        lineup = Preprocessing.get_lineup(possession_data[0])
        
        if player_id in lineup[0:5]:
            return possession_data[0].possession_stats[0]["team_id"]
        else:
            return possession_data[0].possession_stats[0]["opponent_team_id"]
        

    def get_score_difference(player_id, pbp_data, start_index, end_index):
        #not inclusive of end_index possession
        #Accepts possessions object
        filtered_possessions = pbp_data.items[start_index:end_index+1]

        if len(filtered_possessions) == 0:
            return 0
        
        if filtered_possessions[0].offense_team_id == Preprocessing.get_player_team_id(player_id, pbp_data):
            start_margin = filtered_possessions[0].start_score_margin
        else:
            start_margin = (-1)*filtered_possessions[0].start_score_margin
        
        if filtered_possessions[-1].offense_team_id == Preprocessing.get_player_team_id(player_id, pbp_data):
            end_margin = filtered_possessions[-1].start_score_margin
        else:
            end_margin = (-1)*filtered_possessions[-1].start_score_margin

        return end_margin - start_margin
    
    def identify_stints(player_id, pbp_data):
        #pass possession
        #Get list of lineups every possession
        possession_data = pbp_data.items
        lineups = []
        for p in possession_data:
            try: 
                lineup = Preprocessing.get_lineup(p)
            except:
                lineup = lineups[-1]
            lineups.append(lineup)
        
        stints = Preprocessing.find_consecutive_indices(lineups)

        return stints
    
    def get_plus_minus_numbers(player_id, stints, pbp_data):
        margins = []
        for stint in stints:
            margins.append(Preprocessing.get_score_difference(player_id, pbp_data, stint[0], stint[1]))
        
        return margins
    
    def get_stint_lineups(player_id, stints, pbp_data):
        lineups = []
        pbp_data = pbp_data.items
        for p in pbp_data:
            try: 
                lineup = Preprocessing.get_lineup(p)
            except:
                lineup = lineups[-1]
            lineups.append(lineup)
        
        filtered_lineups = []
        for stint in stints:
            full_lineup = Preprocessing.get_lineup(pbp_data[stint[0]])
            print(full_lineup)
            if str(player_id) in full_lineup[0:5]:
                print("here")
                filtered_lineups.append(full_lineup[0:5])
            else:
                filtered_lineups.append(full_lineup[5:])
            print(filtered_lineups[-1])
        return filtered_lineups

class Formatting:
    def merge_lists(input_lists):
        out = []
        for i in input_lists:
            out = out + i
        
        return out
    

    def create_feature_matrix(flattened_stints, flattened_lineups):
        #Unique players
        #Lineups should be an array of arrays of size 5
        print(Formatting.merge_lists(flattened_lineups))
        players = np.unique(Formatting.merge_lists(flattened_lineups))
        feature_matrix = [[None]*len(players)]*len(flattened_stints)

        for i in range(len(flattened_stints)):
            for j in range(len(players)):
                if players[j] in flattened_lineups[i]:
                    feature_matrix[i][j] = 1
                else:
                    feature_matrix[i][j] = 0
        
        return feature_matrix

player_id = Preprocessing.get_player_id("LeBron James")
games = Preprocessing.get_all_player_games(player_id, season="2023-24")
pbp = Preprocessing.get_play_by_play_data(games[0])
stints = Preprocessing.identify_stints(player_id, pbp)
plus_minus = Preprocessing.get_plus_minus_numbers(player_id, stints, pbp)
lineups = Preprocessing.get_stint_lineups(player_id, stints, pbp)

#flattened_lineups = Formatting.merge_lists(lineups)
#flattened_stints = Formatting.merge_lists(stints)
print(lineups)
#print(Formatting.create_feature_matrix(stints, lineups))

    


        