"""How to Read This — research-grounded guidance for interpreting the dashboard.

Two questions parents actually ask: (1) Is my child getting a good education? and
(2) Should I push for more funding / donate to the PTA? Both are answered from the
education-research literature, with sources, and tied back to the dashboard's data.
"""
import streamlit as st


st.title(':material/menu_book: How to Read This')
st.caption(
    'The data on the other pages answers "how does Lincoln compare on X?" This page answers the '
    'harder questions underneath: what actually makes a good education, and what (if anything) a '
    'parent should do about funding. Grounded in education research — sources at the bottom of each tab.'
)

tab_quality, tab_funding = st.tabs([
    ':material/insights: Is it a good education?',
    ':material/volunteer_activism: Funding & giving',
])


# ── Tab 1: education quality ──────────────────────────────────────────────────

with tab_quality:
    with st.container(border=True):
        st.markdown(
            '### :material/lightbulb: The one thing to take away\n'
            '**Test-score *levels* and rankings mostly measure family income, not school quality.** '
            'The research-backed measure of a good school is *growth* — how much students learn each '
            'year — and growth is essentially uncorrelated with poverty (Reardon/SEDA, 300M scores). '
            ':material/arrow_forward: **On this dashboard, weight the SEDA growth/trend pages over '
            'CAASPP proficiency levels.**'
        )

    st.markdown('#### :material/fact_check: What the data can and cannot tell you')
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown(
                ':green[:material/check_circle:] **Captured well**\n'
                '- **Growth / learning rate** (SEDA) — the best proxy for what a school *adds*\n'
                '- **Chronic absenteeism** — a real, causal risk to early reading\n'
                '- **Teacher staffing & turnover** — turnover independently hurts achievement\n'
                '- **Achievement gaps** between groups'
            )
    with c2:
        with st.container(border=True):
            st.markdown(
                ':red[:material/cancel:] **Invisible to the data**\n'
                '- Relationships & whether your child feels **known**\n'
                '- **Belonging**, climate, safety (felt, not measured)\n'
                '- Social-emotional development, curriculum quality\n'
                '- Whether *your specific child* is thriving'
            )

    st.markdown('#### :material/checklist: Dimensions of a good education — and how to assess each')
    st.markdown(
        '| Dimension | Why it matters (research) | How *you* assess it |\n'
        '|---|---|---|\n'
        '| **Academic growth** | Growth reflects what the school adds; levels reflect income | SEDA growth pages; ask the teacher how *your* child progressed |\n'
        '| **Teacher quality & stability** | High value-added teachers shape adult earnings & college-going; turnover disrupts | Staffing page + ask about teacher/principal retention |\n'
        '| **Relationships & belonging** | Strongest lever for motivation & self-regulation | Ask your child: *is there an adult here who knows you?* |\n'
        '| **Climate & safety** | Independently predicts achievement & well-being | CA climate surveys; spend 30 min in the building |\n'
        '| **Social-emotional learning** | Predicts behavior, well-being, even earnings | How are conflicts handled — punitively or developmentally? |\n'
        '| **Play / arts / recess** | Support attention & behavior; cutting them backfires | Is recess protected? Are art/music/PE intact? |\n'
        '| **Your child\'s engagement** | The most proximate signal you have | Do they want to go? Talk about ideas? Show curiosity? |\n'
    )

    st.markdown('#### :material/bolt: If you only do five things')
    st.markdown(
        '1. **Read growth, not rankings** — weight SEDA learning-rate trends over CAASPP levels.\n'
        '2. **Ask your child two questions:** *Is there an adult here who knows you?* and *Do you belong?*\n'
        '3. **Check teacher & principal stability** — one of the few structural signals that tracks quality.\n'
        '4. **Spend 30 minutes in the building** — climate is felt, not measured.\n'
        '5. **Watch your child\'s engagement over months** — the outcome all the data is trying to proxy.'
    )

    st.caption(
        ':material/warning: Honest uncertainty: "grit" has weak replication, long-term SEL evidence is '
        'thin, and many effect sizes are small. Treat any single buzzword skeptically.'
    )
    with st.expander(':material/link: Sources'):
        st.markdown(
            '- [The Long-Term Impacts of Teachers (Chetty, Friedman & Rockoff, NBER)](https://www.nber.org/papers/w19424)\n'
            '- [Early test scores do not predict academic growth (Stanford/Reardon, SEDA)](https://ed.stanford.edu/news/students-early-test-scores-do-not-predict-academic-growth-over-time-stanford-research-finds)\n'
            '- [What Do Test Scores Miss? Teacher effects on non-test outcomes (NBER)](https://www.nber.org/system/files/working_papers/w22226/w22226.pdf)\n'
            '- [CASEL: What does the research say?](https://casel.org/fundamentals-of-sel/what-does-the-research-say/)\n'
            '- [School belonging meta-analytic review (Allen et al.)](https://www.tandfonline.com/doi/full/10.1080/02671522.2019.1615116)\n'
            '- [How teacher turnover harms achievement (Ronfeldt et al., Stanford CEPA)](https://cepa.stanford.edu/content/how-teacher-turnover-harms-student-achievement)\n'
            '- [How GreatSchools steers families toward affluent schools (Chalkbeat)](https://www.chalkbeat.org/2019/12/5/21121858/looking-for-a-home-you-ve-seen-greatschools-ratings-here-s-how-they-nudge-families-toward-schools-wi/)'
        )


