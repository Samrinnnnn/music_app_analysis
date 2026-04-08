import streamlit as st
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from psycopg2.extras import DictCursor
import datetime

st.set_page_config(page_title="WE CAN PLAY",layout="wide",page_icon="🎵")
st.markdown("""
<style>
    .main {background-color: #121212; color: #ffffff;}
    h1, h2, h3 {color: #1db954; font-weight: 700;}
    .stButton>button {background-color: #1db954; color: black; border-radius: 30px; font-weight: bold;}
    .card {background-color: #181818; padding: 15px; border-radius: 12px; margin: 10px 0;}
    .success {background-color: #1db954; color: black; padding: 10px; border-radius: 8px;}
    .error {background-color: #ff4d4d; color: white; padding: 10px; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

st.title("🎵 WE CAN PLAY")
st.markdown("**SONG FOR US**")

