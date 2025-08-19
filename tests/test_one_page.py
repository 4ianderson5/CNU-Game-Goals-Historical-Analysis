import requests
from src.cnu_scrape import parse_box_page, HEADERS

url = "https://static.cnusports.com/custompages/mbball/Stats/2012-2013/cnumgm27.htm"
html = requests.get(url, headers=HEADERS, timeout=30).text
p = parse_box_page(html)
print("Away:", p["away_name"], p["away_totals"])
print("Home:", p["home_name"], p["home_totals"])
print("First halves:", p["away_first_half"], p["home_first_half"])
print("Final:", p["away_pts"], p["home_pts"])
