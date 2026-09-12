import streamlit as st
import math
import requests
import time

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
    
    # Διαχείριση Rate Limiting / Throttling
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

    # Υπολογισμός στατιστικών από τη βαθμολογία
    home_stats = next(item for item in st.session_state["teams_data"] if item["team"]["name"] == home_team_name)
    away_stats = next(item for item in st.session_state["teams_data"] if item["team"]["name"] == away_team_name)

    home_played = home_stats["playedGames"] if home_stats["playedGames"] > 0 else 1
    away_played = away_stats["playedGames"] if away_stats["playedGames"] > 0 else 1

    home_gf_avg = home_stats["goalsFor"] / home_played
    home_ga_avg = home_stats["goalsAgainst"] / home_played

    away_gf_avg = away_stats["goalsFor"] / away_played
    away_ga_avg = away_stats["goalsAgainst"] / away_played

    # Υπολογισμός Μέσου Όρου Πρωταθλήματος
    total_goals = sum(item["goalsFor"] for item in st.session_state["teams_data"])
    total_games = sum(item["playedGames"] for item in st.session_state["teams_data"]) / 2
    league_avg_goals = (total_goals / total_games / 2) if total_games > 0 else 1.3

    st.markdown("---")
    st.subheader("Στατιστικά Μέσων Όρων")
    c1, c2 = st.columns(2)
    c1.write(f"**{home_team_name}**: {home_gf_avg:.2f} γκολ/αγώνα (Σκοράρει), {home_ga_avg:.2f} γκολ/αγώνα (Δέχεται)")
    c2.write(f"**{away_team_name}**: {away_gf_avg:.2f} γκολ/αγώνα (Σκοράρει), {away_ga_avg:.2f} γκολ/αγώνα (Δέχεται)")

    if st.button("Υπολογισμός Πιθανοτήτων Poisson"):
        # Υπολογισμός xG
        attack_home = home_gf_avg / league_avg_goals if league_avg_goals else 1
        defense_away = away_ga_avg / league_avg_goals if league_avg_goals else 1
        lambda_home = attack_home * defense_away * league_avg_goals

        attack_away = away_gf_avg / league_avg_goals if league_avg_goals else 1
        defense_home = home_ga_avg / league_avg_goals if league_avg_goals else 1
        lambda_away = attack_away * defense_home * league_avg_goals

        # Υπολογισμός Πλέγματος Πιθανοτήτων
        max_goals = 6
        prob_home_win = 0.0
        prob_draw = 0.0
        prob_away_win = 0.0

        for h in range(max_goals):
            for a in range(max_goals):
                p = poisson_probability(h, lambda_home) * poisson_probability(a, lambda_away)
                if h > a:
                    prob_home_win += p
                elif h == a:
                    prob_draw += p
                else:
                    prob_away_win += p

        st.markdown("---")
        st.subheader("Αποτελέσματα & Fair Odds")
        col_res1, col_res2, col_res3 = st.columns(3)

        odd_home = 1 / prob_home_win if prob_home_win > 0 else 0
        odd_draw = 1 / prob_draw if prob_draw > 0 else 0
        odd_away = 1 / prob_away_win if prob_away_win > 0 else 0

        col_res1.metric("1 (Νίκη Γηπεδούχου)", f"{prob_home_win*100:.1f}%", f"Απόδοση: {odd_home:.2f}")
        col_res2.metric("X (Ισοπαλία)", f"{prob_draw*100:.1f}%", f"Απόδοση: {odd_draw:.2f}")
        col_res3.metric("2 (Νίκη Φιλοξενούμενου)", f"{prob_away_win*100:.1f}%", f"Απόδοση: {odd_away:.2f}")

