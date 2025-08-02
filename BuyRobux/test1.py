import requests


def get_user_id(username: str) -> int | None:
    url = "https://users.roblox.com/v1/usernames/users"
    resp = requests.post(url, json={"usernames": [username]})
    if resp.status_code != 200:
        print("Ошибка получения userId:", resp.status_code, resp.text)
        return None
    data = resp.json().get("data", [])
    if not data:
        print("Пользователь не найден")
        return None
    return data[0]["id"]


def get_user_games(user_id: int, limit=50):
    url = f"https://games.roblox.com/v2/users/{user_id}/games"
    params = {"sortOrder": "Asc", "limit": limit}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print("Ошибка получения игр:", resp.status_code, resp.text)
        return []
    return resp.json().get("data", [])


def print_user_places_by_username(username: str):
    uid = get_user_id(username)
    if not uid:
        return
    print(f"[✔] userId для {username}: {uid}")
    games = get_user_games(uid)
    if not games:
        print("Игры этого пользователя не найдены или приватны")
        return

    print(f"\n🕹 Игры пользователя {username}:")
    for game in games:
        name = game.get("name", "Без имени")
        root = game.get("rootPlaceId")
        uni = game.get("rootPlaceId")  # UniverseId можно получить в другом API
        visits = game.get("visits", "—")
        playing = game.get("playing", "—")
        print(f"- {name} | Place ID: {root} | Visits: {visits} | Now Playing: {playing}")
    print()


if __name__ == "__main__":
    username = input("Введите ник Roblox: ")
    print_user_places_by_username(username)
