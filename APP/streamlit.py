import streamlit as st
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from psycopg2.extras import DictCursor

st.set_page_config(page_title="Nepal Heart Music", layout="wide")

st.markdown("""
<style>
    .main {background-color: #ffffff; color: #1e1e1e;}
    h1, h2, h3 {color: #1e3a8a; font-weight: 700;}
    .stButton>button {background-color: #1e3a8a; color: white; border-radius: 8px;}
    .success {background-color: #d4edda; color: #155724; padding: 12px; border-radius: 8px;}
    .error {background-color: #f8d7da; color: #721c24; padding: 12px; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

st.title("🎵 Nepal Heart Music")
st.markdown("**Music for Every Generation — Kopila, Phool & Basanta**")

# ====================== SIDEBAR LOGIN ======================
with st.sidebar:
    st.header("🔑 Login")
    login_mode = st.radio("Login Type", ["Listener", "Appuser", "Adminn"], horizontal=True)
    
    if login_mode == "Listener":
        username = st.text_input("Username", placeholder="hari, samrin...")
        password = st.text_input("Password", type="password")
        if st.button("Login as Listener", type="primary"):
            try:
                conn = psycopg2.connect(dbname="backup", user="app_login", password="app123", host="localhost", port="5432")
                conn.autocommit = True
                cur = conn.cursor(cursor_factory=DictCursor)
                cur.execute("SELECT user_login(%s, %s)", (username, password))
                result = cur.fetchone()[0]
                if "successful" in result.lower():
                    st.session_state.conn = conn
                    st.session_state.cur = cur
                    st.session_state.username = username
                    st.success(result)
                    st.rerun()
                else:
                    st.error(result)
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
    
    elif login_mode == "Appuser":
        username = "appuser"
        password = st.text_input("Password", value="pass123", type="password")
        tenant_id = st.text_input("Tenant ID", value="006b1b19-c1bc-489f-902b-f7aa1034b244")
        if st.button("Login as Appuser", type="primary"):
            try:
                conn = psycopg2.connect(dbname="backup", user="app_login", password="app123", host="localhost", port="5432")
                conn.autocommit = True
                cur = conn.cursor(cursor_factory=DictCursor)
                cur.execute("SELECT user_login(%s, %s)", (username, password))
                result = cur.fetchone()[0]
                if "successful" in result.lower():
                    cur.execute("SET ROLE appuser")
                    cur.execute("SELECT set_config('app.current_tenant', %s, false)", (tenant_id,))
                    st.session_state.conn = conn
                    st.session_state.cur = cur
                    st.session_state.username = username
                    st.success("Login successful as appuser")
                    st.rerun()
                else:
                    st.error(result)
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
    
    else:  # Adminn
        username = "adminn"
        password = st.text_input("Password", value="admin123", type="password")
        if st.button("Login as Adminn", type="primary"):
            try:
                conn = psycopg2.connect(dbname="backup", user="app_login", password="app123", host="localhost", port="5432")
                conn.autocommit = True
                cur = conn.cursor(cursor_factory=DictCursor)
                cur.execute("SELECT user_login(%s, %s)", (username, password))
                result = cur.fetchone()[0]
                if "successful" in result.lower():
                    cur.execute("SET ROLE adminn")
                    st.session_state.conn = conn
                    st.session_state.cur = cur
                    st.session_state.username = username
                    st.success("Login successful as adminn")
                    st.rerun()
                else:
                    st.error(result)
            except Exception as e:
                st.error(f"Login failed: {str(e)}")

if "conn" not in st.session_state:
    st.info("👈 Please login from the sidebar")
    st.stop()

conn = st.session_state.conn
cur = st.session_state.cur
username = st.session_state.username

st.write(f"**Logged in as:** `{username}`")

# ====================== TABS ======================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏠 Home", "🎵 Browse", "📊 Dashboard", "🔍 Search", 
    "📜 Your History", "🌸 Age Recommendations", "📋 Collaborative Playlists"
])

with tab1:
    st.subheader("This Week's Famous Songs")
    try:
        cur.execute("SELECT * FROM this_week_famous()")
        df = pd.DataFrame(cur.fetchall(), columns=["ID", "Title", "Artist", "Genre", "Rating", "Premium", "Play Count"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    except:
        st.info("No data yet.")

with tab2:
    st.subheader("Browse All Songs")
    try:
        cur.execute("""
            SELECT 
                song_id as "Song ID",
                title as "Title",
                artist as "Artist",
                genre as "Genre",
                rating as "Rating",
                is_premium as "Premium"
            FROM songs 
            ORDER BY song_id DESC
        """)
        df = pd.DataFrame(cur.fetchall())
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error: {e}")

with tab3:
    if username in ["adminn", "appuser"]:
        st.subheader("📊 Music Dashboard")
        try:
            cur.execute("SELECT * FROM popular_genres()")
            dfg = pd.DataFrame(cur.fetchall(), columns=["Genre", "Song Count", "Avg Rating"])
            st.dataframe(dfg, use_container_width=True, hide_index=True)
            
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(dfg["Genre"], dfg["Song Count"], color="#1e3a8a")
            ax.set_title("Popular Genres by Song Count")
            ax.set_xlabel("Genre")
            ax.set_ylabel("Number of Songs")
            plt.xticks(rotation=45)
            st.pyplot(fig)
        except:
            st.info("No data yet.")
    else:
        st.info("Dashboard is for Admin and Appuser only.")