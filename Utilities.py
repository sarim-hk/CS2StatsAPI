import requests

def get_steam_summaries(steam_ids, steam_api_key):
    try:
        all_summaries = {}
        batched_ids = [steam_ids[i:i + 100] for i in range(0, len(steam_ids), 100)] # Steam API allows max 100 IDS/req

        for batch in batched_ids:
            ids_str = ",".join(batch)
            url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={steam_api_key}&steamids={ids_str}"
            
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if "response" in data and "players" in data["response"]:
                    for player in data["response"]["players"]:
                        all_summaries[player["steamid"]] = player
            else:
                print(f"Failed to fetch Steam summaries: {response.status_code}")

        return all_summaries
    
    except requests.RequestException as e:
        return {"error": "Failed to fetch Steam summaries."}
