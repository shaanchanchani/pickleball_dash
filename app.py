import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO
from collections import Counter
import plotly.graph_objects as go
from datetime import datetime
import colorsys

def get_qualified_players(df, min_games):
    player_counts = pd.concat([df['Team 1 Player 1'], df['Team 1 Player 2'], 
                               df['Team 2 Player 1'], df['Team 2 Player 2']]).value_counts()
    return set(player_counts[player_counts >= min_games].index)

def filter_dataframe(df, qualified_players):
    return df[
        df['Team 1 Player 1'].isin(qualified_players) &
        df['Team 1 Player 2'].isin(qualified_players) &
        df['Team 2 Player 1'].isin(qualified_players) &
        df['Team 2 Player 2'].isin(qualified_players)
    ]

def calculate_win_percentages(df, min_games):
    qualified_players = get_qualified_players(df, min_games)
    filtered_df = filter_dataframe(df, qualified_players)

    player_stats = {player: {'wins': 0, 'total_games': 0, 'games': []} for player in qualified_players}

    for _, row in filtered_df.iterrows():
        winning_team = row['Winner']
        for team in [1, 2]:
            for player in [1, 2]:
                player_name = row[f'Team {team} Player {player}']
                player_stats[player_name]['total_games'] += 1
                player_stats[player_name]['games'].append(row.to_dict())
                if winning_team == f"Team {team}":
                    player_stats[player_name]['wins'] += 1

    stats_df = pd.DataFrame([
        {
            'Player': player,
            'Win %': (stats['wins'] / stats['total_games']) * 100 if stats['total_games'] > 0 else 0,
            'Total Games': stats['total_games'],
            'Games': stats['games']
        }
        for player, stats in player_stats.items()
    ])
    return stats_df.sort_values('Win %', ascending=False)

def calculate_strength_of_schedule(df, stats_df, min_games):
    qualified_players = get_qualified_players(df, min_games)
    filtered_df = filter_dataframe(df, qualified_players)

    player_sos = {player: {'teammate_win_pct': 0, 'opponent_win_pct': 0, 'games_played': 0, 
                           'teammates': [], 'opponents': []} for player in qualified_players}

    for _, row in filtered_df.iterrows():
        for team in [1, 2]:
            for player in [1, 2]:
                current_player = row[f'Team {team} Player {player}']

                teammate = row[f'Team {team} Player {3-player}']
                teammate_win_pct = stats_df.loc[stats_df['Player'] == teammate, 'Win %'].values[0]
                player_sos[current_player]['teammate_win_pct'] += teammate_win_pct
                player_sos[current_player]['teammates'].append((teammate, teammate_win_pct))

                opp_team = 3 - team
                for opp_player in [1, 2]:
                    opponent = row[f'Team {opp_team} Player {opp_player}']
                    opp_win_pct = stats_df.loc[stats_df['Player'] == opponent, 'Win %'].values[0]
                    player_sos[current_player]['opponent_win_pct'] += opp_win_pct
                    player_sos[current_player]['opponents'].append((opponent, opp_win_pct))

                player_sos[current_player]['games_played'] += 1

    sos_df = pd.DataFrame([
        {
            'Player': player,
            'SoS Ratio': (sos['opponent_win_pct'] / (sos['games_played'] * 2)) / 
                         (sos['teammate_win_pct'] / sos['games_played']) if sos['games_played'] > 0 else 0,
            'Teammate Win %': sos['teammate_win_pct'] / sos['games_played'] if sos['games_played'] > 0 else 0,
            'Opponent Win %': sos['opponent_win_pct'] / (sos['games_played'] * 2) if sos['games_played'] > 0 else 0,
            'Total Games': sos['games_played'],
            'Teammates': sos['teammates'],
            'Opponents': sos['opponents']
        }
        for player, sos in player_sos.items()
    ])
    return sos_df.sort_values('SoS Ratio', ascending=False)

def calculate_win_percentages_by_games(df, min_games):
    qualified_players = get_qualified_players(df, min_games)
    filtered_df = filter_dataframe(df, qualified_players)

    player_stats = {player: {'wins': 0, 'games': 0, 'percentages': []} for player in qualified_players}

    for _, row in filtered_df.iterrows():
        winning_team = row['Winner']
        for team in [1, 2]:
            for player in [1, 2]:
                player_name = row[f'Team {team} Player {player}']

                player_stats[player_name]['games'] += 1
                if winning_team == f"Team {team}":
                    player_stats[player_name]['wins'] += 1

                win_percentage = (player_stats[player_name]['wins'] / player_stats[player_name]['games']) * 100
                player_stats[player_name]['percentages'].append(win_percentage)

    return player_stats
def get_distinct_colors(n):
    HSV_tuples = [(x * 1.0 / n, 0.7, 0.9) for x in range(n)]
    return [f'rgb({int(r*255)},{int(g*255)},{int(b*255)})' for r, g, b in map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples)]



