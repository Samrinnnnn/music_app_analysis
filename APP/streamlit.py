import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from psycopg2.extras import DictCursor
from datetime import datetime
import random

# Page configuration
st.set_page_config(
    page_title="WE CAN PLAY - Music Streaming",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    /* Main container */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #1e1e1e;
    }
    
    /* Headers */
    h1, h2, h3 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 25px;
        border: none;
        padding: 10px 25px;
        font-weight: 600;
        transition: transform 0.2s;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Success and Error messages */
    .success {
        background-color: #d4edda;
        color: #155724;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
    }
    
    .error {
        background-color: #f8d7da;
        color: #721c24;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
    }
    
    /* Info cards */
    .info-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 10px 0;
        transition: transform 0.3s;
    }
    
    .info-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* Song cards */
    .song-card {
        background: white;
        border-radius: 15px;
        padding: 15px;
        margin: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s;
    }
    
    .song-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Premium badge */
    .premium-badge {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 3px 8px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
    }
    
    .free-badge {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 3px 8px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
    }
    
    /* Metrics */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
    }
    
    .metric-value {
        font-size: 2em;
        font-weight: bold;
    }
    
    .metric-label {
        font-size: 0.9em;
        opacity: 0.9;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 20px;
        padding: 8px 20px;
        background-color: #f0f2f6;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Title with animation
st.markdown("""
<div style="text-align: center; padding: 50px 0 30px 0;">
    <h1 style="font-size: 4em; margin: 0;">🎵 WE CAN PLAY</h1>
    <p style="font-size: 1.2em; color: #666;">Your Music, Your Way | Premium Experience</p>
</div>
""", unsafe_allow_html=True)

# ====================== SIDEBAR LOGIN ======================
with st.sidebar:
    st.markdown("## 🎧 Music Dashboard")
    st.markdown("---")
    
    if not st.session_state.logged_in:
        st.markdown("### 🔑 Login to Continue")
        login_mode = st.radio("Select Account Type", ["🎵 Listener", "💼 Appuser", "👑 Adminn"], horizontal=False)
        
        st.markdown("---")
        
        if login_mode == "🎵 Listener":
            username = st.text_input("Username", placeholder="samrin, hailey, hari...")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            # Show hints for demo users
            if username:
                demo_hints = {
                    "samrin": "💡 Hint: Password is 'mynameiss' (Premium User)",
                    "hailey": "💡 Hint: Password is 'mynameish' (Free User)",
                    "hari": "💡 Hint: Password is 'hari1234' (Free User)",
                    "raghav": "💡 Hint: Password is 'mynameisr' (Free User)",
                    "jim": "💡 Hint: Password is 'jim1234' (Premium User)"
                }
                if username.lower() in demo_hints:
                    st.info(demo_hints[username.lower()])
            
            if st.button("🎵 Login as Listener", use_container_width=True):
                try:
                    conn = psycopg2.connect(
                        dbname="backup", 
                        user="app_login", 
                        password="app123", 
                        host="localhost", 
                        port="5432"
                    )
                    conn.autocommit = True
                    cur = conn.cursor(cursor_factory=DictCursor)
                    
                    # Call login with 2 parameters (listener doesn't need tenant)
                    cur.execute("SELECT user_login(%s, %s)", (username, password))
                    result = cur.fetchone()[0]
                    
                    if "successful" in result.lower():
                        st.session_state.conn = conn
                        st.session_state.cur = cur
                        st.session_state.username = username
                        st.session_state.role = "listener"
                        st.session_state.logged_in = True
                        st.success(f"✨ {result}")
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
                        conn.close()
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")
        
        elif login_mode == "💼 Appuser":
            username = st.text_input("Username", value="appuser", disabled=True)
            password = st.text_input("Password", value="pass123", type="password")
            tenant_id = st.text_input(
                "Tenant ID", 
                value="006b1b19-c1bc-489f-902b-f7aa1034b244",
                help="USA: 006b1b19-c1bc-489f-902b-f7aa1034b244 | Nepal: 9f6ef55d-c9e6-4934-8ab6-d88cd3a8df9d"
            )
            
            if st.button("💼 Login as Appuser", use_container_width=True):
                try:
                    conn = psycopg2.connect(
                        dbname="backup", 
                        user="app_login", 
                        password="app123", 
                        host="localhost", 
                        port="5432"
                    )
                    conn.autocommit = True
                    cur = conn.cursor(cursor_factory=DictCursor)
                    
                    # Call login with 3 parameters (appuser needs tenant)
                    cur.execute("SELECT user_login(%s, %s, %s)", (username, password, tenant_id))
                    result = cur.fetchone()[0]
                    
                    if "successful" in result.lower():
                        st.session_state.conn = conn
                        st.session_state.cur = cur
                        st.session_state.username = username
                        st.session_state.role = "appuser"
                        st.session_state.tenant_id = tenant_id
                        st.session_state.logged_in = True
                        st.success(f"✨ {result}")
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
                        conn.close()
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")
        
        else:  # Adminn
            username = st.text_input("Username", value="adminn", disabled=True)
            password = st.text_input("Password", value="admin123", type="password")
            
            if st.button("👑 Login as Adminn", use_container_width=True):
                try:
                    conn = psycopg2.connect(
                        dbname="backup", 
                        user="app_login", 
                        password="app123", 
                        host="localhost", 
                        port="5432"
                    )
                    conn.autocommit = True
                    cur = conn.cursor(cursor_factory=DictCursor)
                    
                    # Call login with 2 parameters
                    cur.execute("SELECT user_login(%s, %s)", (username, password))
                    result = cur.fetchone()[0]
                    
                    if "successful" in result.lower():
                        st.session_state.conn = conn
                        st.session_state.cur = cur
                        st.session_state.username = username
                        st.session_state.role = "admin"
                        st.session_state.logged_in = True
                        st.success(f"✨ {result}")
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
                        conn.close()
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")
    
    else:
        # Show user info when logged in
        st.markdown(f"""
        <div class="info-card" style="text-align: center;">
            <h3>👋 Welcome, {st.session_state.username}!</h3>
            <p><b>Role:</b> {st.session_state.role.upper()}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            if 'conn' in st.session_state:
                st.session_state.conn.close()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# Check if logged in
if not st.session_state.logged_in:
    st.stop()

# Get database connection
conn = st.session_state.conn
cur = st.session_state.cur
username = st.session_state.username
role = st.session_state.role

# ====================== MAIN CONTENT TABS ======================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏠 Home", "🎵 Browse", "📊 Dashboard", "🔍 Search", 
    "📜 My History", "🎯 Recommendations", "📋 Playlists"
])

# ====================== TAB 1: HOME ======================
with tab1:
    st.markdown("## 🌟 Welcome to WE CAN PLAY")
    
    # Hero section
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        <div class="info-card">
            <h3>🎉 Discover New Music</h3>
            <p>Explore thousands of songs, create playlists, and enjoy personalized recommendations.</p>
            <p>⭐ <b>Premium users</b> get access to all songs and can create collaborative playlists!</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if role == "listener":
            cur.execute("SELECT role_type FROM users WHERE user_name = %s", (username,))
            user_role = cur.fetchone()
            if user_role and user_role[0] == 'listener_premium':
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">💎 PREMIUM</div>
                    <div class="metric-label">Unlimited Access</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">🎵 FREE</div>
                    <div class="metric-label">Limited Access</div>
                </div>
                """, unsafe_allow_html=True)
    
    # This Week's Hot Hits
    st.markdown("## 🔥 This Week's Hot Hits")
    try:
        cur.execute("SELECT * FROM this_week_famous()")
        hot_songs = cur.fetchall()
        if hot_songs:
            df_hot = pd.DataFrame(hot_songs, columns=["ID", "Title", "Artist", "Genre", "Rating", "Premium", "Play Count"])
            
            # Display as cards
            cols = st.columns(4)
            for idx, song in enumerate(df_hot.head(8).itertuples()):
                with cols[idx % 4]:
                    premium_tag = "💎 PREMIUM" if song.Premium else "🎵 FREE"
                    st.markdown(f"""
                    <div class="song-card">
                        <h4>🎵 {song.Title[:20]}</h4>
                        <p><b>🎤 {song.Artist}</b></p>
                        <p>🎸 {song.Genre}</p>
                        <p>⭐ {song.Rating}/5.0</p>
                        <p><span class="{'premium-badge' if song.Premium else 'free-badge'}">{premium_tag}</span></p>
                        <p>📊 {song.Play_Count} plays this week</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No trending songs this week. Start listening to create trends!")
    except Exception as e:
        st.info(f"✨ Feature coming soon: Popular songs will appear here")

# ====================== TAB 2: BROWSE SONGS ======================
with tab2:
    st.markdown("## 🎵 Browse Music Library")
    
    # Filters
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        genre_filter = st.selectbox("Genre", ["All"] + list(pd.read_sql("SELECT DISTINCT genre FROM songs", conn)['genre'].tolist()))
    with col2:
        if role == "listener":
            cur.execute("SELECT role_type FROM users WHERE user_name = %s", (username,))
            is_premium_user = cur.fetchone()[0] == 'listener_premium'
            if not is_premium_user:
                premium_filter = st.selectbox("Access", ["All Free", "Premium Only (Upgrade needed)"])
            else:
                premium_filter = st.selectbox("Access", ["All", "Free Only", "Premium Only"])
        else:
            premium_filter = st.selectbox("Access", ["All", "Free Only", "Premium Only"])
    with col3:
        sort_by = st.selectbox("Sort by", ["Rating (High to Low)", "Rating (Low to High)", "Title A-Z", "Title Z-A"])
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Build query
    query = "SELECT song_id, title, artist, genre, rating, is_premium FROM songs WHERE 1=1"
    
    if genre_filter != "All":
        query += f" AND genre = '{genre_filter}'"
    
    if premium_filter == "Free Only":
        query += " AND is_premium = FALSE"
    elif premium_filter == "Premium Only" and role != "listener":
        query += " AND is_premium = TRUE"
    elif premium_filter == "Premium Only" and role == "listener":
        # Check if user is premium
        cur.execute("SELECT role_type FROM users WHERE user_name = %s", (username,))
        if cur.fetchone()[0] == 'listener_premium':
            query += " AND is_premium = TRUE"
        else:
            st.warning("⚠️ You need a Premium subscription to see premium songs!")
            query += " AND is_premium = FALSE"
    
    if sort_by == "Rating (High to Low)":
        query += " ORDER BY rating DESC NULLS LAST"
    elif sort_by == "Rating (Low to High)":
        query += " ORDER BY rating ASC NULLS LAST"
    elif sort_by == "Title A-Z":
        query += " ORDER BY title"
    else:
        query += " ORDER BY title DESC"
    
    query += " LIMIT 50"
    
    try:
        cur.execute(query)
        songs = cur.fetchall()
        if songs:
            df_songs = pd.DataFrame(songs, columns=["ID", "Title", "Artist", "Genre", "Rating", "Premium"])
            df_songs['Premium'] = df_songs['Premium'].apply(lambda x: '💎 Premium' if x else '🎵 Free')
            st.dataframe(df_songs, use_container_width=True, hide_index=True)
            st.caption(f"📊 Showing {len(songs)} songs")
        else:
            st.info("No songs found with selected filters")
    except Exception as e:
        st.error(f"Error loading songs: {e}")

# ====================== TAB 3: DASHBOARD ======================
with tab3:
    if role in ["admin", "appuser"]:
        st.markdown("## 📊 Analytics Dashboard")
        
        # Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            cur.execute("SELECT COUNT(*) FROM songs")
            total_songs = cur.fetchone()[0]
            col1.metric("Total Songs", total_songs, delta=None)
            
            cur.execute("SELECT COUNT(*) FROM songs WHERE is_premium = TRUE")
            premium_songs = cur.fetchone()[0]
            col2.metric("Premium Songs", premium_songs, delta=f"{premium_songs/total_songs*100:.0f}%")
            
            cur.execute("SELECT COUNT(DISTINCT artist) FROM songs")
            total_artists = cur.fetchone()[0]
            col3.metric("Unique Artists", total_artists)
            
            cur.execute("SELECT ROUND(AVG(rating), 1) FROM songs WHERE rating IS NOT NULL")
            avg_rating = cur.fetchone()[0] or 0
            col4.metric("Avg Rating", f"⭐ {avg_rating}")
        except Exception as e:
            st.warning(f"Could not load metrics: {e}")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                cur.execute("SELECT * FROM popular_genres()")
                df_genre = pd.DataFrame(cur.fetchall(), columns=["Genre", "Count", "Avg Rating"])
                if not df_genre.empty:
                    fig = px.bar(df_genre, x="Genre", y="Count", title="🎵 Genre Distribution", 
                                 color="Avg Rating", color_continuous_scale="Viridis")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Genre chart unavailable")
        
        with col2:
            try:
                cur.execute("SELECT * FROM popular_artists()")
                df_artist = pd.DataFrame(cur.fetchall(), columns=["Artist", "Count", "Avg Rating"])
                if not df_artist.empty:
                    fig = px.bar(df_artist.head(10), x="Artist", y="Count", title="🎤 Top 10 Artists",
                                 color="Avg Rating", color_continuous_scale="Plasma")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Artist chart unavailable")
        
        # Premium vs Free Pie Chart
        try:
            cur.execute("SELECT is_premium, COUNT(*) FROM songs GROUP BY is_premium")
            df_premium = pd.DataFrame(cur.fetchall(), columns=["Type", "Count"])
            df_premium['Type'] = df_premium['Type'].map({True: 'Premium 💎', False: 'Free 🎵'})
            
            fig = px.pie(df_premium, values="Count", names="Type", title="📊 Premium vs Free Songs",
                         color_discrete_sequence=['#764ba2', '#667eea'])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Premium chart unavailable")
        
        # Rating Distribution
        try:
            cur.execute("SELECT rating FROM songs WHERE rating IS NOT NULL")
            df_rating = pd.DataFrame(cur.fetchall(), columns=["Rating"])
            fig = px.histogram(df_rating, x="Rating", title="⭐ Rating Distribution", 
                               nbins=20, color_discrete_sequence=['#667eea'])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Rating chart unavailable")
            
    else:
        st.info("📊 Analytics Dashboard is available for Admin and Appuser only")

# ====================== TAB 4: SEARCH ======================
with tab4:
    st.markdown("## 🔍 Advanced Search")
    
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_term = st.text_input("Search songs, artists, or genres", placeholder="e.g., Love, Ed Sheeran, Pop...")
    with search_col2:
        search_type = st.selectbox("Search in", ["All", "Title", "Artist", "Genre"])
    
    if search_term:
        try:
            if search_type == "Title":
                query = "SELECT title, artist, genre, rating, is_premium FROM songs WHERE title ILIKE %s"
                cur.execute(query, (f"%{search_term}%",))
            elif search_type == "Artist":
                query = "SELECT title, artist, genre, rating, is_premium FROM songs WHERE artist ILIKE %s"
                cur.execute(query, (f"%{search_term}%",))
            elif search_type == "Genre":
                query = "SELECT title, artist, genre, rating, is_premium FROM songs WHERE genre ILIKE %s"
                cur.execute(query, (f"%{search_term}%",))
            else:
                query = "SELECT title, artist, genre, rating, is_premium FROM songs WHERE title ILIKE %s OR artist ILIKE %s OR genre ILIKE %s"
                cur.execute(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            
            results = cur.fetchall()
            if results:
                df_search = pd.DataFrame(results, columns=["Title", "Artist", "Genre", "Rating", "Premium"])
                df_search['Premium'] = df_search['Premium'].apply(lambda x: '💎 Premium' if x else '🎵 Free')
                st.success(f"🎉 Found {len(results)} songs!")
                st.dataframe(df_search, use_container_width=True, hide_index=True)
            else:
                st.info("😔 No songs found. Try different search terms!")
        except Exception as e:
            st.error(f"Search error: {e}")