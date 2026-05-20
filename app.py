import streamlit as st

from shared.theme import PAGE_CSS, register_brand_theme

st.set_page_config(
    page_title='Lincoln Elementary — Burlingame Analytics',
    page_icon=':material/analytics:',
    layout='wide',
    initial_sidebar_state='collapsed',
)

st.html(PAGE_CSS)
register_brand_theme()


overview = st.Page(
    'views/overview.py',
    title='Lincoln Overview',
    icon=':material/insights:',
    default=True,
)
analysis = st.Page(
    'views/analysis.py',
    title='Lincoln Analysis',
    icon=':material/analytics:',
)
caaspp = st.Page(
    'views/caaspp.py',
    title='Lincoln CAASPP Deep Dive',
    icon=':material/school:',
)
seda = st.Page(
    'views/seda.py',
    title='District SEDA Deep Dive',
    icon=':material/map:',
)
staffing = st.Page(
    'views/staffing.py',
    title='Staffing & Class Size',
    icon=':material/groups:',
)
absenteeism = st.Page(
    'views/absenteeism.py',
    title='Chronic Absenteeism',
    icon=':material/event_busy:',
)
spending = st.Page(
    'views/spending.py',
    title='Per-Pupil Spending',
    icon=':material/payments:',
)

pg = st.navigation([overview, analysis, caaspp, seda, staffing, absenteeism, spending], position='top')
pg.run()
