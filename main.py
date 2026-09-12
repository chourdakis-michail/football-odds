import math
import pandas as pd
import streamlit as st


def poisson_probability(k, lambd):
    return (lambd**k * math.exp(-lambd)) / math.factorial(k)


def calculate_match_odds(
    home_scored,
    home_conceded,
    away_scored,
    away_conceded,
    league_home=1.50,
    league_away=1.00,
):
    home_attack = home_scored / league_home
    home_defense = home_conceded / league_away
    away_attack = away_scored / league_away
    away_defense = away_conceded / league_home

    lambda_home = home_attack * away_defense * league_home
    lambda_away = away_attack * home_defense * league_away

    prob_home, prob_draw, prob_away = 0.0, 0.0, 0.0
    prob_over25, prob_under25 = 0.0, 0.0
    prob_gg, prob_ng = 0.0, 0.0

    for h in range(7):
        p_h = poisson_probability(h, lambda_home)
        for a in range(7):
            p_a = poisson_probability(a, lambda_away)
            p_score = p_h * p_a

            if h > a:
                prob_home += p_score
            elif h == a:
                prob_draw += p_score
            else:
                prob_away += p_score

            if (h + a) > 2.5:
                prob_over25 += p_score
            else:
                prob_under25 += p_score

            if h > 0 and a > 0:
                prob_gg += p_score
            else:
                prob_ng += p_score

    return {
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "1": (prob_home, 1 / prob_home if prob_home > 0 else 0),
        "X": (prob_draw, 1 / prob_draw if prob_draw > 0 else 0),
        "2": (prob_away, 1 / prob_away if prob_away > 0 else 0),
        "Over 2.5": (prob_over25, 1 / prob_over25 if prob_over25 > 0 else 0),
        "Under 2.5": (
            prob_under25,
            1 / prob_under25 if prob_under25 > 0 else 0,
        ),
        "GG": (prob_gg, 1 / prob_gg if prob_gg > 0 else 0),
        "NG": (prob_ng, 1 / prob_ng if prob_ng > 0 else 0),
    }


st.set_page_config(
    page_title="Football Odds Predictor", page_icon="⚽", layout="wide"
)
st.title("⚽ Προβλεπτικό Μοντέλο Ποδοσφαίρου (Poisson)")

st.sidebar.header("📊 Μέσοι Όροι Πρωταθλήματος")
league_home = st.sidebar.number_input(
    "Μ.Ο. Γκολ Γηπεδούχων Πρωταθλήματος", value=1.50, step=0.05
)
league_away = st.sidebar.number_input(
    "Μ.Ο. Γκολ Φιλοξενούμενων Πρωταθλήματος", value=1.00, step=0.05
)

st.subheader("Στατιστικά Αγώνα")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏠 Γηπεδούχος Ομάδα")
    home_name = st.text_input("Όνομα Γηπεδούχου", value="Ολυμπιακός")
    home_scored = st.number_input(
        f"Μ.Ο. Γκολ που σκοράρει εντός ({home_name})", value=2.10, step=0.1
    )
    home_conceded = st.number_input(
        f"Μ.Ο. Γκολ που δέχεται εντός ({home_name})", value=0.75, step=0.1
    )

with col2:
    st.markdown("### ✈️ Φιλοξενούμενη Ομάδα")
    away_name = st.text_input("Όνομα Φιλοξενούμενου", value="ΠΑΟΚ")
    away_scored = st.number_input(
        f"Μ.Ο. Γκολ που σκοράρει εκτός ({away_name})", value=1.20, step=0.1
    )
    away_conceded = st.number_input(
        f"Μ.Ο. Γκολ που δέχεται εκτός ({away_name})", value=1.20, step=0.1
    )

if st.button("🚀 Υπολογισμός Αποδόσεων", type="primary"):
    res = calculate_match_odds(
        home_scored,
        home_conceded,
        away_scored,
        away_conceded,
        league_home,
        league_away,
    )

    st.markdown("---")
    st.subheader(f"🎯 Αποτελέσματα: {home_name} vs {away_name}")

    m1, m2 = st.columns(2)
    m1.metric("Expected Goals (xG) Γηπεδούχου", res["lambda_home"])
    m2.metric("Expected Goals (xG) Φιλοξενούμενου", res["lambda_away"])

    data = {
        "Αγορά": [
            "1 (Νίκη Γηπεδούχου)",
            "X (Ισοπαλία)",
            "2 (Νίκη Φιλοξενούμενου)",
            "Over 2.5 Goals",
            "Under 2.5 Goals",
            "Goal / Goal (GG)",
            "No Goal (NG)",
        ],
        "Πιθανότητα (%)": [
            f"{res['1'][0]*100:.1f}%",
            f"{res['X'][0]*100:.1f}%",
            f"{res['2'][0]*100:.1f}%",
            f"{res['Over 2.5'][0]*100:.1f}%",
            f"{res['Under 2.5'][0]*100:.1f}%",
            f"{res['GG'][0]*100:.1f}%",
            f"{res['NG'][0]*100:.1f}%",
        ],
        "Δίκαιη Απόδοση": [
            f"{res['1'][1]:.2f}",
            f"{res['X'][1]:.2f}",
            f"{res['2'][1]:.2f}",
            f"{res['Over 2.5'][1]:.2f}",
            f"{res['Under 2.5'][1]:.2f}",
            f"{res['GG'][1]:.2f}",
            f"{res['NG'][1]:.2f}",
        ],
    }

    st.table(pd.DataFrame(data))

