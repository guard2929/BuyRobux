import requests

def get_universe_id(place_id: int) -> int | None:
    url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
    try:
        r = requests.get(url)
        r.raise_for_status()
        universe_id = r.json().get("universeId")
        if universe_id:
            print(f"[✔] Universe ID для place {place_id}: {universe_id}")
            return universe_id
        else:
            print(f"[✘] Universe ID не найден для place {place_id}")
            return None
    except requests.RequestException as e:
        print(f"[✘] Ошибка при запросе universeId: {e}")
        return None

def get_gamepasses(universe_id: int):
    url = f"https://games.roblox.com/v1/games/{universe_id}/game-passes?limit=100"
    headers = {
        "User-Agent": "Roblox/WinInet",
        "Accept": "application/json"
    }
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            print("⛔ У этого Universe нет Game Pass'ов.")
            return
        print("\n🎮 Game Pass'ы:")
        for gp in data:
            name = gp.get('name', 'Без названия')
            gp_id = gp.get('id')
            price = gp.get('price', 'Не указана')
            print(f"📛 {name} — ID: {gp_id} — Цена: {price} R$")
    except requests.RequestException as e:
        print(f"[✘] Ошибка при получении Game Pass'ов: {e}")

def main():
    place_id = 7506854335  # Твой placeId из ссылки
    universe_id = get_universe_id(place_id)
    if universe_id:
        get_gamepasses(universe_id)

if __name__ == "__main__":
    main()
