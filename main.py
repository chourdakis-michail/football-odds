import streamlit as st
import math
import requests
import time
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="Football Odds Predictor", layout="wide")

API_KEY = "69207707d6f3499fae03851566eaa7be"
BASE_URL = "https://api.football-data.org/v4/"

headers = {
    "X-Auth-Token": API_KEY
}

# Συνάρτηση υπολογισμού Poisson
def poisson_probability(k, lambd):
    if lambd <= 0:
        return 0.0
    return (math.pow(lambd, k) * math.exp(-lambd)) / math.factorial(k)

# Συνάρτηση ασφαλούς κλήσης API με διαχείριση Throttling
def fetch_api_data(endpoint):
    url = BASE_URL + endpoint
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        retry_after = int(response.headers.get("X-RequestCounter-Reset", 60))
        st.warning(f"Φτάσατε το όριο αιτημάτων. Αναμονή {retry_after} δευτερολέπτων...")
        time.sleep(retry_after)
        response = requests.get(url, headers=headers)
        
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Σφάλμα κατά την ανάκτηση δεδομένων (Code: {response.status_code})")
        return None

st.title("⚽ Προβλεπτικό Μοντέλο Ποδοσφαίρου (Poisson API)")

# Διαθέσιμα πρωταθλήματα στο Free Tier
COMPETITIONS = {
    "Premier League (Αγγλία)": "PL",
    "La Liga (Ισπανία)": "PD",
    "Serie A (Ιταλία)": "SA",
    "Bundesliga (Γερμανία)": "BL1",
    "Ligue 1 (Γαλλία)": "FL1",
    "Eredivisie (Ολλανδία)": "DED",
    "Primeira Liga (Πορτογαλία)": "PPD",
    "Champions League": "CL"
}

selected_comp_label = st.selectbox("Επιλέξτε Πρωτάθλημα:", list(COMPETITIONS.keys()))
comp_code = COMPETITIONS[selected_comp_label]

if st.button("Φόρτωση Ομάδων & Βαθμολογίας"):
    with st.spinner("Ανάκτηση δεδομένων από το Football-Data.org..."):
        data = fetch_api_data(f"competitions/{comp_code}/standings")
        if data and "standings" in data:
            standings = data["standings"][0]["table"]
            st.session_state["teams_data"] = standings
            st.success("Τα δεδομένα φορτώθηκαν επιτυχώς!")

