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
    # ============ HERO SECTION ============
    st.markdown("## 🌟 Welcome to WE CAN PLAY")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 15px;">
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
                <div style="background: linear-gradient(135deg, #667eea, #764ba2); padding: 20px; border-radius: 15px; text-align: center; color: white;">
                    <div style="font-size: 2em; font-weight: bold;">💎 PREMIUM</div>
                    <div style="font-size: 0.9em;">Unlimited Access</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #4facfe, #00f2fe); padding: 20px; border-radius: 15px; text-align: center; color: white;">
                    <div style="font-size: 2em; font-weight: bold;">🎵 FREE</div>
                    <div style="font-size: 0.9em;">Limited Access</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ============ THIS WEEK'S HOT HITS ============
    st.markdown("## 🔥 This Week's Hot Hits")
    
    try:
        cur.execute("SELECT * FROM this_week_famous()")
        rows = cur.fetchall()
        
        if rows:
            # Create DataFrame with proper column names
            df = pd.DataFrame(rows, columns=["ID", "Title", "Artist", "Genre", "Rating", "Premium", "Plays"])
            
            # Filter songs with plays
            df = df[df['Plays'] > 0]
            
            if not df.empty:
                # Display as cards in 4 columns
                cols = st.columns(4)
                for idx, row in df.head(8).iterrows():
                    with cols[idx % 4]:
                        premium_tag = "💎 PREMIUM" if row['Premium'] else "🎵 FREE"
                        st.markdown(f"""
                        <div style="background: white; border-radius: 15px; padding: 15px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <h4>🎵 {row['Title'][:25]}</h4>
                            <p><b>🎤 {row['Artist']}</b></p>
                            <p>🎸 {row['Genre']}</p>
                            <p>⭐ {row['Rating']}/5.0</p>
                            <p><span style="background: {'linear-gradient(135deg, #f093fb, #f5576c)' if row['Premium'] else 'linear-gradient(135deg, #4facfe, #00f2fe)'}; 
                                              color: white; padding: 3px 8px; border-radius: 20px; font-size: 12px;">
                                {premium_tag}
                            </span></p>
                            <p>📊 {row['Plays']} plays this week</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Show total plays
                st.markdown(f"### 📊 Total Weekly Plays: **{df['Plays'].sum()}**")
                
                # Show as table in expander
                with st.expander("📋 View All Trending Songs"):
                    st.dataframe(df[['Title', 'Artist', 'Genre', 'Rating', 'Plays']], 
                                use_container_width=True, hide_index=True)
            else:
                st.info("📊 No plays yet this week. Start listening to create trends!")
        else:
            st.info("✨ No data yet. Start listening to see trending songs!")
            
    except Exception as e:
        st.error(f"Error: {e}")
        st.info("✨ Start listening to see trending songs!")
    
    st.markdown("---")
    
    # ============ FEATURED GENRES ============
    st.markdown("### 🎵 Popular Genres")
    
    try:
        cur.execute("""
            SELECT genre, COUNT(*) as count, ROUND(AVG(rating), 1) as avg_rating
            FROM songs
            GROUP BY genre
            ORDER BY count DESC
            LIMIT 6
        """)
        genres = cur.fetchall()
        
        if genres:
            genre_cols = st.columns(3)
            for idx, genre_data in enumerate(genres):
                with genre_cols[idx % 3]:
                    genre_name, count, avg_rating = genre_data
                    st.markdown(f"""
                    <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; margin: 5px; text-align: center;">
                        <h4>🎸 {genre_name}</h4>
                        <p>{count} songs</p>
                        <p>⭐ {avg_rating}/5.0</p>
                    </div>
                    """, unsafe_allow_html=True)
    except Exception as e:
        pass
    
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

# ============ TAB 3: DASHBOARD ======================
# ====================== TAB 3: DASHBOARD ======================
with tab3:
    if role in ["admin", "appuser"]:
        st.markdown("## 📊 Analytics Dashboard")
        
        # ============ FIRST: TOP SONGS PER GENRE (DENSE_RANK) ============
        st.markdown("### 🏆 Top Songs Per Genre")
        st.caption("Using DENSE_RANK - Same rating = Same rank | No gaps")
        
        try:
            # Call the DENSE_RANK function
            cur.execute("SELECT * FROM top_songs_per_genre() WHERE rank <= 5")
            top_songs_data = cur.fetchall()
            
            if top_songs_data and len(top_songs_data) > 0:
                # Create DataFrame
                df_top = pd.DataFrame(top_songs_data, columns=["Rank", "Genre", "Title", "Artist", "Rating"])
                
                # Display as simple, clean table
                st.dataframe(
                    df_top[['Rank', 'Genre', 'Title', 'Artist', 'Rating']], 
                    use_container_width=True, 
                    hide_index=True
                )
                
                # Display as simple expandable sections by genre
                st.markdown("### 📂 Browse by Genre")
                for genre in df_top['Genre'].unique():
                    with st.expander(f"🎵 {genre}", expanded=False):
                        genre_df = df_top[df_top['Genre'] == genre]
                        for _, row in genre_df.iterrows():
                            medal = "🥇" if row['Rank'] == 1 else "🥈" if row['Rank'] == 2 else "🥉" if row['Rank'] == 3 else f"#{row['Rank']}"
                            st.write(f"{medal} **{row['Title']}** - {row['Artist']} (⭐ {row['Rating']}/5)")
            else:
                st.info("No songs found")
        except Exception as e:
            st.error(f"Error loading top songs: {e}")
        
        st.markdown("---")
        # ============ END DENSE_RANK SECTION ============
        
        # Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            cur.execute("SELECT COUNT(*) FROM songs")
            total_songs = cur.fetchone()[0]
            col1.metric("Total Songs", total_songs)
        except:
            col1.metric("Total Songs", "N/A")
        
        try:
            cur.execute("SELECT COUNT(*) FROM songs WHERE is_premium = TRUE")
            premium_songs = cur.fetchone()[0]
            col2.metric("Premium Songs", premium_songs)
        except:
            col2.metric("Premium Songs", "N/A")
        
        try:
            cur.execute("SELECT COUNT(DISTINCT artist) FROM songs")
            total_artists = cur.fetchone()[0]
            col3.metric("Unique Artists", total_artists)
        except:
            col3.metric("Unique Artists", "N/A")
        
        try:
            cur.execute("SELECT ROUND(AVG(rating), 1) FROM songs WHERE rating IS NOT NULL")
            avg_rating = cur.fetchone()[0] or 0
            col4.metric("Avg Rating", f"⭐ {avg_rating}")
        except:
            col4.metric("Avg Rating", "N/A")
        
        # Charts Row
        col1, col2 = st.columns(2)
        
        # ============ FIXED: GENRE DISTRIBUTION (Direct Query) ============
        with col1:
            st.markdown("### 🎵 Genre Distribution")
            try:
                # Use direct query instead of function
                cur.execute("""
                    SELECT genre, COUNT(*) as song_count, ROUND(AVG(rating), 2) as avg_rating
                    FROM songs
                    GROUP BY genre
                    ORDER BY song_count DESC
                """)
                genre_data = cur.fetchall()
                
                if genre_data and len(genre_data) > 0:
                    df_genre = pd.DataFrame(genre_data, columns=["Genre", "Song Count", "Avg Rating"])
                    fig = px.bar(df_genre, x="Genre", y="Song Count", 
                                 title="Songs by Genre",
                                 color="Avg Rating", 
                                 color_continuous_scale="Viridis")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No genre data available")
            except Exception as e:
                st.warning(f"Could not load genre chart: {e}")
                # Fallback: Show simple table
                try:
                    cur.execute("SELECT genre, COUNT(*) FROM songs GROUP BY genre")
                    simple_data = cur.fetchall()
                    if simple_data:
                        st.table(pd.DataFrame(simple_data, columns=["Genre", "Count"]))
                except:
                    pass
        
        # ============ FIXED: TOP ARTISTS (Direct Query) ============
        with col2:
            st.markdown("### 🎤 Top Artists")
            try:
                # Use direct query instead of function
                cur.execute("""
                    SELECT artist, COUNT(*) as song_count, ROUND(AVG(rating), 2) as avg_rating
                    FROM songs
                    GROUP BY artist
                    ORDER BY song_count DESC
                    LIMIT 10
                """)
                artist_data = cur.fetchall()
                
                if artist_data and len(artist_data) > 0:
                    df_artist = pd.DataFrame(artist_data, columns=["Artist", "Song Count", "Avg Rating"])
                    fig = px.bar(df_artist, x="Artist", y="Song Count", 
                                 title="Top 10 Artists",
                                 color="Avg Rating", 
                                 color_continuous_scale="Plasma")
                    fig.update_layout(height=400, xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No artist data available")
            except Exception as e:
                st.warning(f"Could not load artist chart: {e}")
                # Fallback: Show simple table
                try:
                    cur.execute("SELECT artist, COUNT(*) FROM songs GROUP BY artist ORDER BY COUNT(*) DESC LIMIT 5")
                    simple_data = cur.fetchall()
                    if simple_data:
                        st.table(pd.DataFrame(simple_data, columns=["Artist", "Song Count"]))
                except:
                    pass
        
        # Premium vs Free Pie Chart
        st.markdown("### 💎 Premium vs Free Songs")
        try:
            cur.execute("SELECT is_premium, COUNT(*) FROM songs GROUP BY is_premium")
            premium_data = cur.fetchall()
            
            if premium_data and len(premium_data) > 0:
                df_premium = pd.DataFrame(premium_data, columns=["Type", "Count"])
                df_premium['Type'] = df_premium['Type'].map({True: 'Premium 💎', False: 'Free 🎵'})
                
                fig = px.pie(df_premium, values="Count", names="Type", 
                             title="Premium vs Free Distribution",
                             color_discrete_sequence=['#764ba2', '#667eea'])
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No premium/free data available")
        except Exception as e:
            st.warning(f"Could not load premium chart: {e}")
        
        # Rating Distribution
        st.markdown("### ⭐ Rating Distribution")
        try:
            cur.execute("SELECT rating FROM songs WHERE rating IS NOT NULL")
            rating_data = cur.fetchall()
            
            if rating_data and len(rating_data) > 0:
                df_rating = pd.DataFrame(rating_data, columns=["Rating"])
                fig = px.histogram(df_rating, x="Rating", 
                                   title="Song Rating Distribution", 
                                   nbins=20, 
                                   color_discrete_sequence=['#667eea'])
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No rating data available")
        except Exception as e:
            st.warning(f"Could not load rating chart: {e}")
            
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

# ====================== TAB 5: HISTORY ======================
with tab5:
    if role == "listener":
        st.subheader("📜 Your Listening Journey")
        
        # ============ HISTORY SECTION ============
        st.markdown("### 🎵 Recent Plays")
        
        try:
            cur.execute("""
                SELECT 
                    s.title as "Title",
                    s.artist as "Artist", 
                    s.genre as "Genre", 
                    s.rating as "Rating",
                    CASE WHEN s.is_premium = true THEN '💎 Premium' ELSE '🎵 Free' END as "Type",
                    ph.played_at as "Played At", 
                    ph.listen_duration as "Duration"
                FROM play_history ph
                JOIN songs s ON ph.song_id = s.song_id
                WHERE ph.user_name = %s
                ORDER BY ph.played_at DESC
                LIMIT 50
            """, (username,))
            
            rows = cur.fetchall()
            
            if rows:
                # Create DataFrame with proper column names
                df_history = pd.DataFrame(rows, columns=[
                    "Title", "Artist", "Genre", "Rating", "Type", "Played At", "Duration"
                ])
                st.dataframe(df_history, use_container_width=True, hide_index=True)
            else:
                st.info("No listening history yet. Start playing some songs!")
                
        except Exception as e:
            st.error(f"Error loading history: {e}")
        
        # ============ STREAK SECTION ============
        st.markdown("---")
        st.markdown("### 🔥 Your Listening Streak")
        
        try:
            cur.execute("SELECT * FROM get_listening_streak(%s)", (username,))
            streak_result = cur.fetchall()
            
            if streak_result:
                df_streak = pd.DataFrame(streak_result, columns=["Date", "Streak Day"])
                current_streak = df_streak.iloc[0]['Streak Day']
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown(f"""
                    <div style="text-align: center; background: #FF6B6B; padding: 20px; border-radius: 15px;">
                        <h1 style="font-size: 3em; margin: 0; color: white;">🔥 {current_streak}</h1>
                        <p style="color: white; margin: 0;">Day Streak!</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                col1.metric("📅 Total Active Days", len(df_streak))
                col2.metric("🏆 Best Streak", df_streak['Streak Day'].max())
            else:
                st.info("✨ Listen today to start your streak!")
        except Exception as e:
            st.warning(f"Streak: {e}")
        
        # ============ RECORD PLAY SECTION ============
        st.markdown("---")
        st.markdown("### 🎮 Quick Play")
        
        col1, col2 = st.columns(2)
        with col1:
            song_id = st.number_input("Song ID", min_value=1, step=1)
        with col2:
            duration = st.number_input("Duration (seconds)", min_value=10, value=180, step=30)
        
        if st.button("▶️ Play Song", type="primary", use_container_width=True):
            try:
                cur.execute("SELECT record_song_play(%s, %s, %s)", (song_id, duration, username))
                result = cur.fetchone()[0]
                conn.commit()
                if "Permission Denied" in result:
                    st.warning(result)
                elif "successfully" in result.lower():
                    st.success(result)
                    st.balloons()
                    st.rerun()
                else:
                    st.info(result)
            except Exception as e:
                st.error(f"Error: {e}")
    
    else:
        st.info("🎵 Listening history is available for listeners only.")
# ====================== TAB 6: RECOMMENDATIONS ======================
# ====================== TAB 6: RECOMMENDATIONS ======================
with tab6:
    if role == "listener":
        st.markdown("## 🎯 Personalized Recommendations")
        
        # Show user's age group info
        try:
            cur.execute("SELECT age, role_type FROM users WHERE user_name = %s", (username,))
            user_data = cur.fetchone()
            if user_data:
                age = user_data[0]
                user_type = user_data[1]
                
                if age:
                    if age <= 25:
                        age_group = "Kopila (Young & Energetic)"
                        age_icon = "🎸"
                    elif age <= 40:
                        age_group = "Phool (Romantic & Mature)"
                        age_icon = "🌹"
                    else:
                        age_group = "Basanta (Classic & Timeless)"
                        age_icon = "🌸"
                    
                    st.info(f"{age_icon} Based on your age ({age}), you're in the **{age_group}** group")
                    
                    if user_type == 'listener_free':
                        st.warning("🎵 Free users see only free songs in recommendations. Upgrade to premium for full access!")
        except Exception as e:
            st.warning(f"Could not load age info: {e}")
        
        # Age-based recommendations button
        st.markdown("### 🌸 Your Personalized Picks")
        
        if st.button("🎵 Get My Recommendations", type="primary", use_container_width=True):
            with st.spinner("Finding the perfect songs for you..."):
                try:
                    # Call the fixed function
                    cur.execute("SELECT * FROM get_age_based_recommendations()")
                    recs = cur.fetchall()
                    
                    if recs:
                        df_recs = pd.DataFrame(recs, columns=["Title", "Artist", "Genre", "Rating", "Premium", "For"])
                        
                        # Display as cards
                        st.markdown("#### 🎵 Recommended for You")
                        
                        cols = st.columns(3)
                        for idx, song in enumerate(df_recs.head(9).itertuples()):
                            with cols[idx % 3]:
                                premium_badge = "💎 PREMIUM" if song.Premium else "🎵 FREE"
                                st.markdown(f"""
                                <div class="song-card">
                                    <h4>🎵 {song.Title[:25]}</h4>
                                    <p><b>🎤 {song.Artist}</b></p>
                                    <p>🎸 {song.Genre}</p>
                                    <p>⭐ {song.Rating}/5.0</p>
                                    <p><span class="{'premium-badge' if song.Premium else 'free-badge'}">{premium_badge}</span></p>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Random song suggestion
                        random_song = random.choice(recs)
                        st.markdown(f"""
                        <div class="info-card" style="text-align: center; margin-top: 20px;">
                            <h3>🎲 Today's Top Pick for You</h3>
                            <h2>🎵 {random_song[0]}</h2>
                            <p>🎤 {random_song[1]} | 🎸 {random_song[2]} | ⭐ {random_song[3]}/5.0</p>
                            <p><i>Based on your age group and listening preferences</i></p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No recommendations available. Try listening to more songs!")
                except Exception as e:
                    st.error(f"Error getting recommendations: {e}")
        
        # Popular genres for you
        st.markdown("### 🔥 Popular Genres")
        try:
            cur.execute("""
                SELECT genre, COUNT(*) as count 
                FROM songs 
                GROUP BY genre 
                ORDER BY count DESC 
                LIMIT 6
            """)
            genres = cur.fetchall()
            if genres:
                df_genres = pd.DataFrame(genres, columns=["Genre", "Count"])
                
                # Create a simple bar chart
                fig = px.bar(df_genres, x="Genre", y="Count", title="Most Popular Genres",
                            color="Count", color_continuous_scale="Viridis")
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.info("Genre insights coming soon")
            
    else:
        st.info("🎯 Personalized recommendations are available for listeners only")

# ====================== TAB 7: PLAYLISTS ======================
with tab7:
    st.markdown("## 📋 Collaborative Playlists")
    
    # Check if user is premium for playlist creation
    is_premium_user = False
    if role == "listener":
        cur.execute("SELECT role_type FROM users WHERE user_name = %s", (username,))
        user_role = cur.fetchone()
        is_premium_user = user_role and user_role[0] == 'listener_premium'
    
    # Create Playlist Section (Premium only)
    if role != "admin" and is_premium_user:
        with st.expander("➕ Create New Playlist", expanded=False):
            playlist_name = st.text_input("Playlist Name", key="new_playlist")
            playlist_desc = st.text_area("Description (optional)", key="playlist_desc")
            is_public = st.checkbox("🌍 Make this playlist public", key="is_public")
            
            # Select songs
            st.markdown("**Add Songs to Your Playlist**")
            cur.execute("SELECT song_id, title, artist FROM songs LIMIT 100")
            available_songs = cur.fetchall()
            
            song_options = [f"{s[1]} - {s[2]} (ID: {s[0]})" for s in available_songs]
            selected_songs = st.multiselect("Select songs", song_options, key="selected_songs")
            
            if st.button("✨ Create Playlist", type="primary", use_container_width=True):
                try:
                    import re
                    song_ids = []
                    for song in selected_songs:
                        match = re.search(r'ID: (\d+)', song)
                        if match:
                            song_ids.append(int(match.group(1)))
                    
                    cur.execute("SELECT create_playlist(%s, %s, %s)", (playlist_name, playlist_desc, song_ids))
                    result = cur.fetchone()[0]
                    
                    if "successfully" in result.lower():
                        # Update public status
                        playlist_id = result.split()[-1]
                        cur.execute("UPDATE playlists SET is_public = %s WHERE name = %s", (is_public, playlist_name))
                        conn.commit()
                        st.success(f"✅ {result}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
                except Exception as e:
                    st.error(f"Failed to create playlist: {e}")
    
    elif role == "listener" and not is_premium_user:
        st.warning("💎 Playlists are available for Premium users only! Upgrade to create and manage playlists.")
    
    # Browse Playlists
    st.markdown("### 📚 Browse Playlists")
    
    try:
        if role == "admin":
            cur.execute("""
                SELECT playlist_id, name, description, created_by, is_public, 
                       array_length(song_ids, 1) as song_count
                FROM playlists 
                ORDER BY created_at DESC
            """)
        elif role == "appuser":
            cur.execute("""
                SELECT playlist_id, name, description, created_by, is_public,
                       array_length(song_ids, 1) as song_count
                FROM playlists 
                WHERE tenant_id = current_setting('app.current_tenant', true)::uuid
                ORDER BY created_at DESC
            """)
        else:  # listener (only premium can see playlists)
            if is_premium_user:
                cur.execute("""
                    SELECT playlist_id, name, description, created_by, is_public,
                           array_length(song_ids, 1) as song_count
                    FROM playlists 
                    WHERE is_public = TRUE OR created_by = current_user
                    ORDER BY is_public DESC, created_at DESC
                """)
            else:
                cur.execute("SELECT * FROM playlists WHERE FALSE")  # No results for free users
        
        playlists = cur.fetchall()
        
        if not playlists:
            if is_premium_user:
                st.info("No playlists yet. Create your first playlist above!")
            elif role == "listener":
                st.info("💎 Premium users can create and view playlists. Upgrade to premium!")
            else:
                st.info("No playlists available")
        else:
            # Display playlists in grid
            cols = st.columns(3)
            for idx, playlist in enumerate(playlists):
                with cols[idx % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div class="song-card">
                            <h3>📀 {playlist[1]}</h3>
                            <p><i>{playlist[2] if playlist[2] else "No description"}</i></p>
                            <p><b>👤 By:</b> {playlist[3]}</p>
                            <p><b>📊 Songs:</b> {playlist[5] or 0}</p>
                            <p><b>{'🌍 Public' if playlist[4] else '🔒 Private'}</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"🎵 View Songs", key=f"view_{playlist[0]}"):
                            st.session_state.selected_playlist = playlist[0]
            
            # Show songs in selected playlist
            if "selected_playlist" in st.session_state:
                st.markdown("---")
                st.markdown("### 🎶 Playlist Songs")
                
                try:
                    cur.execute("""
                        SELECT name, song_ids FROM playlists WHERE playlist_id = %s
                    """, (st.session_state.selected_playlist,))
                    playlist = cur.fetchone()
                    
                    if playlist and playlist[1]:
                        cur.execute("""
                            SELECT song_id, title, artist, genre, rating
                            FROM songs WHERE song_id = ANY(%s)
                        """, (playlist[1],))
                        
                        df_playlist_songs = pd.DataFrame(cur.fetchall(), 
                                                          columns=["ID", "Title", "Artist", "Genre", "Rating"])
                        st.dataframe(df_playlist_songs, use_container_width=True, hide_index=True)
                        
                        if st.button("Close", key="close_playlist"):
                            del st.session_state.selected_playlist
                            st.rerun()
                    else:
                        st.info("This playlist has no songs yet")
                except Exception as e:
                    st.error(f"Error loading songs: {e}")
                    
    except Exception as e:
        st.error(f"Error loading playlists: {e}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 20px;">
    <p>🎵 <b>WE CAN PLAY</b> - Your Music Streaming Platform</p>
    <p style="font-size: 0.8em; color: #666;">Made with ❤️ using Streamlit | © 2024</p>
</div>
""", unsafe_allow_html=True)