import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# CNU brand colors (Pantone -> HEX)
# -----------------------------
CNU_BLUE   = "#0033A0"  # Pantone 286
CNU_GRAY   = "#A7A8AA"  # Pantone 429
CNU_SILVER = "#8A8D8F"  # Pantone 877 (on-screen approximation)
BG_LIGHT   = "#F7F8FA"
TEXT_DARK  = "#111827"

st.set_page_config(page_title="CNU Basketball Goals Dashboard", layout="wide")

# ---- High-contrast CSS & tiles ----
st.markdown(
    f"""
    <style>
      .main {{ background-color: {BG_LIGHT}; }}
      .block-container {{ padding-top: 1.5rem; padding-bottom: 1.5rem; }}
      .metric-tile {{
        background: linear-gradient(135deg, {CNU_BLUE} 0%, {CNU_SILVER} 100%);
        color: white;
        border-radius: 14px;
        padding: 18px 18px 12px 18px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.08);
      }}
      .metric-tile h3 {{ font-weight: 600; letter-spacing: .3px; margin: 0 0 6px 0; }}
      .metric-tile h2 {{ margin: 0; font-size: 28px; }}
      .subtitle {{ color: {CNU_BLUE}; font-weight: 700; letter-spacing: .3px; margin-top: .25rem; }}
      .stDataFrame thead tr th {{ background-color: {CNU_BLUE} !important; color: white !important; }}
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data
def load_data():
    return pd.read_csv("data/cnu_games_with_goals.csv")

df = load_data()
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["pred_win"] = (df["goals_hit"] >= 3).astype(int)

# ----------------------------
# HEADER & FILTERS
# ----------------------------
st.title("CNU Basketball Game Goals")
st.caption(">30 at half, outrebound ______, 40% of offensive rebounds, less turnovers")

seasons = sorted(df["season"].dropna().unique())
season_choice = st.multiselect("Select seasons", seasons, default=seasons)
filtered = df[df["season"].isin(season_choice)].copy()

if filtered.empty:
    st.warning("No games in the selected season range.")
    st.stop()

# ----------------------------
# METRICS
# ----------------------------
tp = ((filtered.pred_win==1)&(filtered.win==1)).sum()
fp = ((filtered.pred_win==1)&(filtered.win==0)).sum()
tn = ((filtered.pred_win==0)&(filtered.win==0)).sum()
fn = ((filtered.pred_win==0)&(filtered.win==1)).sum()

total = max(1, tp+fp+tn+fn)
acc  = (tp+tn)/total
prec = tp/max(1, tp+fp)
rec  = tp/max(1, tp+fn)
cal  = prec  # calibration among predicted wins equals precision

c1, c2, c3, c4 = st.columns([1,1,1,1])
with c1:
    st.markdown(f"<div class='metric-tile'><h3>Accuracy</h3><h2>{acc:.2%}</h2></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-tile'><h3>Precision</h3><h2>{prec:.2%}</h2></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-tile'><h3>Recall</h3><h2>{rec:.2%}</h2></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-tile'><h3>Calibration (Pred. Wins)</h3><h2>{cal:.2%}</h2></div>", unsafe_allow_html=True)

st.markdown(f"<span class='subtitle'>Confusion:</span> TP={tp} • FP={fp} • TN={tn} • FN={fn}", unsafe_allow_html=True)
st.markdown("---")

# ---------------------------------------
# CHART 1: Win % by Number of Goals Hit
# ---------------------------------------
st.subheader("Win rate by number of goals achieved")

wr = filtered.groupby("goals_hit")["win"].mean().reindex([0,1,2,3,4]).reset_index()
wr["Games"] = filtered.groupby("goals_hit")["win"].count().reindex([0,1,2,3,4]).values

fig1 = px.bar(
    wr, x="goals_hit", y="win", text="Games",
    labels={"goals_hit": "Goals hit", "win": "Win %"},
    color="goals_hit",
    color_discrete_sequence=[CNU_GRAY, CNU_SILVER, "#d1d5db", CNU_BLUE, "#001e5e"],
)
fig1.update_traces(textposition="outside", textfont_color=TEXT_DARK)
fig1.update_layout(
    template="simple_white",
    font=dict(color=TEXT_DARK),
    yaxis=dict(
        title=dict(text="Win %", font=dict(color=TEXT_DARK)),
        tickformat=".0%",
        gridcolor=CNU_GRAY,
        zerolinecolor=CNU_GRAY,
        color=TEXT_DARK,
        tickfont=dict(color=TEXT_DARK),
    ),
    xaxis=dict(
        title=dict(text="Goals hit", font=dict(color=TEXT_DARK)),
        color=TEXT_DARK,
        tickfont=dict(color=TEXT_DARK),
    ),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(t=30, r=20, b=40, l=40),
)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# ------------------------------------------------------------------
# CHART 2 (replacement): Season Comparison (Win% vs Rule Accuracy)
# ------------------------------------------------------------------
st.subheader("Season comparison: Win% vs. Rule accuracy")

grp = (
    filtered.groupby("season")
    .apply(lambda g: pd.Series({
        "win_pct": g["win"].mean(),
        "rule_acc": (g["pred_win"] == g["win"]).mean(),
        "games": g["win"].size,
        "avg_goals": g["goals_hit"].mean(),
    }))
    .reset_index()
    .sort_values("season")
)

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=grp["season"], y=grp["win_pct"],
    name="Win %",
    marker_color=CNU_BLUE,
    text=[f"{v:.0%}" for v in grp["win_pct"]],
    textposition="outside",
))
fig2.add_trace(go.Bar(
    x=grp["season"], y=grp["rule_acc"],
    name="Rule Accuracy",
    marker_color=CNU_SILVER,
    text=[f"{v:.0%}" for v in grp["rule_acc"]],
    textposition="outside",
))
fig2.update_layout(
    barmode="group",
    template="simple_white",
    font=dict(color=TEXT_DARK),
    yaxis=dict(
        title=dict(text="Rate", font=dict(color=TEXT_DARK)),
        tickformat=".0%",
        gridcolor=CNU_GRAY,
        zerolinecolor=CNU_GRAY,
        rangemode="tozero",
        color=TEXT_DARK,
        tickfont=dict(color=TEXT_DARK),
    ),
    xaxis=dict(
        title=dict(text="Season", font=dict(color=TEXT_DARK)),
        tickangle=-30,
        color=TEXT_DARK,
        tickfont=dict(color=TEXT_DARK),
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(t=30, r=20, b=60, l=40),
)
st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------
# CHART 3 (optional): Goals Mix by Season (stacked distribution)
# ------------------------------------------------------------------
with st.expander("Goals mix by season (distribution of 0–4 goals hit)"):
    mix = (
        filtered
        .groupby(["season", "goals_hit"])["win"]
        .count()
        .reset_index(name="N")
    )
    totals = mix.groupby("season")["N"].transform("sum")
    mix["Share"] = mix["N"] / totals

    fig3 = px.bar(
        mix, x="season", y="Share", color="goals_hit",
        labels={"Share":"Share of games", "season":"Season", "goals_hit":"Goals hit"},
        color_discrete_sequence=[CNU_GRAY, CNU_SILVER, "#d1d5db", CNU_BLUE, "#001e5e"],
    )
    fig3.update_layout(
        barmode="stack",
        template="simple_white",
        font=dict(color=TEXT_DARK),
        yaxis=dict(
            title=dict(text="Share", font=dict(color=TEXT_DARK)),
            tickformat=".0%",
            gridcolor=CNU_GRAY,
            zerolinecolor=CNU_GRAY,
            rangemode="tozero",
            color=TEXT_DARK,
            tickfont=dict(color=TEXT_DARK),
        ),
        xaxis=dict(
            title=dict(text="Season", font=dict(color=TEXT_DARK)),
            tickangle=-30,
            color=TEXT_DARK,
            tickfont=dict(color=TEXT_DARK),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=30, r=20, b=60, l=40),
    )
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ----------------------------
# GAME TABLE + HIGHLIGHT
# ----------------------------
st.subheader("Game detail")
filtered["rule_correct"] = ((filtered["pred_win"] == filtered["win"]).map({True:"✅", False:"❌"}))
view_cols = [
    "date","season","opponent","win","goals_hit",
    "goal_reb","goal_to","goal_orb","goal_def30",
    "cnu_pts","opp_pts","rule_correct"
]
st.dataframe(
    filtered[view_cols].sort_values("date", ascending=False),
    use_container_width=True,
)