if "teams_data" in st.session_state:
    teams_list = [item["team"]["name"] for item in st.session_state["teams_data"]]
    
    col1, col2 = st.columns(2)
    with col1:
        home_team_name = st.selectbox("Γηπεδούχος Ομάδα:", teams_list, index=0)
    with col2:
        away_team_name = st.selectbox("Φιλοξενούμενη Ομάδα:", teams_list, index=min(1, len(teams_list)-1))

    # Υπολογισμός στατιστικών από τη βαθμολογία (Τρέχουσα Σεζόν)
    home_stats = next(item for item in st.session_state["teams_data"] if item["team"]["name"] == home_team_name)
    away_stats = next(item for item in st.session_state["teams_data"] if item["team"]["name"] == away_team_name)

    home_played = home_stats["playedGames"] if home_stats["playedGames"] > 0 else 1
    away_played = away_stats["playedGames"] if away_stats["playedGames"] > 0 else 1

    home_gf_curr = home_stats["goalsFor"] / home_played
    home_ga_curr = home_stats["goalsAgainst"] / home_played

    away_gf_curr = away_stats["goalsFor"] / away_played
    away_ga_curr = away_stats["goalsAgainst"] / away_played

    # Επιλογή Συνυπολογισμού Περσινής Σεζόν
    st.markdown("---")
    use_prev_season = st.checkbox("➕ Συνυπολογισμός Περσινών Στατιστικών (Ιδανικό για τις πρώτες αγωνιστικές)")

    home_gf_final = home_gf_curr
    home_ga_final = home_ga_curr
    away_gf_final = away_gf_curr
    away_ga_final = away_ga_curr

    if use_prev_season:
        st.info("Εισάγετε τους μέσους όρους της περσινής σεζόν. Το μοντέλο θα υπολογίσει: **70% Φετινά + 30% Περσινά**.")
        col_prev1, col_prev2 = st.columns(2)
        with col_prev1:
            prev_home_gf = st.number_input(f"Περσινά γκολ/αγώνα {home_team_name} (Σκοράρει):", value=home_gf_curr, step=0.1)
            prev_home_ga = st.number_input(f"Περσινά γκολ/αγώνα {home_team_name} (Δέχεται):", value=home_ga_curr, step=0.1)
        with col_prev2:
            prev_away_gf = st.number_input(f"Περσινά γκολ/αγώνα {away_team_name} (Σκοράρει):", value=away_gf_curr, step=0.1)
            prev_away_ga = st.number_input(f"Περσινά γκολ/αγώνα {away_team_name} (Δέχεται):", value=away_ga_curr, step=0.1)

        # Σταθμισμένος Μέσος Όρος (70% Φετινά - 30% Περσινά)
        home_gf_final = (home_gf_curr * 0.7) + (prev_home_gf * 0.3)
        home_ga_final = (home_ga_curr * 0.7) + (prev_home_ga * 0.3)
        away_gf_final = (away_gf_curr * 0.7) + (prev_away_gf * 0.3)
        away_ga_final = (away_ga_curr * 0.7) + (prev_away_ga * 0.3)

    # Υπολογισμός Μέσου Όρου Πρωταθλήματος
    total_goals = sum(item["goalsFor"] for item in st.session_state["teams_data"])
    total_games = sum(item["playedGames"] for item in st.session_state["teams_data"]) / 2
    league_avg_goals = (total_goals / total_games / 2) if total_games > 0 else 1.3

    st.markdown("---")
    st.subheader("📊 Τελικοί Μέσοι Όροι Μοντέλου")
    c1, c2 = st.columns(2)
    c1.write(f"**{home_team_name}**: {home_gf_final:.2f} γκολ/αγώνα (Σκοράρει), {home_ga_final:.2f} γκολ/αγώνα (Δέχεται)")
    c2.write(f"**{away_team_name}**: {away_gf_final:.2f} γκολ/αγώνα (Σκοράρει), {away_ga_final:.2f} γκολ/αγώνα (Δέχεται)")

    if st.button("Υπολογισμός Πιθανοτήτων Poisson"):
        # Υπολογισμός xG
        attack_home = home_gf_final / league_avg_goals if league_avg_goals else 1
        defense_away = away_ga_final / league_avg_goals if league_avg_goals else 1
        lambda_home = attack_home * defense_away * league_avg_goals

        attack_away = away_gf_final / league_avg_goals if league_avg_goals else 1
        defense_home = home_ga_final / league_avg_goals if league_avg_goals else 1
        lambda_away = attack_away * defense_home * league_avg_goals

        # Υπολογισμός Πλέγματος Πιθανοτήτων
        max_goals = 7
        prob_home_win, prob_draw, prob_away_win = 0.0, 0.0, 0.0
        prob_under_25, prob_over_25 = 0.0, 0.0

        for h in range(max_goals):
            for a in range(max_goals):
                p = poisson_probability(h, lambda_home) * poisson_probability(a, lambda_away)
                if h > a: prob_home_win += p
                elif h == a: prob_draw += p
                else: prob_away_win += p

                if (h + a) < 2.5: prob_under_25 += p
                else: prob_over_25 += p

        st.markdown("---")
        st.subheader("🎯 Αποτελέσματα Αγώνα (1X2) & Fair Odds")
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("1 (Νίκη Γηπεδούχου)", f"{prob_home_win*100:.1f}%", f"Απόδοση: {(1/prob_home_win if prob_home_win else 0):.2f}")
        col_res2.metric("X (Ισοπαλία)", f"{prob_draw*100:.1f}%", f"Απόδοση: {(1/prob_draw if prob_draw else 0):.2f}")
        col_res3.metric("2 (Νίκη Φιλοξενούμενου)", f"{prob_away_win*100:.1f}%", f"Απόδοση: {(1/prob_away_win if prob_away_win else 0):.2f}")

        st.markdown("---")
        st.subheader("⚽ Αγορά Γκολ (Over / Under 2.5)")
        col_ou1, col_ou2 = st.columns(2)
        col_ou1.metric("Under 2.5 Γκολ", f"{prob_under_25*100:.1f}%", f"Απόδοση: {(1/prob_under_25 if prob_under_25 else 0):.2f}")
        col_ou2.metric("Over 2.5 Γκολ", f"{prob_over_25*100:.1f}%", f"Απόδοση: {(1/prob_over_25 if prob_over_25 else 0):.2f}")
        # --- ΠΡΟΒΛΕΨΗ ΚΟΡΝΕΡ ---
st.markdown("---")
st.header("⛳ Πρόβλεψη & Αποδόσεις Κόρνερ")

col_c1, col_c2 = st.columns(2)
with col_c1:
    home_corners = st.number_input(
        "Μ.Ο. Κόρνερ Γηπεδούχου (Εντός)",
        min_value=0.0,
        value=5.5,
        step=0.1,
        key="hc",
    )
with col_c2:
    away_corners = st.number_input(
        "Μ.Ο. Κόρνερ Φιλοξενούμενης (Εκτός)",
        min_value=0.0,
        value=4.2,
        step=0.1,
        key="ac",
    )

if st.button("Υπολογισμός Κόρνερ", key="btn_corners"):
    expected_corners = home_corners + away_corners
    corners_range = np.arange(0, 26)
    probs = poisson.pmf(corners_range, expected_corners)

    st.subheader(f"🎯 Αναμενόμενα Κόρνερ Αγώνα: **{expected_corners:.2f}**")

    lines = [8.5, 9.5, 10.5, 11.5]
    data_matrix = []

    for line in lines:
        under_prob = np.sum(probs[corners_range < line])
        over_prob = 1.0 - under_prob

        fair_under = (1 / under_prob) if under_prob > 0 else 0
        fair_over = (1 / over_prob) if over_prob > 0 else 0

        data_matrix.append({
            "Όριο": f"Over/Under {line}",
            "Πιθανότητα Over": f"{over_prob * 100:.1f}%",
            "Fair Over": f"{fair_over:.2f}",
            "Πιθανότητα Under": f"{under_prob * 100:.1f}%",
            "Fair Under": f"{fair_under:.2f}",
        })

    st.table(data_matrix)



