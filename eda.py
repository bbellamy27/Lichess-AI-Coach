"""Plotly chart builders. Styling comes from the 'coach' template in theme.py."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from theme import COLORS, DIVERGING, SEQUENTIAL

OUTCOME_COLORS = {k: COLORS[k] for k in ('Win', 'Draw', 'Loss')}
OUTCOME_ORDER = {'result': ['Win', 'Draw', 'Loss']}
RATING_BINS = ["<1000", "1000-1200", "1200-1400", "1400-1600", "1600-1800", "1800-2000", "2000-2200", "2200+"]
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def _empty(title, message):
    fig = go.Figure()
    fig.update_layout(
        title=title, xaxis_visible=False, yaxis_visible=False, height=320,
        annotations=[dict(text=message, xref='paper', yref='paper', showarrow=False, font=dict(color=COLORS['muted']))],
    )
    return fig


def _rounded(fig):
    """Thin bars with a surface-colored gap between stacked segments."""
    fig.update_traces(marker_line_width=2, marker_line_color=COLORS['surface'], selector=dict(type='bar'))
    return fig


def plot_win_rate_by_color(df):
    if df.empty:
        return None
    data = df.groupby(['user_color', 'result']).size().reset_index(name='games')
    data['user_color'] = data['user_color'].str.title()
    fig = px.bar(data, x='user_color', y='games', color='result', title="Results by Color",
                 color_discrete_map=OUTCOME_COLORS, category_orders=OUTCOME_ORDER,
                 labels={'user_color': '', 'games': 'Games', 'result': ''})
    fig.update_traces(hovertemplate='%{x}: %{y} games<extra>%{fullData.name}</extra>')
    fig.update_layout(bargap=0.55, yaxis_title=None)
    return _rounded(fig)


def plot_rating_trend(df):
    if df.empty:
        return None
    data = df.sort_values('date')
    daily = (data['date'].max() - data['date'].min()).days > 2
    if daily:
        # One point per day (closing rating) reads better than per-game noise over weeks
        data = data.groupby(data['date'].dt.normalize()).agg(user_rating=('user_rating', 'last')).reset_index()
    fig = px.line(data, x='date', y='user_rating', title="Rating Trend", labels={'date': '', 'user_rating': ''},
                  markers=daily)
    fig.update_traces(line=dict(color=COLORS['primary'], width=2, shape='spline', smoothing=0.4),
                      marker=dict(size=6), fill='tozeroy', fillcolor='rgba(124,108,242,0.10)',
                      hovertemplate=('%{x|%b %d}' if daily else '%{x|%b %d, %H:%M}') + '<br><b>%{y}</b><extra></extra>')
    low, high = data['user_rating'].min(), data['user_rating'].max()
    pad = max(20, (high - low) * 0.15)
    fig.update_layout(hovermode='x unified', yaxis_range=[low - pad, high + pad],
                      xaxis_tickformat='%b %d' if daily else '%H:%M')
    return fig


def plot_top_openings(df, n=10):
    if df.empty:
        return None
    top = df['opening_name'].value_counts().head(n).reset_index()
    top.columns = ['opening_name', 'games']
    fig = px.bar(top, x='games', y='opening_name', orientation='h', title=f"Most Played Openings",
                 labels={'opening_name': '', 'games': ''})
    fig.update_traces(marker_color=COLORS['primary'], hovertemplate='%{y}<br><b>%{x} games</b><extra></extra>')
    fig.update_layout(yaxis_categoryorder='total ascending', height=420)
    return _rounded(fig)


def plot_win_rate_by_opening(opening_stats, min_games=5):
    title = f"Win Rate by Opening (≥{min_games} games)"
    if opening_stats.empty:
        return None
    data = opening_stats[opening_stats['games'] >= min_games].head(15).copy()
    if data.empty:
        return _empty(title, f"Not enough games yet<br>(need {min_games}+ games in an opening)")
    data['win_pct'] = data['win_rate'] * 100
    fig = px.bar(data, x='win_pct', y='opening_name', orientation='h', title=title,
                 color='win_rate', color_continuous_scale=[(0, COLORS['Loss']), (0.5, COLORS['border']), (1, COLORS['primary'])],
                 range_color=[0, 1], labels={'opening_name': '', 'win_pct': 'Win rate (%)'},
                 custom_data=['games'], text_auto='.0f')
    fig.update_traces(hovertemplate='%{y}<br><b>%{x:.1f}%</b> over %{customdata[0]} games<extra></extra>',
                      textfont_color=COLORS['text'])
    fig.update_layout(yaxis_categoryorder='total ascending', xaxis_range=[0, 100], coloraxis_showscale=False, height=420)
    return _rounded(fig)


def plot_time_heatmap(df):
    if df.empty:
        return None
    pivot = (df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
             .reindex(index=DAYS, columns=range(24), fill_value=0))
    fig = px.imshow(pivot, title="When You Play", labels=dict(x="Hour of day", y="", color="Games"),
                    color_continuous_scale=[COLORS['surface_2']] + SEQUENTIAL[1:], aspect='auto')
    fig.update_traces(xgap=2, ygap=2, hovertemplate='%{y} %{x}:00<br><b>%{z} games</b><extra></extra>')
    fig.update_layout(coloraxis_showscale=False, xaxis=dict(dtick=3, showgrid=False), yaxis=dict(showgrid=False))
    return fig


def plot_opponent_scatter(df):
    if df.empty:
        return None
    data = df.groupby(['opponent_rating_bin', 'result']).size().reset_index(name='games')
    fig = px.bar(data, x='opponent_rating_bin', y='games', color='result', title="Results by Opponent Rating",
                 category_orders={'opponent_rating_bin': RATING_BINS, **OUTCOME_ORDER},
                 color_discrete_map=OUTCOME_COLORS, labels={'opponent_rating_bin': 'Opponent rating', 'games': 'Games', 'result': ''})
    fig.update_traces(hovertemplate='%{x}: %{y} games<extra>%{fullData.name}</extra>')
    return _rounded(fig)


def plot_termination_pie(df):
    if df.empty:
        return None
    data = df['termination'].fillna('unknown').str.title().value_counts().reset_index()
    data.columns = ['termination', 'games']
    fig = px.pie(data, values='games', names='termination', title="How Games End", hole=0.62)
    fig.update_traces(marker_line_color=COLORS['surface'], marker_line_width=2, texttemplate='%{percent:.0%}',
                      textposition='inside', insidetextorientation='horizontal', sort=True,
                      hovertemplate='%{label}<br><b>%{value} games</b> (%{percent:.0%})<extra></extra>')
    fig.update_layout(uniformtext=dict(minsize=11, mode='hide'),
                      legend=dict(orientation='v', x=1, xanchor='left', y=0.5, yanchor='middle'))
    return fig


def plot_correlation_heatmap(df):
    if df.empty:
        return None
    labels = {'user_rating': 'My rating', 'opponent_rating': 'Opp rating', 'ply_count': 'Game length', 'result_numeric': 'Result'}
    data = df.assign(result_numeric=df['result'].map({'Win': 1, 'Draw': 0.5, 'Loss': 0}))
    data = data[list(labels)].apply(pd.to_numeric, errors='coerce').dropna()
    if data.empty:
        return None
    corr = data.corr().rename(index=labels, columns=labels)
    fig = px.imshow(corr, title="What Moves Together", color_continuous_scale=DIVERGING, zmin=-1, zmax=1, text_auto='.2f')
    fig.update_traces(xgap=2, ygap=2, hovertemplate='%{y} × %{x}<br><b>%{z:.2f}</b><extra></extra>')
    fig.update_layout(coloraxis_showscale=False)
    return fig


def plot_radar_chart(data):
    if not data:
        return None
    categories = data['categories'] + data['categories'][:1]
    values = data['values'] + data['values'][:1]
    fig = go.Figure(go.Scatterpolar(
        r=values, theta=categories, fill='toself', fillcolor='rgba(124,108,242,0.25)',
        line=dict(color=COLORS['primary'], width=2), marker=dict(size=8),
        hovertemplate='%{theta}<br><b>%{r:.1f}/10</b><extra></extra>',
    ))
    fig.update_layout(
        title="Player Personality", showlegend=False, margin=dict(l=70, r=70, t=64, b=40),
        polar=dict(bgcolor='rgba(0,0,0,0)',
                   radialaxis=dict(range=[0, 10], tickvals=[5, 10], gridcolor=COLORS['line'], linecolor='rgba(0,0,0,0)',
                                   tickfont=dict(color=COLORS['muted'], size=10), angle=90, tickangle=90),
                   angularaxis=dict(rotation=90, direction='clockwise', gridcolor=COLORS['line'], linecolor=COLORS['border'],
                                    tickfont=dict(color=COLORS['text_2'], size=12))),
    )
    return fig


def plot_move_time_distribution(raw_times):
    if not raw_times:
        return None
    upper = max(10, float(pd.Series(raw_times).quantile(0.98)))
    fig = px.histogram(x=[t for t in raw_times if t <= upper], title="Time Spent per Move", labels={'x': 'Seconds per move'})
    fig.update_traces(marker_color=COLORS['accent'], marker_line_width=1, marker_line_color=COLORS['surface'],
                      hovertemplate='%{x}s<br><b>%{y} moves</b><extra></extra>')
    fig.update_traces(xbins=dict(start=0, end=upper, size=max(0.5, round(upper / 40, 1))))
    fig.update_layout(xaxis_range=[0, upper], yaxis_title=None, bargap=0.08)
    return fig


def plot_repertoire(df, color, top=6):
    """Top opening families for one color: games played, split into wins / draws / losses."""
    data = df[(df['user_color'] == color) & df['opening_name'].notna()]
    if data.empty:
        return None
    family = data['opening_name'].str.split(':').str[0].str.strip()
    counts = (data.assign(family=family).groupby(['family', 'result']).size()
              .unstack(fill_value=0).reindex(columns=['Win', 'Draw', 'Loss'], fill_value=0))
    counts['games'] = counts.sum(axis=1)
    counts = counts.sort_values('games', ascending=False).head(top).iloc[::-1]  # biggest on top
    win_pct = counts['Win'] / counts['games']

    fig = go.Figure()
    for outcome in ('Win', 'Draw', 'Loss'):
        fig.add_bar(y=counts.index, x=counts[outcome], name=outcome, orientation='h',
                    marker_color=OUTCOME_COLORS[outcome],
                    hovertemplate='%{y}<br>' + outcome + 's: <b>%{x}</b><extra></extra>')
    for fam, total, pct in zip(counts.index, counts['games'], win_pct):
        fig.add_annotation(x=total, y=fam, text=f"<b>{pct:.0%}</b>", xanchor='left', xshift=8, showarrow=False,
                           font=dict(color=COLORS['text'] if pct >= 0.5 else COLORS['muted'], size=12))
    fig.update_layout(title=f"As {color.title()}", barmode='stack', height=90 + 46 * len(counts), legend_traceorder='normal',
                      xaxis=dict(title=None, showgrid=False, showticklabels=False, range=[0, counts['games'].max() * 1.18]),
                      yaxis=dict(title=None, tickfont=dict(color=COLORS['text_2'], size=12)), bargap=0.38)
    return _rounded(fig)
