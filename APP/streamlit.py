import streamlit as st
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from psycopg2.extras import DictCursor
import datetime

#THEME
st.set_page_config(page_title="WE CAN PLAY",layout="centered",page_icon="🎵")
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
    
#SIDEBAR
with st.sidebar:
    #st.image("C:\Users\Samrin\Downloads\Cheerful music note app icon.png",width=180)
    st.image(r"C:\Users\Samrin\Downloads\Cheerful_music_note_app_icon-removebg-preview.png", width=180)
    st.header("Login")
    role = st.selectbox("Select Role", ["listener_free", "listener_premium", "appuser", "adminn"])
    tenant_id = st.text_input("Tenant ID", value="006b1b19-c1bc-489f-902b-f7aa1034b244")
    
    if st.button("🚀 Connect", type="primary"):
        try:
            pw_map = {"appuser":"pass123", "adminn":"admin123", "listener_free":"free123", "listener_premium":"premium456"}
            conn = psycopg2.connect(dbname="backup", user=role, password=pw_map.get(role,""), host="localhost", port="5432")
            conn.autocommit = True
            cur = conn.cursor(cursor_factory=DictCursor)
            cur.execute("SELECT set_config('app.current_tenant', %s, false)", (tenant_id,))
            st.session_state.conn = conn
            st.session_state.cur = cur
            st.session_state.role = role
            st.session_state.tenant_id = tenant_id
            st.success(f"✅ Connected as **{role}**")
        except Exception as e:
            st.error(f"Connection failed: {e}")

if "conn" not in st.session_state:
    st.info("👈 Please login from the sidebar")
    st.stop()

conn = st.session_state.conn
cur = st.session_state.cur
role = st.session_state.role

st.write(f"**Role:** `{role}` | **Tenant:** `{st.session_state.tenant_id[:12]}...`")

#TABS
tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8=st.tabs([
    "Home",
    "🎵Browse",
    "📊Dashboard",
    "🏆 Top Leaderboard",
    "🔍Search",
    "📜 Your History", 
    "🌸 Age Recommendations", 
    "📋 Collaborative Playlists"
])
#TAB1: HOME

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
        cur.execute("SELECT song_id, title, artist, genre, rating, is_premium FROM songs ORDER BY song_id DESC")
        df = pd.DataFrame(cur.fetchall())
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error: {e}")
# Tab 3: Dashboard
# Tab 3: Dashboard (Only for adminn & appuser)
with tab3:
    if role in ["adminn", "appuser"]:
        st.subheader("📊 Music Dashboard")
        
        st.write("### Popular Genres")
        try:
            cur.execute("SELECT * FROM popular_genres()")
            dfg = pd.DataFrame(cur.fetchall(), columns=["Genre", "Song Count", "Avg Rating"])
            st.dataframe(dfg, use_container_width=True)
            fig = px.bar(dfg, x="Genre", y="Song Count", color="Avg Rating", title="Popular Genres")
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("Popular genres data not available yet.")

        st.write("### Popular Artists")
        try:
            cur.execute("SELECT * FROM popular_artists()")
            dfa = pd.DataFrame(cur.fetchall(), columns=["Artist", "Song Count", "Avg Rating"])
            st.dataframe(dfa, use_container_width=True)
        except:
            pass

        st.write("### Song Rating vs Listener Count")
        try:
            cur.execute("SELECT title, rating, listener_count FROM song_listener_stats LIMIT 20")
            dfs = pd.DataFrame(cur.fetchall(), columns=["Title", "Rating", "Listener Count"])
            fig = px.scatter(dfs, x="Rating", y="Listener Count", text="Title", title="Song Popularity", color="Rating")
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("Scatterplot data not available yet.")
    else:
        st.info("Dashboard is visible only to adminn and appuser.")