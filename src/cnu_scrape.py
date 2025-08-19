import os
import re
import time
import csv
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Season index pages look like:
# https://static.cnusports.com/custompages/mbball/Stats/2012-2013/teamstat.htm
BASE_SEASON_URL_TMPL = "https://static.cnusports.com/custompages/mbball/Stats/{season}/teamstat.htm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CNU-DS-Project/1.0)"
}

# ---------- helpers for season page ----------

def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def parse_game_result_rows(html: str, season_url: str):
    """
    Find 'Box score' links on a season page and extract (date, location, result, box_url).
    Returns list of tuples: (date_text, location_text, result_text, box_url)
    """
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True).lower() == "box score":
            row = a.find_parent("tr")
            if not row:
                continue
            # PyCharm sometimes warns on get_text(strip=...), so do strip() separately.
            cells = []
            for c in row.find_all(["td", "th"]):
                txt = c.get_text(" ").strip()
                cells.append(txt)
            if len(cells) >= 3:
                date_text = cells[0]
                location_text = cells[1] if len(cells) > 1 else ""
                result_text = cells[2] if len(cells) > 2 else ""
                box_href = a.get("href", "")
                box_url = urljoin(season_url, box_href)
                out.append((date_text, location_text, result_text, box_url))
    return out

def clean_date(date_text: str) -> str:
    """Convert mm/dd/yy or mm/dd/yyyy -> YYYY-MM-DD"""
    date_text = date_text.strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(date_text, fmt)
            if fmt == "%m/%d/%y" and dt.year < 1990:
                dt = dt.replace(year=dt.year + 2000)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_text  # fallback

# ---------- box page parsing (text-only, robust for CNU pages) ----------

SCORE_BY_PERIODS_RE = re.compile(
    r"Score by Periods\s+1st\s+2nd(?:\s+OT\d*)*\s+Total\s+([^\n]+)\n([^\n]+)",
    re.IGNORECASE
)
TEAM_HEADER_RE = re.compile(r"^(VISITORS|HOME TEAM):\s*(.*)$", re.MULTILINE)
TOTALS_LINE_PATTERN = re.compile(r"^\s*Totals\.\.+\s+(.*)$", re.IGNORECASE)

def _parse_totals_line(line: str):
    """
    Parse: Totals........   26-58   7-18  25-35  10 32 42  17  84 14  9  4  6 200
    Order:
      FG-FGA, 3PT-3PTA, FT-FTA, OFF, DEF, TOT, PF, TP, A, TO, BLK, S, MIN
    Returns dict with fgm,fga,tpm,tpa,ftm,fta,orb,drb,trb,to
    """
    tokens = line.split()
    if len(tokens) < 13:
        return None

    def split_pair(tok):
        if "-" in tok:
            a, b = tok.split("-", 1)
            try:
                return int(a), int(b)
            except Exception:
                return None, None
        try:
            return int(tok), None
        except Exception:
            return None, None

    # First three are shot pairs
    fgm, fga = split_pair(tokens[0])
    tpm, tpa = split_pair(tokens[1])
    ftm, fta = split_pair(tokens[2])

    def to_int(tok):
        try:
            return int(tok)
        except Exception:
            return None

    # Next 10 single integers: OFF DEF TOT PF TP A TO BLK S MIN
    rest = [to_int(tok) for tok in tokens[3:3 + 10]]
    if len(rest) < 10:
        return None
    off, de, tot, pf, tp, a, tov, blk, s, mins = rest[:10]

    return {
        "fgm": fgm, "fga": fga,
        "tpm": tpm, "tpa": tpa,
        "ftm": ftm, "fta": fta,
        "orb": off, "drb": de, "trb": tot,
        "to": tov
    }

def _extract_totals_from_block(text_block: str):
    """Find a 'Totals....' line in the block and parse it."""
    for raw in text_block.splitlines():
        m = TOTALS_LINE_PATTERN.match(raw)
        if m:
            return _parse_totals_line(m.group(1))
    return None

