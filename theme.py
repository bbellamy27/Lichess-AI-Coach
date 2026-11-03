"""Design tokens, global CSS and small HTML building blocks."""
import base64
import html
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

import grades

# --- Tokens ---
# 60-30-10: warm graphite neutrals, raised surfaces, one crimson brand hue (from the logo).
# Highlights use tints of the brand hue (monochromatic), so color always means something.
COLORS = {
    'page': '#111214',
    'surface': '#18191C',
    'surface_2': '#202226',
    'line': '#2A2C31',
    'border': '#363940',
    'text': '#EDEDEF',
    'text_2': '#B4B6BD',
    'muted': '#8A8D95',
    'primary': '#D7261F',
    'primary_hi': '#B81F19',
    'accent': '#FF8A80',
    'tile': 'rgba(215,38,31,.16)',
    # Neutral data colour: red/green are reserved for good/bad judgements
    'data': '#2E9BDB',
    # Outcomes: validated for color-blind separation on the graphite surface
    'Win': '#4ADE80',
    'Loss': '#C93A3A',
    'Draw': '#C3C6CD',
    # Status
    'good': '#4ADE80',
    'warning': '#F2B84B',
    'critical': '#F2716E',
}

SERIES = ['#2E9BDB', '#B87A18', '#8F81F5', '#D8578C']  # validated order; never reuse outcome colors
SEQUENTIAL = ['#18191C', '#173A5C', '#1F5E94', '#2E9BDB', '#A9D4F5']
DIVERGING = [(0, '#2E9BDB'), (0.5, '#2A2C31'), (1, '#D7261F')]
SANS = '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
DISPLAY = '"Plus Jakarta Sans", "Inter", system-ui, -apple-system, "Segoe UI", sans-serif'


# Text/indicator colour for each grade (green good, amber ok, red needs work)
TONE = {grades.GOOD: COLORS['good'], grades.OK: COLORS['warning'], grades.BAD: COLORS['critical'],
        grades.NEUTRAL: COLORS['muted']}


def status_color(score):
    """Map a 0-10 score to a status color."""
    return TONE[grades.score_grade(score)]


# --- Plotly template: every chart inherits this ---
pio.templates['coach'] = go.layout.Template(
    layout=go.Layout(
        font=dict(family=SANS, color=COLORS['text_2'], size=13),
        title=dict(font=dict(family=DISPLAY, size=15, color=COLORS['text']), x=0, xanchor='left', xref='container',
                   y=1, yanchor='top', yref='container', pad=dict(l=20, t=18)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        colorway=SERIES,
        margin=dict(l=20, r=20, t=56, b=16),
        xaxis=dict(gridcolor=COLORS['line'], linecolor=COLORS['border'], zeroline=False, tickfont=dict(color=COLORS['muted'])),
        yaxis=dict(gridcolor=COLORS['line'], linecolor=COLORS['border'], zeroline=False, tickfont=dict(color=COLORS['muted'])),
        legend=dict(orientation='h', yanchor='bottom', y=1.0, xanchor='right', x=1, bgcolor='rgba(0,0,0,0)', title_text=''),
        hoverlabel=dict(bgcolor=COLORS['surface_2'], bordercolor=COLORS['border'], font=dict(family=SANS, color=COLORS['text'])),
        bargap=0.35,
        barcornerradius=4,
    )
)
pio.templates.default = 'plotly_dark+coach'


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');
:root {{
    --page: {COLORS['page']}; --surface: {COLORS['surface']}; --surface-2: {COLORS['surface_2']};
    --line: {COLORS['line']}; --border: {COLORS['border']};
    --text: {COLORS['text']}; --text-2: {COLORS['text_2']}; --muted: {COLORS['muted']};
    --primary: {COLORS['primary']}; --primary-hi: {COLORS['primary_hi']}; --accent: {COLORS['accent']};
    --tile: {COLORS['tile']};
    --radius: 16px; --ease: cubic-bezier(.2,.7,.2,1);
    --sans: {SANS}; --display: {DISPLAY};
}}

html, body, .stApp, [data-testid="stSidebar"], button, input, textarea {{ font-family: var(--sans) !important; }}
.stApp {{
    background:
        radial-gradient(1100px 620px at 100% -10%, rgba(215,38,31,0.16), transparent 62%),
        radial-gradient(1000px 650px at -5% 110%, rgba(15,163,163,0.13), transparent 60%),
                linear-gradient(180deg, #17161F 0%, var(--page) 60%);
    background-attachment: fixed;
}}
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, rgba(215,38,31,0.04), transparent 35%), var(--surface) !important; }}
.block-container {{ padding-top: 2rem; max-width: 1320px; }}
header[data-testid="stHeader"] {{ background: transparent; }}
h1, h2, h3, h4 {{ font-family: var(--display) !important; color: var(--text); letter-spacing: -0.02em; }}

