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

pg = st.navigation([overview, analysis, caaspp, seda], position='top')
pg.run()
