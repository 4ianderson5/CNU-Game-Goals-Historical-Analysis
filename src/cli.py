import argparse
import os

from .cnu_scrape import scrape_range
from .process_goals import build_goals
from .report_rule import rule_report

def main():
    parser = argparse.ArgumentParser(description="CNU MBB 3-of-4 Goals CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scrape = sub.add_parser("scrape", help="Scrape seasons into a raw CSV")
    p_scrape.add_argument("--start", type=int, required=True, help="Start season first year (e.g., 2010 for 2010-11)")
    p_scrape.add_argument("--end", type=int, required=True, help="End season first year (e.g., 2024 for 2024-25)")
    p_scrape.add_argument("--out", type=str, default="data/cnu_games_raw.csv", help="Output CSV path")
    p_scrape.add_argument("--sleep", type=float, default=0.6, help="Seconds to sleep between box pages")

    p_proc = sub.add_parser("process", help="Build features and goals from raw CSV")
    p_proc.add_argument("--in", dest="in_csv", type=str, required=True, help="Raw CSV path")
    p_proc.add_argument("--out", type=str, default="data/cnu_games_with_goals.csv", help="Output CSV path")

    p_rep = sub.add_parser("report", help="Print quick metrics for the 3-of-4 rule")
    p_rep.add_argument("--in", dest="in_csv", type=str, required=True, help="CSV with goals")

    args = parser.parse_args()

    # Helpful for diagnosing path issues:
    print("CWD:", os.getcwd())

    if args.cmd == "scrape":
        scrape_range(args.start, args.end, args.out, sleep_sec=args.sleep)
    elif args.cmd == "process":
        build_goals(args.in_csv, args.out)
    elif args.cmd == "report":
        rule_report(args.in_csv)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
