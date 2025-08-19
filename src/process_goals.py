import os
import pandas as pd

def build_goals(in_csv: str, out_csv: str):
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    df = pd.read_csv(in_csv)

    # Outcome
    df["win"] = (df["cnu_pts"] > df["opp_pts"]).astype(int)  # noinspection PyUnresolvedReferences

    # 1) Outrebound
    df["goal_reb"] = (df["cnu_trb"] > df["opp_trb"]).astype(int)  # noinspection PyUnresolvedReferences

    # 2) Fewer turnovers
    # If you have rare missing TOs, either drop those rows or treat missing as very large to avoid false "wins".
    # Uncomment the next two lines if needed:
    # df["cnu_to"] = df["cnu_to"].fillna(10**9)
    # df["opp_to"] = df["opp_to"].fillna(10**9)
    df["goal_to"] = (df["cnu_to"] < df["opp_to"]).astype(int)  # noinspection PyUnresolvedReferences

    # 3) 40% of our missed shots (coach definition)
    misses = df["cnu_fga"] - df["cnu_fgm"]
    df["goal_orb"] = ((misses == 0) | ((df["cnu_orb"] / misses) >= 0.40)).astype(int)  # noinspection PyUnresolvedReferences

    # 4) Opponent < 30 in 1st half
    df["goal_def30"] = (df["opp_first_half"] < 30).astype(int)  # noinspection PyUnresolvedReferences

    df["goals_hit"] = df[["goal_reb", "goal_to", "goal_orb", "goal_def30"]].sum(axis=1)

    df.to_csv(out_csv, index=False)
    print(f"Wrote {len(df)} rows with goals -> {out_csv}")
    return out_csv