/* Sidebar */
[data-testid="stSidebar"] {{ background: var(--surface); border-right: 1px solid var(--line); }}
[data-testid="stSidebar"] h3 {{
    font-family: var(--sans) !important; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.14em;
    color: var(--muted); font-weight: 600; margin: 1.1rem 0 0.2rem;
}}

/* Metrics as cards */
[data-testid="stMetric"] {{
    background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px 18px;
    transition: border-color .2s var(--ease);
}}
[data-testid="stMetric"]:hover {{ border-color: var(--border); }}
[data-testid="stMetricLabel"] p {{ color: var(--muted); font-size: 0.78rem; font-weight: 500; }}
[data-testid="stMetricValue"] {{ font-family: var(--display); color: var(--text); font-weight: 800; letter-spacing: -0.03em; }}

/* Tabs as a pill bar */
.stTabs [role="tablist"] {{
    gap: 4px; background: var(--surface); padding: 4px; border-radius: 12px; border: 1px solid var(--line);
    width: fit-content; max-width: 100%; overflow-x: auto; box-shadow: none; margin-bottom: 4px;
}}
.stTabs [data-testid="stTab"] {{
    height: 38px; padding: 0 18px; border-radius: 9px; color: var(--muted); background: transparent;
    border: none; box-shadow: none; transition: color .15s var(--ease), background .15s var(--ease);
}}
.stTabs [data-testid="stTab"]:hover {{ color: var(--text); }}
.stTabs [data-testid="stTab"][aria-selected="true"] {{ background: var(--primary); color: #fff; }}
.stTabs [data-testid="stTab"] p {{ font-size: 0.9rem; font-weight: 600; }}

/* Segmented control */
[data-testid="stButtonGroup"] button {{ border-radius: 10px !important; }}

/* Buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stPopover"] button {{
    border-radius: 12px; border: 1px solid var(--border); background: var(--surface-2); font-weight: 600;
    transition: transform .15s var(--ease), border-color .15s var(--ease), background .15s var(--ease);
}}
.stButton > button:hover {{ border-color: var(--accent); transform: translateY(-1px); }}
.stButton > button[kind="primary"] {{
    background: var(--primary); border: none; color: #fff;
    box-shadow: 0 8px 22px -12px rgba(215,38,31,.7);
}}
.stButton > button[kind="primary"]:hover {{ background: var(--primary-hi); }}

/* Inputs, containers, charts */
[data-baseweb="input"], [data-baseweb="select"] > div {{ border-radius: 10px !important; background: var(--page) !important; }}
[data-testid="stExpander"] details {{ border-radius: 12px; border: 1px solid var(--line); background: var(--surface); }}
[data-testid="stAlertContainer"] {{ border-radius: 12px; background: var(--surface); border: 1px solid var(--line); }}
[data-testid="stAlertContentInfo"], [data-testid="stAlertContentInfo"] * {{ color: var(--text-2) !important; }}
[data-testid="stAlertContentInfo"] strong {{ color: var(--accent) !important; }}
[data-testid="stPlotlyChart"] {{
    background: var(--surface); border: none; box-shadow: inset 0 0 0 1px var(--line);
    border-radius: var(--radius); overflow: hidden;
}}
[data-testid="stDataFrame"] {{ border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }}
.card, [data-testid="stMetric"] {{ min-height: 124px; box-sizing: border-box; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: var(--line) !important; border-radius: var(--radius) !important; }}
hr {{ border-color: var(--line) !important; }}

/* --- Components --- */
.hero {{ position: relative; overflow: hidden; padding: 26px 30px; min-height: 150px; box-sizing: border-box; padding-right: 190px; border-radius: 20px; margin-bottom: 18px;
    background: linear-gradient(120deg, rgba(24,25,28,0.96) 45%, rgba(215,38,31,0.14)); border: 1px solid var(--line); }}
.hero .hero-art {{ position: absolute; right: 20px; top: 12px; bottom: 12px; height: calc(100% - 24px);
    aspect-ratio: 1; object-fit: contain; z-index: 0 !important; pointer-events: none;
    filter: drop-shadow(0 6px 18px rgba(0,0,0,.45)); }}
@media (max-width: 640px) {{ .hero .hero-art {{ height: 64px; top: 14px; bottom: auto; right: 14px; }} }}
.hero > * {{ position: relative; z-index: 1; }}
.eyebrow {{ font-size: 0.7rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--accent); font-weight: 700; }}
.hero-title {{ font-family: var(--display); font-size: clamp(1.9rem, 3.6vw, 3rem); font-weight: 800; color: var(--text);
    letter-spacing: -0.025em; margin: 6px 0 2px; line-height: 1.05; }}
.hero-title em {{ font-style: normal; background: linear-gradient(90deg, var(--accent), var(--primary)); -webkit-background-clip: text; background-clip: text; color: transparent; }}
.hero-chips {{ display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }}
.chip {{ font-size: 0.78rem; padding: 5px 11px; border-radius: 999px; color: var(--text-2);
    background: rgba(255,255,255,0.04); border: 1px solid var(--line); }}
.chip b {{ color: var(--text); }}

.section {{ margin: 26px 0 10px; }}
.section-title {{ font-family: var(--display); font-size: 1.2rem; font-weight: 800; color: var(--text); letter-spacing: -0.02em; }}

.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px 18px; height: 100%; }}
.card-label {{ color: var(--muted); font-size: 0.78rem; font-weight: 500; }}
.card-foot {{ color: var(--text-2); font-size: 0.78rem; margin-top: 6px; }}
.card-foot b {{ color: var(--accent); }}