def plot_win_percentages_by_games(df, min_games):
    player_data = calculate_win_percentages_by_games(df, min_games)

    fig = go.Figure()

    colors = get_distinct_colors(len(player_data))
    max_games = max(len(data['percentages']) for data in player_data.values())

    for (player, data), color in zip(player_data.items(), colors):
        games = list(range(1, len(data['percentages']) + 1))
        win_percentages = data['percentages']

        fig.add_trace(go.Scatter(
            x=games,
            y=win_percentages,
            mode='lines',
            name=player,
            line=dict(shape='spline', smoothing=1.3, color=color),
            hovertemplate='<b>%{text}</b><br>' +
                          'Games Played: %{x}<br>' +
                          'Win %: %{y:.1f}%<extra></extra>',
            text=[player] * len(games)
        ))

    fig.update_layout(
        title=f'Win % by Games Played',
        xaxis_title='Games Played',
        yaxis_title='Win Percentage (%)',
        hovermode='closest',
        legend_title='Player',
        # legend=dict(
        #     orientation="h",
        #     yanchor="bottom",
        #     y=1.02,
        #     xanchor="right",
        #     x=1
        # ),
        # updatemenus=[
        #     dict(
        #         type="buttons",
        #         direction="right",
        #         x=0.7,
        #         y=1.2,
        #         showactive=True,
        #         buttons=list([
        #             dict(label="All Games",
        #                  method="relayout",
        #                  args=[{"xaxis.range": [1, max_games]}]),
        #             dict(label="First 10 Games",
        #                  method="relayout",
        #                  args=[{"xaxis.range": [1, 10]}]),
        #             dict(label="Last 10 Games",
        #                  method="relayout",
        #                  args=[{"xaxis.range": [max(1, max_games - 9), max_games]}]),
        #         ]),
        #     )
        # ]
    )

    fig.update_xaxes(rangeslider_visible=True)

    return fig

def calculate_sos_adjusted_win_percentages(df, min_games):
    qualified_players = get_qualified_players(df, min_games)
    filtered_df = filter_dataframe(df, qualified_players)

    player_stats = {player: {'wins': 0, 'games': 0, 'sos_sum': 0, 'percentages': []} for player in qualified_players}

    for _, row in filtered_df.iterrows():
        winning_team = row['Winner']
        for team in [1, 2]:
            opponent_team = 3 - team
            for player in [1, 2]:
                player_name = row[f'Team {team} Player {player}']

                player_stats[player_name]['games'] += 1
                if winning_team == f"Team {team}":
                    player_stats[player_name]['wins'] += 1

                # Calculate SoS for this game
                opponent_win_pcts = [
                    player_stats[row[f'Team {opponent_team} Player {i}']]['wins'] / 
                    player_stats[row[f'Team {opponent_team} Player {i}']]['games']
                    if player_stats[row[f'Team {opponent_team} Player {i}']]['games'] > 0 else 0
                    for i in [1, 2]
                ]
                game_sos = sum(opponent_win_pcts) / 2

                player_stats[player_name]['sos_sum'] += game_sos

                win_percentage = player_stats[player_name]['wins'] / player_stats[player_name]['games']
                cumulative_sos = player_stats[player_name]['sos_sum'] / player_stats[player_name]['games']
                sos_adjusted_win_percentage = win_percentage * cumulative_sos * 100

                player_stats[player_name]['percentages'].append(sos_adjusted_win_percentage)

    return player_stats
