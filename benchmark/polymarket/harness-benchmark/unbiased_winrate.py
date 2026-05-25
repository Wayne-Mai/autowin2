"""
Layer 4-lite: unbiased win-rate via CLOB resolution data.

For each exemplar wallet:
  1. Pull full /activity history (TRADEs + REDEEMs)
  2. Group BUY trades by conditionId, sum net YES/NO position per market
  3. Determine "which side they bet on" per market (the side with net positive shares)
  4. Query CLOB /markets/{condition_id} for each unique market → winner field
  5. Compute unbiased win_rate = #(bet_side == winner_side) / #resolved markets they participated in
  6. Also compute realized PnL per market using winner data:
       win  → (1 - avg_buy_price) * shares_held  (positive)
       lose → -avg_buy_price * shares_held       (negative)

Compares unbiased_win_rate to the biased one computed in Layer 2.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from collections import defaultdict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ACT_URL = "https://data-api.polymarket.com/activity"
CLOB_URL = "https://clob.polymarket.com/markets/{cid}"
DB_PATH = "/Users/gaga/harness-benchmark/data/polypaper.sqlite"
PAGE_SIZE = 500
SLEEP_ACTIVITY = 0.25
SLEEP_CLOB = 0.15

EXEMPLARS = [
    "0xe3726a1b9c6ba2f06585d1c9e01d00afaedaeb38",
    "0x8e9eedf20dfa70956d49f608a205e402d9df38e4",
    "0x63d43bbb87f85af03b8f2f9e2fad7b54334fa2f1",
]


def http_get_json(url, params=None, retries=3, timeout=20):
    full = url + ("?" + urlencode(params) if params else "")
    for attempt in range(retries):
        try:
            req = Request(full, headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urlopen(req, timeout=timeout).read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.0 + attempt)


def pull_activity(wallet):
    out = []
    cursor = None
    seen = set()
    for _ in range(200):
        params = {"user": wallet, "limit": PAGE_SIZE}
        if cursor is not None:
            params["end"] = cursor
        batch = http_get_json(ACT_URL, params)
        if not batch:
            break
        new_count = 0
        emin = None
        for a in batch:
            k = (a.get("timestamp"), a.get("transactionHash"), a.get("asset"), a.get("type"))
            if k in seen:
                continue
            seen.add(k)
            out.append(a)
            new_count += 1
            ts = a.get("timestamp")
            if ts is not None and (emin is None or ts < emin):
                emin = ts
        if new_count == 0 or emin is None:
            break
        cursor = emin
        if len(batch) < PAGE_SIZE:
            break
        time.sleep(SLEEP_ACTIVITY)
    return out


def per_market_bets(acts):
    """For each conditionId, compute net BUY shares per outcome.
    Returns {cid: {outcome: net_shares, ..., 'avg_buy_price_by_outcome': {...}}}.
    """
    # We track: total spent USDC + total shares acquired, per (cid, outcome)
    state = defaultdict(lambda: defaultdict(lambda: {"shares": 0.0, "usdc_spent": 0.0}))
    for ev in acts:
        if ev.get("type") != "TRADE":
            continue
        cid = ev.get("conditionId")
        outcome = ev.get("outcome")
        if not cid or not outcome:
            continue
        size = float(ev.get("size") or 0)
        price = float(ev.get("price") or 0)
        side = ev.get("side")
        if side == "BUY":
            state[cid][outcome]["shares"] += size
            state[cid][outcome]["usdc_spent"] += size * price
        elif side == "SELL":
            # Reduce position (rough; doesn't fix avg price perfectly)
            state[cid][outcome]["shares"] -= size
            state[cid][outcome]["usdc_spent"] -= size * price
    result = {}
    for cid, outs in state.items():
        # Outcome with the larger net long share count = primary bet direction
        net = {o: v["shares"] for o, v in outs.items()}
        primary = max(net.items(), key=lambda kv: kv[1])[0] if net else None
        result[cid] = {
            "primary_outcome": primary,
            "outcomes": {o: dict(v) for o, v in outs.items()},
            "primary_shares": net.get(primary, 0) if primary else 0,
        }
    return result


def fetch_market_winner(cid):
    """Returns (resolved: bool, winner_outcome: Optional[str])"""
    try:
        d = http_get_json(CLOB_URL.format(cid=cid))
    except Exception as e:
        return False, None, str(e)
    tokens = d.get("tokens") or []
    closed = d.get("closed", False)
    winner = None
    for t in tokens:
        if t.get("winner"):
            winner = t.get("outcome")
            break
    return closed, winner, None


def main():
    conn = sqlite3.connect(DB_PATH)
    for col in ("unbiased_win_rate REAL", "n_markets_resolved_real INTEGER",
                "n_markets_bet INTEGER", "unbiased_realized_pnl REAL",
                "winrate_bias_delta REAL"):
        try:
            conn.execute(f"ALTER TABLE candidate_metrics ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass

    print(f"{'wallet':45s} {'n_mkts':>7s} {'n_res':>6s} {'biased':>7s} {'unbiased':>9s} {'delta':>7s} {'realized_pnl_$':>15s}")
    print("-" * 110)
    for w in EXEMPLARS:
        acts = pull_activity(w)
        bets = per_market_bets(acts)
        n_mkts = len(bets)
        if n_mkts == 0:
            print(f"{w}  (no markets)")
            continue

        # Fetch winner for each unique conditionId
        wins = 0
        losses = 0
        unresolved = 0
        realized_pnl = 0.0
        for i, (cid, b) in enumerate(bets.items()):
            closed, winner, err = fetch_market_winner(cid)
            time.sleep(SLEEP_CLOB)
            if err or not closed or not winner:
                unresolved += 1
                continue
            primary = b["primary_outcome"]
            if primary == winner:
                wins += 1
                # Realized PnL on winning side: shares × (1 - avg_buy_price)
                d = b["outcomes"][primary]
                shares = d["shares"]
                if shares > 0:
                    avg_p = d["usdc_spent"] / shares
                    realized_pnl += shares * (1 - avg_p)
            else:
                losses += 1
                # Realized PnL on losing side: -avg_buy_price * shares (tokens went to $0)
                if primary in b["outcomes"]:
                    d = b["outcomes"][primary]
                    realized_pnl -= d["usdc_spent"]
            if (i + 1) % 50 == 0:
                resolved_so_far = wins + losses
                rate = wins / resolved_so_far if resolved_so_far else 0
                print(f"  ...{w[:14]}  progress {i+1}/{n_mkts}  resolved {resolved_so_far}  unbiased_win_rate so far={rate:.2%}")

        n_resolved = wins + losses
        unbiased = (wins / n_resolved) if n_resolved else 0
        biased = conn.execute(
            "SELECT win_rate FROM candidate_metrics WHERE wallet=?", (w,)
        ).fetchone()
        biased = biased[0] if biased else None
        delta = (biased - unbiased) if biased is not None else None

        conn.execute("""UPDATE candidate_metrics SET
            unbiased_win_rate=?, n_markets_resolved_real=?, n_markets_bet=?,
            unbiased_realized_pnl=?, winrate_bias_delta=? WHERE wallet=?""",
            (unbiased, n_resolved, n_mkts, realized_pnl, delta, w))
        conn.commit()

        print(f"{w} {n_mkts:>7d} {n_resolved:>6d} "
              f"{(biased or 0)*100:>6.1f}% {unbiased*100:>8.1f}% "
              f"{(delta or 0)*100:>+6.1f}% {realized_pnl/1e3:>13.1f}k")


if __name__ == "__main__":
    main()