.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(128px, 1fr)); gap: 12px; margin-bottom: 8px; }}
.kpi {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px 18px; min-width: 0; }}
.kpi.wide {{ grid-column: span 2; }}
.kpi-value {{ font-family: var(--display); font-size: 2rem; font-weight: 800; color: var(--text); letter-spacing: -0.03em;
    line-height: 1.15; margin-top: 4px; display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }}
.kpi.wide .kpi-value {{ font-family: var(--sans); font-size: 1rem; font-weight: 700; letter-spacing: 0; line-height: 1.3; }}
.kpi-delta {{ font-family: var(--sans); font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; }}
.kpi-delta.up {{ color: #4ADE80; background: rgba(74,222,128,.14); }}
.kpi-delta.down {{ color: #F2716E; background: rgba(242,113,110,.14); }}
.kpi .card-label {{ display: flex; justify-content: space-between; align-items: center; gap: 6px; }}
.grade-tag {{ font-size: 0.68rem; font-weight: 700; color: var(--tone); padding: 1px 7px; border-radius: 999px;
    background: color-mix(in srgb, var(--tone) 14%, transparent); white-space: nowrap; }}
.grade-legend {{ display: flex; gap: 14px; flex-wrap: wrap; font-size: 0.78rem; color: var(--muted); margin: 2px 0 10px; }}
.kpi-wrap {{ container-type: inline-size; }}
@container (max-width: 760px) {{
    .kpi-grid {{ grid-template-columns: repeat(6, 1fr); }}
    .kpi {{ grid-column: span 2; }}
    .kpi.wide {{ grid-column: span 3; }}
}}
@container (max-width: 440px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .kpi {{ grid-column: span 1; }}
    .kpi.wide {{ grid-column: 1 / -1; }}
    .kpi-value {{ font-size: 1.6rem; }}
}}
/* Smaller screens: slimmer sidebar and gutters so tables keep their columns */
@media (max-width: 1200px) {{
    .block-container {{ padding-left: 1.25rem; padding-right: 1.25rem; }}
    [data-testid="stSidebar"] {{ min-width: 260px !important; max-width: 260px !important; }}
}}
.tile {{ width: 38px; height: 38px; border-radius: 11px; background: var(--tile); color: var(--accent);
    display: grid; place-items: center; flex: none; }}
.tile svg {{ width: 19px; height: 19px; }}

.score-head {{ display: flex; justify-content: space-between; align-items: center; }}
.score-name {{ font-weight: 700; color: var(--text); }}
.score-value {{ font-family: var(--display); font-size: 1.7rem; font-weight: 800; color: var(--text); }}
.score-value small {{ font-size: 0.8rem; color: var(--muted); font-weight: 600; }}
.meter {{ height: 6px; border-radius: 3px; background: var(--surface-2); margin: 10px 0 12px; overflow: hidden; }}
.meter span {{ display: block; height: 100%; background: var(--score); border-radius: 3px; }}
.score-stats {{ display: flex; gap: 16px; font-size: 0.8rem; color: var(--muted); }}
.score-stats b {{ color: var(--text); }}
.score-note {{ font-size: 0.84rem; color: var(--text-2); margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line); }}

.insight {{ display: flex; gap: 12px; align-items: center; padding: 12px 14px; border-radius: 14px;
    background: var(--surface); border: 1px solid var(--line); margin-bottom: 8px; }}
.insight-title {{ font-weight: 700; color: var(--text); font-size: 0.82rem; }}
.insight-body {{ color: var(--text-2); font-size: 0.86rem; margin-top: 1px; }}

.empty {{ text-align: center; padding: 56px 24px 20px; }}
.empty .hero-title {{ font-size: clamp(2.2rem, 4.5vw, 3.6rem); }}
.empty-sub {{ color: var(--text-2); font-size: 1.05rem; margin-top: 10px; }}
.steps {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; margin: 36px auto 0; max-width: 900px;
    border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); text-align: left; }}