def display_sos_calculation(player_data):
    st.markdown(f"### SoS for {player_data['Player']}")

    # Custom CSS for left-aligned labels and right-aligned values
    st.markdown("""
    <style>
    .metric-label {
        text-align: left !important;
        color: #888;
        font-size: 14px;
    }
    .metric-value {
        text-align: right !important;
        font-size: 18px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    # Display metrics
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<p class="metric-label">Teammate Win %</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Opponent Win %</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">SoS Ratio</p>', unsafe_allow_html=True)

    with col2:
        st.markdown(f'<p class="metric-value">{player_data["Teammate Win %"]:.1f}%</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{player_data["Opponent Win %"]:.1f}%</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{player_data["SoS Ratio"]:.2f}</p>', unsafe_allow_html=True)

    # Create a dataframe for teammates and opponents
    teammates = Counter(player for player, _ in player_data['Teammates'])
    opponents = Counter(player for player, _ in player_data['Opponents'])

    max_length = max(len(teammates), len(opponents))

    data = {
        'Teammates': [f"{player} ({count})" for player, count in teammates.items()] + [''] * (max_length - len(teammates)),
        'Opponents': [f"{player} ({count})" for player, count in opponents.items()] + [''] * (max_length - len(opponents))
    }

    df = pd.DataFrame(data)

    st.table(df)


def main():
    st.set_page_config(layout="wide")
    st.title("Engine Works Pickleball Stats")
# Add this CSS to your Streamlit app to make the metric text smaller
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] {
            font-size: 18px;
        }
        [data-testid="stMetricLabel"] {
            font-size: 14px;
        }
        </style>
        """, unsafe_allow_html=True)

    try:
        df = pd.read_csv('data2.csv')
    except FileNotFoundError:
        st.error("Error: 'data2.csv' file not found in the current directory.")
        return

    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:        
        min_games = st.slider("Minimum games played", 
                              min_value=1, 
                              max_value=int(df['Team 1 Player 1'].value_counts().max()), 
                              value=1)

        qualified_players = get_qualified_players(df, min_games)
        selected_player = st.selectbox("Select player for SoS calculation:", 
                                       sorted(qualified_players))

        stats_df = calculate_win_percentages(df, min_games)
        sos_df = calculate_strength_of_schedule(df, stats_df, min_games)

        display_sos_calculation(sos_df[sos_df['Player'] == selected_player].iloc[0])

    with col2:
        fig_win_by_games = plot_win_percentages_by_games(df, min_games)
        st.plotly_chart(fig_win_by_games, use_container_width=True)

        sos_adjusted_stats = calculate_sos_adjusted_win_percentages(df, min_games)
        fig_sos_adjusted = go.Figure()
        colors = get_distinct_colors(len(sos_adjusted_stats))

        for (player, data), color in zip(sos_adjusted_stats.items(), colors):
            games = list(range(1, len(data['percentages']) + 1))
            fig_sos_adjusted.add_trace(go.Scatter(
                x=games,
                y=data['percentages'],
                mode='lines',
                name=player,

                line=dict(shape='spline', smoothing=1.3, color=color),

                hovertemplate='<b>%{text}</b><br>Games Played: %{x}<br>SoS Adjusted Win %: %{y:.1f}%<extra></extra>',
                text=[player] * len(games)
            ))

        fig_sos_adjusted.update_layout(
            title=f'Adjusted Win % by SoS',
            xaxis_title='Games Played',
            yaxis_title='SoS Adjusted Win Percentage (%)',
            hovermode='closest',
            legend_title='Player'
        )
        st.plotly_chart(fig_sos_adjusted, use_container_width=True)

    with col3:
        # st.subheader("Win Percentage")
        stats_df_sorted = stats_df.sort_values('Win %', ascending=True)
        fig_win = px.bar(stats_df_sorted, y='Player', x='Win %', 
                         title=f"Win % by Player (Min. {min_games} games)",
                         hover_data=['Total Games'],
                         labels={'Win %': 'Win Percentage'},
                         orientation='h')
        fig_win.update_traces(
            hovertemplate="<br>".join([
                "Player: %{y}",
                "Win %: %{x:.1f}%",
                "Total Games: %{customdata[0]}"
            ]),
            marker=dict(color=stats_df_sorted['Win %'], colorscale='Viridis')
        )
        fig_win.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_win, use_container_width=True)

        sos_df_sorted = sos_df.sort_values('SoS Ratio', ascending=True)
        fig_sos = px.bar(sos_df_sorted, y='Player', x='SoS Ratio', 
                         title=f"SoS Ratio by Player (Min. {min_games} games)",
                         hover_data=['Teammate Win %', 'Opponent Win %', 'Total Games'],
                         labels={'SoS Ratio': 'SoS Ratio'},
                         orientation='h')
        fig_sos.update_traces(
            hovertemplate="<br>".join([
                "Player: %{y}",
                "SoS Ratio: %{x:.2f}",
                "Teammate Win %: %{customdata[0]:.1f}%",
                "Opponent Win %: %{customdata[1]:.1f}%",
                "Total Games: %{customdata[2]}"
            ]),
            marker=dict(color=sos_df_sorted['SoS Ratio'], colorscale='Viridis')
        )
        fig_sos.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_sos, use_container_width=True)
    st.subheader("Raw Data")
    # Get all unique players
    all_players = sorted(set(df['Team 1 Player 1'].unique()) | 
                         set(df['Team 1 Player 2'].unique()) | 
                         set(df['Team 2 Player 1'].unique()) | 
                         set(df['Team 2 Player 2'].unique()))

    # Create a multiselect widget for player selection
    selected_players = st.multiselect("Select players to filter games:", all_players)

    # Filter the dataframe based on selected players
    if selected_players:
        filtered_df = df[
            (df['Team 1 Player 1'].isin(selected_players)) |
            (df['Team 1 Player 2'].isin(selected_players)) |
            (df['Team 2 Player 1'].isin(selected_players)) |
            (df['Team 2 Player 2'].isin(selected_players))
        ]
    else:
        filtered_df = df

    # Display the filtered dataframe
    st.dataframe(filtered_df)

if __name__ == "__main__":
    main()
