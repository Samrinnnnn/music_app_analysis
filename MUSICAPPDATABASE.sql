--ARTIST TABLE--
CREATE TABLE artists(
artist_id SERIAL PRIMARY KEY,
    artist_name TEXT NOT NULL,
    country TEXT
);
--SONGS TABLE--
CREATE TABLE songs(
song_id SERIAL PRIMARY KEY,
song_title TEXT NOT NULL,
genre TEXT NOT NULL,
is_premium BOOLEAN DEFAULT FALSE, 
distributor TEXT NOT NULL,
release_year INT
);
--MAPPING TABLE--
CREATE TABLE song_artists(
song_id INT REFERENCES songs(song_id),
artist_id INT REFERENCES artists(artist_id)
);
--listen table--
CREATE TABLE IF NOT EXISTS listens (
    listen_id SERIAL PRIMARY KEY,
    song_id INT REFERENCES songs(song_id),
    listener_country TEXT NOT NULL,
    listened_at TIMESTAMP DEFAULT now()
);

--RLS ENABLE--
ALTER TABLE songs ENABLE ROW LEVEL SECURITY;
DROP POLICY songs_rls_policy ON songs;
CREATE POLICY songs_rls_policy
ON songs
USING (
    current_setting('app.user_role') = 'admin'
    OR distributor = current_setting('app.current_distributor')
);
--CRUD FUNCTION--
--1.Artists Insert--
CREATE OR REPLACE FUNCTION add_artist(p_name TEXT,p_country TEXT)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE new_id INT;
BEGIN
   INSERT INTO artists(artist_name, country) VALUES (p_name, p_country)
   RETURNING artist_id INTO new_id;
   RETURN new_id;
   END;
   $$;
   --2.Songs INSERT--
   CREATE OR REPLACE FUNCTION add_song(
   p_title TEXT,
   p_genre TEXT,
   p_is_premium BOOLEAN,
   p_release_year INT
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE new_id INT;
BEGIN
  INSERT INTO songs(song_title,genre,is_premium,distributor,release_year)
  VALUES(p_title,p_genre,p_is_premium,current_setting('app.current_distributor'),p_release_year)
  RETURNING song_id INTO new_id;
  RETURN new_id;
  END;
  $$;
 --3. map songs to artist--
 CREATE OR REPLACE FUNCTION map_song_artist(p_song_id INT, p_artist_id INT)
 RETURNS VOID
 LANGUAGE plpgsql
 AS $$
 BEGIN
  INSERT INTO song_artists(song_id, artist_id) VALUES (p_song_id, p_artist_id);
  END;
  $$;
  --4. Delete Songs--
  CREATE OR REPLACE FUNCTION delete_song(p_song_id INT)
  RETURNS VOID
  LANGUAGE plpgsql
  AS $$
  BEGIN
      DELETE FROM songs WHERE song_id = p_song_id;
	  END;
	  $$;
	  -- 5. Search song/artist--
	  CREATE OR REPLACE FUNCTION search_song_artist(p_text TEXT)
	  RETURNS TABLE (song_title TEXT, artist_name TEXT, genre TEXT)
	  LANGUAGE plpgsql
	  AS $$
	  BEGIN
	   RETURN QUERY
	   SELECT s.song_title, a.artist_name, s.genre
	   FROM songs s
	   JOIN song_artists sa ON s.song_id= sa.song_id
	   JOIN artists a ON sa.artist_id=a.artist_id
	   WHERE s.song_title ILIKE '%' || p_text || '%'
	   OR a.artist_name ILIKE '%' ||p_text|| '%';
	   END;
	   $$;
--ANALYSIS--
--1.Popular genre--
CREATE OR REPLACE FUNCTION popular_genres()
RETURNS TABLE (genre TEXT, total INT)
LANGUAGE plpgsql
AS $$
 BEGIN
  RETURN QUERY
  SELECT s.genre, COUNT(*)
  FROM listens l
  JOIN songs s ON l.song_id = s.song_id
  GROUP BY s.genre
  ORDER BY COUNT(*) DESC;
END;
$$;
  --2.TOP ARTIST--
  CREATE OR REPLACE FUNCTION top_artists()
  RETURNS TABLE (artist_name TEXT, total INT)
  LANGUAGE plpgsql
  AS $$
  BEGIN
   RETURN QUERY
   SELECT a.artist_name, COUNT(*)
   FROM songs s
   JOIN song_artists sa ON s.song_id=sa.song_id
   JOIN artists a ON sa.artist_id=a.artist_id
   GROUP BY a.artist_name
   ORDER BY total DESC;
   END;
   $$;
   --3.FREE VS PREMIUM CONTENT--
   CREATE OR REPLACE FUNCTION content_split()
   RETURNS TABLE (content_type TEXT, total INT)
   LANGUAGE plpgsql
   AS $$
   BEGIN
      RETURN QUERY
	  SELECT CASE WHEN is_premium THEN 'Premium' ELSE 'Free' END, COUNT(*)
	  FROM songs
	  GROUP BY is_premium;
   END;
   $$;
   --4.SONGS Recommendation--
   CREATE OR REPLACE FUNCTION recommend_songs(p_genre TEXT)
RETURNS TABLE(song_title TEXT, artist_name TEXT)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT s.song_title, a.artist_name
  FROM songs s
  JOIN song_artists sa ON s.song_id = sa.song_id
  JOIN artists a ON sa.artist_id = a.artist_id
  WHERE s.genre ILIKE p_genre
    AND (
        s.is_premium = FALSE
        OR current_setting('app.subscription_level') = 'premium'
    )
  ORDER BY s.release_year DESC
  LIMIT 5;
END;
$$;
	  --PERMISSION--
 GRANT SELECT,INSERT, DELETE ON ALL TABLES IN SCHEMA public To app_user;
 GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public To app_user; 
--for avoiding duplication of songs--
ALTER TABLE song_artists
ADD CONSTRAINT uq_song_artist UNIQUE (song_id, artist_id);




 