.step {{ display: flex; gap: 12px; align-items: center; padding: 18px 20px; }}
.step + .step {{ border-left: 1px solid var(--line); }}
.step-t {{ color: var(--text); font-weight: 700; font-size: 0.92rem; }}
.step-s {{ color: var(--muted); font-size: 0.8rem; }}
@media (max-width: 640px) {{ .hero {{ padding-right: 90px; }} .empty-logo {{ width: 120px; height: 120px; }} }}
@media (max-width: 760px) {{ .steps {{ grid-template-columns: 1fr; }} .step + .step {{ border-left: none; border-top: 1px solid var(--line); }} }}

.brand {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
.brand-mark {{ width: 44px; height: 44px; flex: none; display: grid; place-items: center; }}
.brand-mark img {{ width: 100%; height: 100%; object-fit: contain; }}
.empty-logo {{ width: 168px; height: 168px; object-fit: contain; margin: 0 auto 6px; display: block;
    filter: drop-shadow(0 10px 30px rgba(229,83,75,.25)); }}
.brand-name {{ font-family: var(--display); font-weight: 800; font-size: 1.15rem; color: var(--text); letter-spacing: -0.02em; }}

.st-key-report {{ padding: 8px 12px; }}
.st-key-report h1, .st-key-report h2 {{ font-size: 1.2rem !important; margin-top: 1.2rem; }}
.st-key-report h3, .st-key-report h4 {{ font-size: 1rem !important; }}
.st-key-report p, .st-key-report li {{ color: var(--text-2); line-height: 1.65; }}
.st-key-report strong {{ color: var(--text); }}
.brand-name span {{ color: var(--accent); }}
[data-testid="stChatMessageAvatarUser"] {{ background: var(--surface-2) !important; color: var(--text-2) !important; }}
[data-testid="stChatMessageAvatarAssistant"] {{ background: var(--primary) !important; color: #fff !important; }}
[data-testid="stChatMessage"] {{ background: transparent; }}
.footer {{ color: var(--muted); font-size: 0.72rem; margin-top: 20px; }}
</style>
"""


def chart(fig, where=st):
    """Render a Plotly figure with our template (Streamlit's theme would override it)."""
    if fig is not None:
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        where.plotly_chart(fig, width="stretch", theme=None,
                           config={'displayModeBar': False, 'displaylogo': False})


ASSETS = Path(__file__).parent / "assets"


def _data_uri(name):
    return "data:image/webp;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


LOGO_SMALL = _data_uri("gambit_logo_128.webp")
LOGO_LARGE = _data_uri("gambit_logo.webp")

_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{}</svg>'
ICONS = {
    'load': _ICON.format('<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>'),
    'chart': _ICON.format('<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/>'),
    'spark': _ICON.format('<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>'),
    'risk': _ICON.format('<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>'),
    'pace': _ICON.format('<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2"/><path d="M9 2h6"/>'),
}


def inject_css():
    # Blank lines would end Markdown's HTML block, so drop them
    st.markdown("\n".join(line for line in CSS.splitlines() if line.strip()), unsafe_allow_html=True)


def esc(value):
    return html.escape(str(value))


def plain(text):
    """Drop emoji from generated labels so headings stay clean."""
    return "".join(ch for ch in str(text) if ord(ch) < 0x2190).strip()


def _html(markup):
    # Strip leading whitespace so Markdown never treats lines as code blocks
    st.markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def hero(eyebrow, title, chips=None):
    """Banner; `title` may contain <em> for the gradient highlight."""
    chip_html = "".join(f'<span class="chip">{c}</span>' for c in (chips or []))
    _html(f"""
    <div class="hero">
        <img class="hero-art" src="{LOGO_LARGE}" alt="">
        <div class="eyebrow">{esc(eyebrow)}</div>
        <div class="hero-title">{title}</div>
        {f'<div class="hero-chips">{chip_html}</div>' if chip_html else ''}
    </div>
    """)


def section(title):
    _html(f'<div class="section"><div class="section-title">{esc(title)}</div></div>')


def kpis(items):
    """Responsive KPI grid: wraps onto more rows instead of truncating numbers."""
    cells = []
    for it in items:
        delta = it.get('delta')
        delta_html = ''
        if delta:
            cls = 'up' if delta > 0 else 'down'
            delta_html = f'<span class="kpi-delta {cls}">{"▲" if delta > 0 else "▼"} {abs(delta)}</span>'
        foot = f'<div class="card-foot">{it["foot"]}</div>' if it.get('foot') else ''
        cls = 'kpi wide' if it.get('wide') else 'kpi'
        grade = it.get('grade')
        value_style = f' style="color:{TONE[grade]}"' if grade else ''
        tag = (f'<span class="grade-tag" style="--tone:{TONE[grade]}">{grades.LABELS[grade]}</span>'
               if grade and grade != grades.NEUTRAL else '')
        cells.append(f'<div class="{cls}"><div class="card-label">{esc(it["label"])}{tag}</div>'
                     f'<div class="kpi-value"{value_style}>{esc(it["value"])}{delta_html}</div>{foot}</div>')
    _html(f'<div class="kpi-wrap"><div class="kpi-grid">{"".join(cells)}</div></div>')


def grade_legend(note="Graded against standard chess benchmarks"):
    dots = "".join(f'<span style="color:{TONE[g]};font-weight:600">{grades.LABELS[g]}</span>'
                   for g in (grades.GOOD, grades.OK, grades.BAD))
    _html(f'<div class="grade-legend">{dots}<span>· {esc(note)}</span></div>')


def score_card(name, score, stats, note=None):
    stats_html = "".join(f'<span>{esc(k)} <b>{esc(v)}</b></span>' for k, v in stats.items())
    note_html = f'<div class="score-note">{esc(note)}</div>' if note else ''
    _html(f"""
    <div class="card" style="--score:{status_color(score)}">
        <div class="score-head"><span class="score-name">{esc(name)}</span>
        <span class="score-value">{esc(score)}<small>/10</small></span></div>
        <div class="meter"><span style="width:{max(0, min(10, float(score))) * 10}%"></span></div>
        <div class="score-stats">{stats_html}</div>
        {note_html}
    </div>
    """)


def insight(icon, title, body):
    _html(f'<div class="insight"><div class="tile">{icon}</div><div><div class="insight-title">{esc(title)}</div><div class="insight-body">{esc(body)}</div></div></div>')


def empty_state():
    _html(f"""
    <div class="empty">
        <img class="empty-logo" src="{LOGO_LARGE}" alt="Gambit AI">
        <div class="eyebrow">Gambit AI · personal chess coach</div>
        <div class="hero-title">Know your game<br><em>Fix one thing</em></div>
        <div class="empty-sub">Enter a Lichess username in the sidebar, or see it in action.</div>
    </div>
    """)


def empty_steps():
    _html(f"""
    <div class="empty" style="padding-top: 8px;">
        <div class="steps" style="margin-top: 20px;">
            <div class="step"><div class="tile">{ICONS["load"]}</div><div><div class="step-t">Load games</div><div class="step-s">Any Lichess player</div></div></div>
            <div class="step"><div class="tile">{ICONS["chart"]}</div><div><div class="step-t">See patterns</div><div class="step-s">Openings, pace, accuracy</div></div></div>
            <div class="step"><div class="tile">{ICONS["spark"]}</div><div><div class="step-t">Get a plan</div><div class="step-s">From your AI coach</div></div></div>
        </div>
    </div>
    """)


def brand():
    _html(f'<div class="brand"><div class="brand-mark"><img src="{LOGO_SMALL}" alt=""></div>'
          f'<div class="brand-name">Gambit <span>AI</span></div></div>')
