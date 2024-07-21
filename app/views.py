import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from django.shortcuts import render
from django.http import JsonResponse
from datetime import datetime
from django.http import HttpResponse

# Load your data
df = pd.read_csv("t20_wc_2024_deliveries.csv")


def get_match_data(match_ids):
    match_info = {}
    for match_id in match_ids:
        teams = df[df["match_id"] == match_id]["batting_team"].unique().tolist()
        print(f"Teams for match {match_id}: {teams}")  # Debugging print
        if len(teams) < 2:
            continue  # Skip if there are not enough teams to form a match
        match_info[match_id] = {
            "teams": f"{teams[0]} vs {teams[1]}",
            "stats": {},
            "team_performance": {},
            "powerplay": {},
            "result": "",
        }

        # Match stats
        for team in teams:
            temp_df = df[(df["match_id"] == match_id) & (df["batting_team"] == team)]
            match_info[match_id]["stats"][team] = {
                "Total Score": temp_df["runs_of_bat"].sum() + temp_df["extras"].sum(),
                "Runs From Bat": temp_df["runs_of_bat"].sum(),
                "Extra Runs": temp_df["extras"].sum(),
                "Total Wides": temp_df["wide"].sum(),
                "Total Leg Byes": temp_df["legbyes"].sum(),
                "Total Byes": temp_df["byes"].sum(),
                "Total No Balls": temp_df["noballs"].sum(),
                "Total Wickets": temp_df["player_dismissed"].nunique(),
                "Over": temp_df["over"].max(),  # Changed tail(1) to max() for last over
            }

        # Team performance
        fig = go.Figure()
        for team in teams:
            temp_df = df[(df["match_id"] == match_id) & (df["batting_team"] == team)]
            temp_df["Total_Score"] = temp_df["runs_of_bat"] + temp_df["extras"]
            cumulative_runs = (
                temp_df.groupby("over")["Total_Score"].sum().cumsum().reset_index()
            )
            fig.add_trace(
                go.Scatter(
                    x=cumulative_runs["over"],
                    y=cumulative_runs["Total_Score"],
                    mode="lines",
                    name=team,
                )
            )
            dismissals = temp_df[temp_df["player_dismissed"].notnull()]
            dismissals_cumulative_runs = (
                dismissals.groupby("over")["Total_Score"].sum().cumsum().reset_index()
            )
            fig.add_trace(
                go.Scatter(
                    x=dismissals_cumulative_runs["over"],
                    y=dismissals_cumulative_runs["Total_Score"],
                    mode="markers",
                    name=f"{team} Wickets",
                )
            )
        fig.update_layout(
            title=f"{teams[0]} vs {teams[1]}",
            xaxis_title="Over",
            yaxis_title="Cumulative Total Score",
        )
        match_info[match_id]["team_performance"] = fig.to_html(full_html=False)

        # Powerplay analysis
        figures = []
        for team in teams:
            temp_df = df[(df["match_id"] == match_id) & (df["batting_team"] == team)]
            temp_df = temp_df.assign(
                Total_Score=temp_df["runs_of_bat"] + temp_df["extras"]
            )
            first_phase = temp_df[temp_df["over"] <= 6]
            second_phase = temp_df[(temp_df["over"] > 6) & (temp_df["over"] <= 15)]
            third_phase = temp_df[temp_df["over"] > 15]
            phases_df = pd.DataFrame(
                {
                    "Phase": ["Powerplay", "Middle Overs", "Death Overs"],
                    "Total_Score": [
                        first_phase["Total_Score"].sum(),
                        second_phase["Total_Score"].sum(),
                        third_phase["Total_Score"].sum(),
                    ],
                    "Total_Wickets": [
                        first_phase["player_dismissed"].nunique(),
                        second_phase["player_dismissed"].nunique(),
                        third_phase["player_dismissed"].nunique(),
                    ],
                }
            )
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=phases_df["Phase"],
                    y=phases_df["Total_Score"],
                    name="Total Score",
                    text=phases_df["Total_Score"],
                    textposition="outside"
                )
            )
            fig.add_trace(
                go.Bar(
                    x=phases_df["Phase"],
                    y=phases_df["Total_Wickets"],
                    name="Total Wickets",
                    text=phases_df["Total_Wickets"],
                    textposition="outside"
                )
            )
            fig.update_layout(
                title=f"Scores and Wickets for {team} in Match {match_id}",
                xaxis_title="Phase",
                yaxis_title="Count",
                barmode='group'
            )
            figures.append(fig.to_html(full_html=False))
        match_info[match_id]["powerplay"] = figures

        # Match result
        temp_df1 = df[(df["match_id"] == match_id) & (df["batting_team"] == teams[0])]
        team1_score = temp_df1["runs_of_bat"].sum() + temp_df1["extras"].sum()
        team1_wickets = temp_df1["player_dismissed"].nunique()
        temp_df2 = df[(df["match_id"] == match_id) & (df["batting_team"] == teams[1])]
        team2_score = temp_df2["runs_of_bat"].sum() + temp_df2["extras"].sum()
        team2_wickets = temp_df2["player_dismissed"].nunique()
        if team1_score > team2_score:
            result = f"{teams[0]} won by {team1_score - team2_score} runs"
        elif team1_score < team2_score:
            result = f"{teams[1]} won by {10 - team2_wickets} wickets"
        else:
            result = "The match is a tie"
        match_info[match_id]["result"] = result
    
    return match_info

def match_details(request):
    if request.method == "POST":
        date = request.POST.get("date")
        # Parse the input date string to the correct format
        date = pd.to_datetime(date).strftime("%Y-%m-%d")
        
        # Convert the date column in the dataframe to the correct format
        df['date'] = pd.to_datetime(df['date']).dt.strftime("%Y-%m-%d")
        
        # Find matches for the selected date
        match_ids = df[df["date"] == date]["match_id"].unique().tolist()
        matches = {
            match_id: f"{df[df['match_id'] == match_id]['batting_team'].unique()[0]} vs {df[df['match_id'] == match_id]['batting_team'].unique()[1]}"
            for match_id in match_ids
        }
        
        # Check for specific date and conditionally modify matches        
        if matches:
            return render(
                request, "select_match.html", {"matches": matches, "date": date}
            )
        else:
            return HttpResponse("No matches found for the selected date.")
    
    return render(request, "select_date.html")

def match_details_view(request, match_id):
    match_info = get_match_data([match_id])
    return render(request, "match_details.html", {"match_info": match_info})
