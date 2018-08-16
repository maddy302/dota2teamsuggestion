import dota2api
import requests
import time
import json
import sqlite3
import logging
from threading import Thread 


api_key = 'CB3762621E46727A6F9FC9B72F6A9DE5'
database = 'dota2data'


def match_history():
    count_history = 10
    while(count_history>=0):
        do_match_history()
        time.sleep(60)
        print('Inside match_history')
        count_history = count_history - 1

def match_details():
    count_matches = 10
    while(count_matches>=0):
        do_match_details()
        time.sleep(60)
        print('Inside match_details')
        count_matches = count_matches - 1
        
def do_match_history(lobby_types=[0, 2, 5, 6, 7], skill=3, tournament_games_only=False):
    start_match_id = 4015357757
    print('inside do_match_history')
    matches = 0 
    while True:
        tries = 0
        while tries < 3:
            tries+=1
            try:
                result = api.get_match_history(skill = skill, min_players = 10, tournament_games_only="1" if tournament_games_only else "0", 
                                               matches_requested=100, start_at_match_id=start_at_match_id,)
                break
            except(requests.exceptions.ConnectionError, dota2api.src.exceptions.APIError, dota2api.src.exceptions.APITimeoutError):
                logging.warning("Api or timeout error in MatchHistory on try {}.".format(tries))
                time.sleep(30)
                continue
        if tries==3:
            return
        if result["results_remaining"] == 0:
            break
        start_at_match_id = result["matches"][-1]["match_id"] - 1
        for match in result["matches"]:
            if len(match["players"]) == 10 and match["lobby_type"] in lobby_types:
                add_match_to_db(match)
                matches += 1
    print("Added", matches, "matches.")
    
def do_match_details():
    print('Inside do_match_details')
    connection = sqlite3.connect(database, timeout=10)
    matches = connection.execute("SELECT match_id FROM matches WHERE radiant_win IS NULL").fetchall()
    connection.close()
    for (match_id,) in matches:
        try:
            result = api.get_match_details(match_id=match_id)
        except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError, dota2api.src.exceptions.APIError, dota2api.src.exceptions.APITimeoutError):
            logging.warning("Api or timeout error in MatchDetails on matchid {}.".format(match_id))
            time.sleep(30)
            continue
        print("Added details for {}.".format(result["match_id"]))
        update_match_in_db(result)
        time.sleep(1)
    
def add_match_to_db():
    print('Inside add_match_to_db')
    radiant_heros = list()
    dire_heros = list()
    assert(len(match["players"])==10)
    for p in match["players"]:
        slot = p["players_slot"]
        if slot< 128:
            radiant_heroes.append(p["hero_id"])
        else:
            dire_heroes.append(p["hero_id"])
    assert(len(radiant_heroes) == 5)
    assert(len(dire_heroes) == 5)
    # Skip matches where a player didnt pick a hero
    if 0 in radiant_heroes or 0 in dire_heroes:
        logging.info("Skipping {} because of 0 hero.".format(match["match_id"]))
        return
    connection = sqlite3.connect(database, timeout=10)
    connection.execute("INSERT OR IGNORE INTO matches values (?,?,?,?,?,?,?,?,?,?,?,?,?,null,null,null,null)",
                       (match["match_id"], match["start_time"], match["lobby_type"]) + tuple(radiant_heroes) + tuple(dire_heroes))
    connection.commit()
    connection.close()

def update_match_in_db():
    print('Inside update_match_in_db')
    has_leavers = False
    for p in match["players"]:
        if p["leaver_status"] in [2,3,4,5,6]: 
            has_leavers = True
        connection = sqlite3.connect(database, timeout = 10)
        connection.execute("UPDATE OR IGNORE matches SET game_mode=?, has_leaver=?, duration=?, radiant_win=? WHERE match_id=?", (match["game_mode"], has_leavers, match["duration"], match["radiant_win"], match["match_id"]))
        connection.commit()
        connection.close()
        

api = dota2api.Initialise(api_key,raw_mode=True)
match_history_thread = Thread(target=match_history)
match_history_thread.daemon = True
match_details_thread = Thread(target=match_details)
match_details_thread.daemon = True
match_history_thread.start()
match_details_thread.start()
print("Starting MatchHistory and MatchDetails threads.")
# This is needed (instead of joining the threads) to respond to crl-c
while True:
    time.sleep(1)
    