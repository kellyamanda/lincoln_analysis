import os
import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHOOL_DIR = os.path.join(BASE_DIR, 'school_scores')
SEDA_DIR = os.path.join(BASE_DIR, 'seda_app', 'data')

# Identifiers
SEDA_DISTRICT_ID = '606480'
CAASPP_DISTRICT_CODE = '68882'
LINCOLN_SCHOOL_CODE = '6043566'
BIS_SCHOOL_CODE = '6043525'

BURL_ELEMENTARIES = {
    '6043541': 'Franklin',
    '6043566': 'Lincoln',
    '6043574': 'McKinley',
    '6043590': 'Roosevelt',
    '6043608': 'Washington',
    '0133157': 'Hoover',
}


@st.cache_data(show_spinner=False)
def load_caaspp():
    df = pd.read_parquet(os.path.join(SCHOOL_DIR, 'school_data.parquet'))
    df['Pct Met Above'] = pd.to_numeric(df['Percentage Standard Met and Above'], errors='coerce')
    df['Mean Scale Score'] = pd.to_numeric(df['Mean Scale Score'], errors='coerce')
    df['Students with Scores'] = pd.to_numeric(df['Students with Scores'], errors='coerce')
    return df


@st.cache_data(show_spinner=False)
def load_caaspp_subgroups():
    df = pd.read_parquet(os.path.join(SCHOOL_DIR, 'subgroup_data.parquet'))
    df['Pct Met Above'] = pd.to_numeric(df['Pct Met Above'], errors='coerce')
    df['Students with Scores'] = pd.to_numeric(df.get('Students with Scores', pd.Series(dtype=float)), errors='coerce')
    return df


@st.cache_data(show_spinner=False)
def load_lincoln_full():
    """Lincoln K-5 with %Exceeded extracted from raw CAASPP files."""
    path = os.path.join(SCHOOL_DIR, 'lincoln_full_metrics.parquet')
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def load_bis():
    """Burlingame Intermediate (BIS) grade 6-8 from raw CAASPP files."""
    path = os.path.join(SCHOOL_DIR, 'bis_metrics.parquet')
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def load_seda_trends():
    df = pd.read_parquet(os.path.join(SEDA_DIR, 'trends.parquet'))
    return df


@st.cache_data(show_spinner=False)
def load_seda_cohorts():
    df = pd.read_parquet(os.path.join(SEDA_DIR, 'cohorts.parquet'))
    return df


@st.cache_data(show_spinner=False)
def load_seda_demo():
    df = pd.read_parquet(os.path.join(SEDA_DIR, 'demographics.parquet'))
    return df


@st.cache_data(show_spinner=False)
def load_frpm():
    path = os.path.join(SEDA_DIR, 'burlingame_frpm.csv')
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_staffing():
    """CDE Student/Staff Ratio data for Burlingame schools (enrollment, teacher FTE, ratios)."""
    path = os.path.join(SEDA_DIR, 'burlingame_staffing.parquet')
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def load_absenteeism():
    """CDE chronic absenteeism for Burlingame elementaries, by school/year/subgroup."""
    path = os.path.join(SEDA_DIR, 'burlingame_absenteeism.parquet')
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_parquet(path)


def lincoln_caaspp(df):
    return df[df['is_lincoln']].copy()


def burl_caaspp(df):
    return df[df['District Code'] == CAASPP_DISTRICT_CODE].copy()


def burl_seda_trends(df):
    return df[df['district_id'] == SEDA_DISTRICT_ID].copy()


def burl_seda_cohorts(df):
    return df[df['district_id'] == SEDA_DISTRICT_ID].copy()


def burl_seda_demo(df):
    return df[df['district_id'] == SEDA_DISTRICT_ID].copy()
