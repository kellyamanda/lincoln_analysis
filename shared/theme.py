import altair as alt

LINCOLN_COLOR = '#2563EB'
PEER_COLOR = '#10B981'
GRAY = '#9CA3AF'
LIGHT_GRAY = '#E5E7EB'
WARN = '#F59E0B'
DANGER = '#DC2626'

PCT_COLORS = {25: '#F87171', 50: '#9CA3AF', 75: '#6B7280', 90: '#F59E0B', 95: '#10B981'}
GRADE_COLORS = {
    'Grade 3': '#2563EB', 'Grade 4': '#F59E0B', 'Grade 5': '#10B981',
    'Grade 6': '#7C3AED', 'Grade 7': '#0891B2', 'Grade 8': '#DC2626',
}

SUBGROUP_COLORS = {
    'All Students':            '#2563EB',
    'White':                   '#16A34A',
    'Black':                   '#DC2626',
    'Hispanic':                '#D97706',
    'Asian':                   '#7C3AED',
    'Native American':         '#0891B2',
    'Econ. Disadvantaged':     '#B45309',
    'Not Econ. Disadvantaged': '#059669',
    'Female':                  '#DB2777',
    'Male':                    '#1D4ED8',
}


def _brand_theme():
    return {
        'config': {
            'background': '#FFFFFF',
            'title':  {'color': '#111827', 'fontSize': 13, 'fontWeight': 600, 'anchor': 'start'},
            'axis':   {'labelColor': '#6B7280', 'titleColor': '#374151',
                       'gridColor': '#F3F4F6', 'domainColor': '#E5E7EB',
                       'tickColor': '#E5E7EB'},
            'legend': {'labelColor': '#374151', 'titleColor': '#111827',
                       'labelFontSize': 11, 'titleFontSize': 11},
            'view':   {'stroke': 'transparent'},
        }
    }


def register_brand_theme():
    try:
        alt.themes.register('lincoln_brand', _brand_theme)
        alt.themes.enable('lincoln_brand')
    except Exception:
        pass


def configure(chart):
    return chart.configure_axis(labelFontSize=11, titleFontSize=12).configure_title(fontSize=13)


PAGE_CSS = """
<style>
  /* ---- Page chrome & title spacing ----------------------------------- */
  /* Push page content below the top nav so st.title isn't clipped */
  .block-container {
    padding-top: 4rem !important;
    padding-bottom: 2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px !important;
  }
  /* Top nav: opaque white background so it doesn't bleed scrolling content through */
  [data-testid="stHeader"],
  header[data-testid="stHeader"] {
    background: #FFFFFF !important;
    border-bottom: 1px solid #E5E7EB !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    backdrop-filter: none !important;
    z-index: 999 !important;
  }
  /* The actual nav links container — push them in to match content padding */
  [data-testid="stTopNav"],
  div[data-testid="stTopNav"] > div,
  nav[role="navigation"] {
    background: #FFFFFF !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
  }

  /* ---- Metric / hr polish -------------------------------------------- */
  [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; }
  [data-testid="stMetricLabel"] { font-size: 0.78rem !important; color: #6B7280 !important; }
  hr { border-color: #E5E7EB; margin: 1rem 0 1.5rem 0; }

  /* ---- Tabs (pages tab nav AND st.tabs) ------------------------------ */
  .stTabs [data-baseweb="tab-panel"] { padding-top: 1rem !important; }
  /* Only the indicator under the SELECTED tab is blue.
     The full bar beneath all tabs stays the default light gray. */
  .stTabs [data-baseweb="tab-highlight"] {
    background-color: #2563EB !important;
  }
  .stTabs [aria-selected="true"] {
    color: #2563EB !important;
  }
  .stTabs [data-baseweb="tab"]:hover {
    color: #2563EB !important;
  }
  /* Top-position navigation: highlight underline + selected/hover text */
  [data-testid="stTopNav"] [aria-selected="true"],
  [data-testid="stTopNav"] a[aria-current="page"] {
    color: #2563EB !important;
    border-color: #2563EB !important;
  }
  [data-testid="stTopNav"] a:hover {
    color: #2563EB !important;
  }

  /* ---- Pills (st.pills) ---------------------------------------------- */
  [data-testid="stPills"] button[aria-pressed="true"],
  [data-testid="stPills"] button[data-selected="true"] {
    background-color: #2563EB !important;
    border-color: #2563EB !important;
    color: white !important;
  }
  [data-testid="stPills"] button:hover {
    border-color: #2563EB !important;
    color: #2563EB !important;
  }
  [data-testid="stPills"] button[aria-pressed="true"]:hover,
  [data-testid="stPills"] button[data-selected="true"]:hover {
    color: white !important;
    background-color: #1D4ED8 !important;
  }

  /* ---- Segmented control --------------------------------------------- */
  [data-testid="stSegmentedControl"] button[aria-pressed="true"],
  [data-testid="stSegmentedControl"] button[data-selected="true"] {
    background-color: #2563EB !important;
    color: white !important;
  }
  [data-testid="stSegmentedControl"] button:hover {
    color: #2563EB !important;
  }
  [data-testid="stSegmentedControl"] button[aria-pressed="true"]:hover {
    color: white !important;
    background-color: #1D4ED8 !important;
  }

  /* ---- Buttons / links / focus rings --------------------------------- */
  .stButton > button:focus,
  .stButton > button:hover {
    border-color: #2563EB !important;
    color: #2563EB !important;
  }
  a, a:visited { color: #2563EB; }
  a:hover { color: #1D4ED8; }
</style>
"""
