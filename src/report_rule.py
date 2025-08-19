import pandas as pd

def rule_report(in_csv: str):
    df = pd.read_csv(in_csv)
    if "win" not in df.columns or "goals_hit" not in df.columns:
        raise ValueError("Input must contain 'win' and 'goals_hit'. Run the 'process' step first.")

    print("=== Win rate by # of goals hit ===")
    for k in range(0, 5):
        mask = (df["goals_hit"] == k)
        n = int(mask.sum())
        if n == 0:
            print(f"{k} goals: N=0")
            continue
        wr = float(df.loc[mask, "win"].mean())
        print(f"{k} goals: N={n:3d} | Win%={wr:0.3f}")

    print("\n=== 3-of-4 rule as classifier (predict WIN if goals_hit >= 3) ===")
    df["pred_win"] = (df["goals_hit"] >= 3).astype(int)  # noinspection PyUnresolvedReferences
    tp = int(((df["pred_win"] == 1) & (df["win"] == 1)).sum())
    fp = int(((df["pred_win"] == 1) & (df["win"] == 0)).sum())
    tn = int(((df["pred_win"] == 0) & (df["win"] == 0)).sum())
    fn = int(((df["pred_win"] == 0) & (df["win"] == 1)).sum())

    acc = (tp + tn) / max(1, (tp + tn + fp + fn))
    prec = tp / max(1, (tp + fp))
    rec = tp / max(1, (tp + fn))
    print(f"Confusion: TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    print(f"Metrics:   ACC={acc:0.3f}, PREC={prec:0.3f}, REC={rec:0.3f}")

    if (tp + fp) > 0:
        print(f"Calibration among predicted 'win': {tp / (tp + fp):0.3f}")
