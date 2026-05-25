import json
from pathlib import Path

from polypaper.models import Quote, TraderTrade


FIXTURE = Path(__file__).parent / "fixtures" / "small_replay.json"


def load_small_fixture():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    trades = [TraderTrade.from_api(row) for row in data["trades"]]
    quotes = [Quote.from_dict(row) for row in data["quotes"]]
    return trades, quotes