def parse_box_page(html: str):
    """
    Parse a single box score page into:
      - team names (away/home)
      - first-half points (away/home)
      - totals dicts (away/home) with fgm,fga,orb,drb,trb,to (plus shots)
      - final points (away/home)
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    # Team names (strip trailing records like "22-5")
    names = {}
    for label, rest in TEAM_HEADER_RE.findall(text):
        tokens = rest.split()
        while tokens and re.match(r"^\d+-\d+$", tokens[-1]):
            tokens.pop()
        names[label] = " ".join(tokens).strip(" #.")

    # Score by Periods (away line then home line)
    away_first = home_first = away_pts = home_pts = None
    m = SCORE_BY_PERIODS_RE.search(text)
    if m:
        row1, row2 = m.group(1), m.group(2)
        ints1 = [int(x) for x in re.findall(r"\d+", row1)]
        ints2 = [int(x) for x in re.findall(r"\d+", row2)]
        if ints1:
            away_first, away_pts = ints1[0], ints1[-1]
        if ints2:
            home_first, home_pts = ints2[0], ints2[-1]

    # Split into VISITORS and HOME TEAM blocks
    v_start = text.find("VISITORS:")
    h_start = text.find("HOME TEAM:")
    away_block = text[v_start:h_start] if (v_start != -1 and h_start != -1) else ""
    home_block = text[h_start:] if h_start != -1 else ""

    away_totals = _extract_totals_from_block(away_block)
    home_totals = _extract_totals_from_block(home_block)

    return {
        "away_name": names.get("VISITORS", ""),
        "home_name": names.get("HOME TEAM", ""),
        "away_first_half": away_first,
        "home_first_half": home_first,
        "away_totals": away_totals,
        "home_totals": home_totals,
        "away_pts": away_pts,
        "home_pts": home_pts,
    }

# ---------- main scrape orchestrator ----------

def scrape_range(start_year: int, end_year: int, out_csv: str, sleep_sec: float = 0.6):
    """
    start_year=2010, end_year=2024 covers 2010-2011 ... 2024-2025.
    Writes one CSV with one row per game.
    """
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    seasons = [f"{y}-{y + 1}" for y in range(start_year, end_year + 1)]
    fieldnames = [
        "season","date","home","opponent","location_text","result_text",
        "cnu_pts","opp_pts",
        "cnu_fgm","cnu_fga","cnu_orb","cnu_drb","cnu_trb","cnu_to",
        "opp_fgm","opp_fga","opp_orb","opp_drb","opp_trb","opp_to",
        "cnu_first_half","opp_first_half","ot","box_url"
    ]
    out_rows = []

    for season in seasons:
        season_url = BASE_SEASON_URL_TMPL.format(season=season)
        try:
            html = fetch(season_url)
        except Exception as e:
            print(f"[WARN] Could not open season {season}: {e}")
            continue

        games = parse_game_result_rows(html, season_url)
        print(f"{season}: found {len(games)} box links")

        for (date_text, location_text, result_text, box_url) in games:
            time.sleep(sleep_sec)
            try:
                box_html = fetch(box_url)
            except Exception as e:
                print(f"[WARN] {season} {date_text} failed: {box_url} -> {e}")
                continue

            p = parse_box_page(box_html)

            # Determine if CNU is home or away (handle name variants)
            cname_candidates = ["Christopher Newport", "Chris. Newport", "CNU", "Chris Newport"]
            is_home_cnu = any(x in p["home_name"] for x in cname_candidates)
            is_away_cnu = any(x in p["away_name"] for x in cname_candidates)
            if not (is_home_cnu or is_away_cnu):
                # Shouldn't happen, but be safe.
                continue

            date_iso = clean_date(date_text)
            home_flag = 1 if is_home_cnu else 0
            opponent_name = p["away_name"] if is_home_cnu else p["home_name"]

            cnu_tot = p["home_totals"] if is_home_cnu else p["away_totals"]
            opp_tot = p["away_totals"] if is_home_cnu else p["home_totals"]

            cnu_first = p["home_first_half"] if is_home_cnu else p["away_first_half"]
            opp_first = p["away_first_half"] if is_home_cnu else p["home_first_half"]

            cnu_pts = p["home_pts"] if is_home_cnu else p["away_pts"]
            opp_pts = p["away_pts"] if is_home_cnu else p["home_pts"]

            ot_flag = int(("OT" in result_text.upper()) or ("OT" in (location_text.upper() if location_text else "")))

            row = {
                "season": season,
                "date": date_iso,
                "home": home_flag,
                "opponent": opponent_name,
                "location_text": location_text,
                "result_text": result_text,
                "cnu_pts": cnu_pts,
                "opp_pts": opp_pts,
                "cnu_fgm": cnu_tot.get("fgm") if cnu_tot else None,
                "cnu_fga": cnu_tot.get("fga") if cnu_tot else None,
                "cnu_orb": cnu_tot.get("orb") if cnu_tot else None,
                "cnu_drb": cnu_tot.get("drb") if cnu_tot else None,
                "cnu_trb": cnu_tot.get("trb") if cnu_tot else None,
                "cnu_to":  cnu_tot.get("to")  if cnu_tot else None,
                "opp_fgm": opp_tot.get("fgm") if opp_tot else None,
                "opp_fga": opp_tot.get("fga") if opp_tot else None,
                "opp_orb": opp_tot.get("orb") if opp_tot else None,
                "opp_drb": opp_tot.get("drb") if opp_tot else None,
                "opp_trb": opp_tot.get("trb") if opp_tot else None,
                "opp_to":  opp_tot.get("to")  if opp_tot else None,
                "cnu_first_half": cnu_first,
                "opp_first_half": opp_first,
                "ot": ot_flag,
                "box_url": box_url,
            }
            if cnu_tot is None or opp_tot is None:
                print(f"[DEBUG] Totals missing for {box_url}")
            out_rows.append(row)

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    print(f"Wrote {len(out_rows)} games to {out_csv}")
    return out_csv
