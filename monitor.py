

import os

import json

import requests

from bs4 import BeautifulSoup

BASE_URL = "https://www.cineq.co.kr"

STATE_FILE = "seat_state.json"

SHOWTIMES = [

    {"hall": "SUITE 7관", "time": "10:55~12:41", "id": "1117312", "expected": 30},

    {"hall": "SUITE 7관", "time": "13:05~14:51", "id": "1117313", "expected": 30},

    {"hall": "SUITE 7관", "time": "15:15~17:01", "id": "1117317", "expected": 30},

    {"hall": "SUITE 7관", "time": "17:25~19:11", "id": "1117318", "expected": 30},

    {"hall": "SUITE 7관", "time": "19:35~21:21", "id": "1117316", "expected": 30},

    {"hall": "RESERVE 5관", "time": "10:00~11:46", "id": "1117300", "expected": 69},

    {"hall": "RESERVE 5관", "time": "12:10~13:56", "id": "1117301", "expected": 69},

    {"hall": "RESERVE 5관", "time": "14:20~16:06", "id": "1117302", "expected": 69},

    {"hall": "RESERVE 5관", "time": "16:30~18:16", "id": "1117303", "expected": 69},

    {"hall": "RESERVE 5관", "time": "21:15~23:01", "id": "1117305", "expected": 69},

]

def get_seats(session, plan_id, expected):

    url = f"{BASE_URL}/Popup/SeatChoiceSeatMap"

    response = session.post(

        url,

        data={"screenPlanId": plan_id},

        timeout=30

    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    seat_elements = soup.select("input.choose-seat")

    if len(seat_elements) != expected:

        raise RuntimeError(

            f"{plan_id}: 좌석 수 오류 "

            f"(예상 {expected}, 확인 {len(seat_elements)})"

        )

    seats = {}

    for seat in seat_elements:

        seat_id = seat.get("id")

        if not seat_id or seat_id in seats:

            raise RuntimeError(f"{plan_id}: 좌석 ID 오류")

        classes = seat.get("class", [])

        disabled = (

            "disabled" in classes

            or seat.has_attr("disabled")

        )

        seats[seat_id] = not disabled

    return seats

def send_telegram(message):

    token = os.environ["TELEGRAM_BOT_TOKEN"]

    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    response = requests.post(

        f"https://api.telegram.org/bot{token}/sendMessage",

        data={"chat_id": chat_id, "text": message},

        timeout=20

    )

    response.raise_for_status()

    if not response.json().get("ok"):

        raise RuntimeError("텔레그램 전송 실패")

def main():

    session = requests.Session()

    session.headers.update({

        "User-Agent": (

            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 "

            "like Mac OS X) AppleWebKit/605.1.15 "

            "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

        ),

        "Referer": "https://www.cineq.co.kr/",

        "Origin": "https://www.cineq.co.kr"

    })

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r", encoding="utf-8") as f:

            previous = json.load(f)

    else:

        previous = {}

    current = {}

    alerts = []

    for show in SHOWTIMES:

        plan_id = show["id"]

        seats = get_seats(session, plan_id, show["expected"])

        current[plan_id] = seats

        old_seats = previous.get(plan_id)

        if old_seats is not None:

            newly_available = [

                seat_id

                for seat_id, available in seats.items()

                if available and not old_seats.get(seat_id, False)

            ]

            if newly_available:

                alerts.append(

                    "🎬 치이카와 취소석 발생!\n"

                    f"상영관: {show['hall']}\n"

                    f"시간: {show['time']}\n"

                    f"좌석: {', '.join(newly_available)}"

                )

    for alert in alerts:

        send_telegram(alert)

    with open(STATE_FILE, "w", encoding="utf-8") as f:

        json.dump(current, f, ensure_ascii=False, indent=2)

    print(f"감시 완료: {len(current)}개 회차")

    print(f"새 취소석 알림: {len(alerts)}건")

if __name__ == "__main__":

    main()
