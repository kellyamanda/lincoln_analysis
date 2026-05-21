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
    title='Academic Analysis',
    icon=':material/analytics:',
)
caaspp = st.Page(
    'views/caaspp.py',
    title='CAASPP',
    icon=':material/school:',
)
seda = st.Page(
    'views/seda.py',
    title='SEDA',
    icon=':material/map:',
)
staffing = st.Page(
    'views/staffing.py',
    title='Staffing & Class Size',
    icon=':material/groups:',
)
teachers = st.Page(
    'views/teachers.py',
    title='Teacher Experience',
    icon=':material/co_present:',
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
guide = st.Page(
    'views/guide.py',
    title='How to Read This',
    icon=':material/menu_book:',
)
dashboard = st.Page(
    'views/dashboard.py',
    title='CA Dashboard',
    icon=':material/dashboard:',
)
enrollment = st.Page(
    'views/enrollment.py',
    title='Enrollment & Demographics',
    icon=':material/diversity_3:',
)

# Top nav: empty-string section renders as direct items; named sections become
# collapsible dropdowns. Section labels carry a material icon so the dropdowns
# match the icon styling of the direct pages.
pg = st.navigation(
    {
        '': [overview, analysis, guide],
        ':material/grading: Score Detail': [caaspp, seda],
        ':material/account_balance: Resources & Environment':
            [staffing, teachers, absenteeism, spending, dashboard, enrollment],
    },
    position='top',
)
pg.run()
