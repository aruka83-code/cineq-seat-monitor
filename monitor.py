

import os

import json

import requests

from bs4 import BeautifulSoup

BASE_URL = "https://www.cineq.co.kr"

STATE_FILE = "seat_state.json"

SHOWTIMES = [

    # SUITE 7관 - 30석

    {"hall": "SUITE 7관", "time": "10:55~12:41", "id": "1117312", "expected": 30},

    {"hall": "SUITE 7관", "time": "13:05~14:51", "id": "1117313", "expected": 30},

    {"hall": "SUITE 7관", "time": "15:15~17:01", "id": "1117317", "expected": 30},

    {"hall": "SUITE 7관", "time": "17:25~19:11", "id": "1117318", "expected": 30},

    {"hall": "SUITE 7관", "time": "19:35~21:21", "id": "1117316", "expected": 30},

    # RESERVE 5관 - 69석

    {"hall": "RESERVE 5관", "time": "10:00~11:46", "id": "1117300", "expected": 69},

    {"hall": "RESERVE 5관", "time": "12:10~13:56", "id": "1117301", "expected": 69},

    {"hall": "RESERVE 5관", "time": "14:20~16:06", "id": "1117302", "expected": 69},

    {"hall": "RESERVE 5관", "time": "16:30~18:16", "id": "1117303", "expected": 69},

    {"hall": "RESERVE 5관", "time": "21:15~23:01", "id": "1117305", "expected": 69},

]

def get_seats(session, plan_id, expected):

    response = session.post(

        f"{BASE_URL}/Popup/SeatChoiceSeatMap",

        data={"screenPlanId": plan_id},

        timeout=30

    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    elements = soup.select("input.choose-seat")

    if len(elements) != expected:

        raise RuntimeError(

            f"{plan_id}: 예상 {expected}석, 실제 {len(elements)}석"

        )

    seats = {}

    for seat in elements:

        seat_id = seat.get("id")

        if not seat_id or seat_id in seats:

            raise RuntimeError(f"{plan_id}: 좌석 ID 오류")

        unavailable = (

            "disabled" in seat.get("class", [])

            or seat.has_attr("disabled")

        )

        seats[seat_id] = not unavailable

    return seats

def send_telegram(message):

    token = os.environ["TELEGRAM_BOT_TOKEN"]

    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    response = requests.post(

        f"https://api.telegram.org/bot{token}/sendMessage",

        data={

            "chat_id": chat_id,

            "text": message

        },

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

            "(KHTML, like Gecko) Version/17.0 "

            "Mobile/15E148 Safari/604.1"

        ),

        "Referer": "https://www.cineq.co.kr/",

        "Origin": "https://www.cineq.co.kr"

    })

    # 홈페이지 접속으로 세션 쿠키 확보

    home = session.get(BASE_URL, timeout=30)

    home.raise_for_status()

    previous = {}

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r", encoding="utf-8") as f:

            previous = json.load(f)

    current = {}

    alerts = []

    for show in SHOWTIMES:

        plan_id = show["id"]

        seats = get_seats(

            session,

            plan_id,

            show["expected"]

        )

        current[plan_id] = seats

        old_seats = previous.get(plan_id)

        # 첫 실행은 기준값만 저장하고 알림하지 않음

        if old_seats is None:

            continue

        # 매진 -> 예매 가능으로 바뀐 좌석만 감지

        opened = [

            seat_id

            for seat_id, available in seats.items()

            if available and not old_seats.get(seat_id, False)

        ]

        if opened:

            alerts.append(

                "🎬 치이카와 취소석 발생!\n"

                f"상영관: {show['hall']}\n"

                f"시간: {show['time']}\n"

                f"좌석: {', '.join(opened)}"

            )

    # 알림 전송

    for alert in alerts:

        send_telegram(alert)

    # 모든 회차 조회가 성공한 뒤 상태 저장

    with open(STATE_FILE, "w", encoding="utf-8") as f:

        json.dump(

            current,

            f,

            ensure_ascii=False,

            indent=2

        )

    print(f"감시 완료: {len(current)}개 회차")

    print(f"감시 좌석: {sum(len(v) for v in current.values())}석")

    print(f"신규 취소석 알림: {len(alerts)}건")

if __name__ == "__main__":

    main()