# ── Tab 2: funding & giving ───────────────────────────────────────────────────

with tab_funding:
    with st.container(border=True):
        st.markdown(
            '### :material/lightbulb: The one thing to take away\n'
            'Lincoln spends below the state average **because California concentrates funding on '
            'high-poverty students (LCFF supplemental/concentration + Title I) and Burlingame is '
            'low-poverty** — the gap is the formula working as designed, not a deficiency. And the '
            'marginal dollar does the *least* at an already high-performing, low-poverty school. '
            ':material/arrow_forward: **If you give, give to the district-wide foundation (BCE), '
            'not the Lincoln-only PTA.**'
        )

    st.markdown('#### :material/payments: Does more money improve outcomes?')
    st.markdown(
        '- **On average, yes** — the modern causal evidence settled the old debate. Jackson & '
        'Mackevicius (2024): a sustained **+\\$1,000/pupil over 4 years ≈ +0.035 SD** test scores, '
        '+1.9pp graduation, +2.7pp college-going.\n'
        '- **But the effect is concentrated in low-income, low-spending districts.** At an affluent, '
        'high-achieving, already-strong school like Lincoln, diminishing returns are real — this is '
        'the *weakest* case for "more money."'
    )

    st.markdown('#### :material/construction: What marginal dollars should buy')
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown(
                ':green[:material/trending_up:] **Strong evidence**\n'
                '- **High-dosage tutoring** (~+0.37 SD) — the single best-evidenced use of money\n'
                '- **Teacher retention & quality** (hard to buy with a check)\n'
                '- **Counselors / support staff** (context-dependent)'
            )
    with c2:
        with st.container(border=True):
            st.markdown(
                ':red[:material/trending_down:] **Weak / cautionary**\n'
                '- **Class-size reduction** — nudging 23→20 is exactly California\'s 1996 reform that '
                'showed *no* test gains\n'
                '- **Enrichment/arts** — valuable for experience, thin achievement evidence'
            )

    st.markdown('#### :material/account_balance: The California mechanics & the equity angle')
    st.markdown(
        '- **LCFF:** every district gets a base grant; *supplemental* (+20%) and *concentration* '
        '(+50%, only above 55% high-need) grants go to low-income/EL/foster students. Burlingame '
        'gets little supplemental and **zero concentration** money — hence below-average spending.\n'
        '- **PTA vs. foundation:** parent fundraising at affluent schools widens between-school '
        'inequality. **But Burlingame\'s BCE foundation already pools ~\\$2.8-3.0M across all 7 schools** '
        '(funding ~20 arts/music/wellness/intervention teachers). A dollar to **BCE is shared '
        'district-wide**; a dollar to the **Lincoln PTA stays at Lincoln**.'
    )

    st.markdown('#### :material/bolt: A decision framework, ranked by leverage')
    st.markdown(
        '1. **Don\'t over-index on the spending gap** — below-average spending coexists with top '
        'outcomes; "catching up to \\$19,450" is not an evidence-based goal here.\n'
        '2. **Give to BCE over the PTA** — same dollar, pooled equitably district-wide, and funds the '
        'categories closest to what works (intervention/support).\n'
        '3. **Champion high-dosage tutoring** — best impact-per-dollar, ideally where need is highest.\n'
        '4. **Parcel-tax / budget advocacy** — durable and equitable, but slow.\n'
        '5. **Non-money levers may be your best return:** home discussion and protecting Lincoln\'s '
        'strong attendance culture outrank marginal school dollars for *your own child\'s* outcomes.'
    )

    with st.expander(':material/link: Sources'):
        st.markdown(
            '- [Jackson & Mackevicius, What Impacts Can We Expect from School Spending? (AEJ: Applied)](https://www.aeaweb.org/articles?id=10.1257%2Fapp.20220279)\n'
            '- [Lafortune, Rothstein & Schanzenbach, School Finance Reform & Achievement](https://www.aeaweb.org/articles?id=10.1257%2Fapp.20160567)\n'
            '- [PPIC, Understanding the Effects of School Funding (2022)](https://www.ppic.org/publication/understanding-the-effects-of-school-funding/)\n'
            '- [Nickow, Oreopoulos & Quinn, The Impressive Effects of Tutoring (NBER)](https://www.nber.org/papers/w27476)\n'
            '- [Brookings, Class Size: What Research Says](https://www.brookings.edu/articles/class-size-what-research-says-and-what-it-means-for-state-policy/)\n'
            '- [CA Dept. of Education, LCFF Overview](https://www.cde.ca.gov/fg/aa/lc/lcffoverview.asp)\n'
            '- [BCE Foundation, School Funding 101](https://www.bcefoundation.org/post/school-funding-101)\n'
            '- [The Nation, The Unequal World of PTA Wealth](https://www.thenation.com/article/society/pta-schools-education/)'
        )
