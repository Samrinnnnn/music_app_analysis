# music_rls_viz.py
# Requirements: pip install psycopg2-binary matplotlib

import psycopg2
import matplotlib.pyplot as plt

# ── SWITCH USER HERE ────────────────────────────────────────────────
# Use "appuser" → restricted by RLS (only sees/inserts own songs)
# Use "admin"   → bypasses RLS (sees and inserts everything)
DB_USER = "appuser"           # ← change to "appuser" to see RLS in action

DB_CONFIG = {
    "dbname":   "appformusic",
    "user":     DB_USER,
    "password": "pass123" if DB_USER == "appuser" else "admin123",
    "host":     "localhost",
    "port":     5432
}

def connect():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"Connected successfully as: {DB_USER}")
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        raise

def add_song(conn, title, artist, genre, rating):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO songs (title, artist, genre, rating)
            VALUES (%s, %s, %s, %s)
        """, (title, artist, genre, rating))
    conn.commit()
    print(f"Added → {title} by {artist} ({genre}) {rating}/5")

def show_my_songs(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT title, artist, genre, rating 
            FROM songs 
            ORDER BY id DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
    
    if not rows:
        print("No songs found.")
        return
    
    print(f"\nShowing songs visible to {DB_USER} ({len(rows)} rows):")
    for row in rows:
        print(f"  • {row[0]:<30} {row[1]:<20} {row[2]:<12} {row[3]}")

def show_avg_per_genre(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM get_avg_rating_per_genre()")
        rows = cur.fetchall()
    
    if not rows:
        print("No data to calculate averages yet.")
        return rows
    
    print(f"\nAverage rating per genre (function result):")
    for genre, avg in rows:
        print(f"  {genre:18} → {avg:.1f}")
    
    return rows

def plot_genre_avg(data):
    if not data:
        return
    
    genres = [row[0] for row in data]
    values = [float(row[1]) for row in data]
    
    plt.figure(figsize=(9, 5))
    bars = plt.bar(genres, values, color='cornflowerblue', edgecolor='navy', width=0.6)
    plt.bar_label(bars, fmt='%.1f')
    
    plt.title(f"Average Song Rating per Genre\n(visible to {DB_USER})", fontsize=14)
    plt.xlabel("Genre")
    plt.ylabel("Average Rating")
    plt.ylim(0, 5.5)
    plt.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    
    filename = f"genre_avg_{DB_USER}.png"
    plt.savefig(filename, dpi=120)
    plt.show()
    print(f"Chart saved as: {filename}\n")

def main():
    conn = None
    try:
        conn = connect()
        # Add some example songs (RLS will decide visibility)
        print("\nAdding example songs...")
        add_song(conn, "Yellow", "Cold Play", "Rock", 5)
        
        
        
        
        # Show visible data
        show_my_songs(conn)
        
        # Use function + visualization
        avg_data = show_avg_per_genre(conn)
        plot_genre_avg(avg_data)
        
        print("\nDone. Try changing DB_USER and run again to see RLS difference.")
        
    except Exception as e:
        print(f"Error during execution: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()