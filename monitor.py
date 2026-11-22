import os

import re

import json

import requests

from bs4 import BeautifulSoup

BASE_URL = "https://www.cineq.co.kr"

PLAN_IDS = {

    "10:55": "1117312",

    "13:05": "1117313",

    "15:15": "1117317",

    "17:25": "1117318",

    "19:35": "1117316",

}

def get_seats(plan_id):

    url = f"{BASE_URL}/Popup/SeatChoiceSeatMap"

    response = requests.post(

        url,

        data={"screenPlanId": plan_id},

        timeout=20

    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    seats = {}

    for seat in soup.select("input.choose-seat"):

        seat_id = seat.get("id")

        if not seat_id:

            continue

        classes = seat.get("class", [])

        disabled = "disabled" in classes or seat.has_attr("disabled")

        seats[seat_id] = not disabled

    return seats

def send_telegram(message):

    token = os.environ["TELEGRAM_BOT_TOKEN"]

    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    requests.post(

        f"https://api.telegram.org/bot{token}/sendMessage",

        data={"chat_id": chat_id, "text": message},

        timeout=20

    ).raise_for_status()

def main():

    state_file = "seat_state.json"

    if os.path.exists(state_file):

        with open(state_file, "r", encoding="utf-8") as f:

            previous = json.load(f)

    else:

        previous = {}

    current = {}

    alerts = []

    for time, plan_id in PLAN_IDS.items():

        seats = get_seats(plan_id)

        current[plan_id] = seats

        old_seats = previous.get(plan_id)

        if old_seats is not None:

            newly_available = [

                seat for seat, available in seats.items()

                if available and not old_seats.get(seat, False)

            ]

            if newly_available:

                alerts.append(

                    f"🎬 치이카와 취소석 발생!\n"

                    f"회차: {time}\n"

                    f"좌석: {', '.join(newly_available)}"

                )

    with open(state_file, "w", encoding="utf-8") as f:

        json.dump(current, f, ensure_ascii=False, indent=2)

    for alert in alerts:

        send_telegram(alert)

if __name__ == "__main__":

    main()
