

import os

import json

import requests

from bs4 import BeautifulSoup

BASE_URL = "https://www.cineq.co.kr"

SEAT_URL = BASE_URL + "/Popup/SeatChoiceSeatMap"

STATE_FILE = "seat_state.json"

SHOWTIMES = [

    {"id": "1117312", "hall": "SUITE 7관", "time": "10:55", "count": 30},

    {"id": "1117313", "hall": "SUITE 7관", "time": "13:05", "count": 30},

    {"id": "1117317", "hall": "SUITE 7관", "time": "15:15", "count": 30},

    {"id": "1117318", "hall": "SUITE 7관", "time": "17:25", "count": 30},

    {"id": "1117316", "hall": "SUITE 7관", "time": "19:35", "count": 30},

    {"id": "1117300", "hall": "RESERVE 5관", "time": "10:00", "count": 69},

    {"id": "1117301", "hall": "RESERVE 5관", "time": "12:10", "count": 69},

    {"id": "1117302", "hall": "RESERVE 5관", "time": "14:20", "count": 69},

    {"id": "1117303", "hall": "RESERVE 5관", "time": "16:30", "count": 69},

    {"id": "1117305", "hall": "RESERVE 5관", "time": "21:15", "count": 69},

]

def load_state():

    if not os.path.exists(STATE_FILE):

        return {}

    try:

        with open(STATE_FILE, "r", encoding="utf-8") as f:

            data = json.load(f)

            return data if isinstance(data, dict) else {}

    except (json.JSONDecodeError, OSError):

        return {}

def get_available_seats(session, showtime):

    response = session.post(

        SEAT_URL,

        data={"screenPlanId": showtime["id"]},

        timeout=30

    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    seats = soup.select("input.choose-seat")

    if not seats:

        raise RuntimeError(

            f"{showtime['hall']} {showtime['time']}: "

            "좌석 정보를 찾지 못했습니다."

        )

    if len(seats) != showtime["count"]:

        raise RuntimeError(

            f"{showtime['hall']} {showtime['time']}: "

            f"예상 좌석 {showtime['count']}개, "

            f"실제 확인 {len(seats)}개. 상태 저장을 중단합니다."

        )

    available = set()

    for seat in seats:

        seat_id = seat.get("id") or seat.get("value")

        if not seat_id:

            continue

        classes = seat.get("class", [])

        unavailable = (

            "disabled" in classes

            or seat.has_attr("disabled")

        )

        if not unavailable:

            available.add(seat_id)

    return available

def send_telegram(message):

    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:

        raise RuntimeError("텔레그램 환경변수가 설정되지 않았습니다.")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(

        url,

        data={

            "chat_id": chat_id,

            "text": message

        },

        timeout=30

    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):

        raise RuntimeError(f"텔레그램 전송 실패: {result}")

def main():

    session = requests.Session()

    session.headers.update({

        "User-Agent": (

            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

        ),

        "Referer": BASE_URL + "/",

        "Origin": BASE_URL,

        "X-Requested-With": "XMLHttpRequest"

    })

    homepage = session.get(BASE_URL, timeout=30)

    homepage.raise_for_status()

    previous_state = load_state()

    current_state = {}

    alerts = []

    for showtime in SHOWTIMES:

        available = get_available_seats(session, showtime)

        key = showtime["id"]

        old_seats = previous_state.get(key)

        # 최초 확인은 기준 좌석 상태만 저장하고 알림하지 않음

        if isinstance(old_seats, list):

            newly_available = available - set(old_seats)

            if newly_available:

                seat_text = ", ".join(sorted(newly_available))

                alerts.append(

                    "🎬 치이카와 신규 취소 좌석!\n\n"

                    f"극장: 씨네Q 신도림\n"

                    f"상영관: {showtime['hall']}\n"

                    f"시간: {showtime['time']}\n"

                    f"좌석: {seat_text}"

                )

        current_state[key] = sorted(available)

        print(

            f"{showtime['hall']} {showtime['time']}: "

            f"예약 가능 {len(available)}석"

        )

    # 모든 회차 조회가 성공한 경우에만 상태 저장

    with open(STATE_FILE, "w", encoding="utf-8") as f:

        json.dump(

            current_state,

            f,

            ensure_ascii=False,

            indent=2

        )

    for alert in alerts:

        send_telegram(alert)

    print("좌석 감시 완료")

if __name__ == "__main__":

    main()
