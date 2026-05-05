--CREATE ROLE--
DO $$ BEGIN
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='appuser')THEN
 CREATE ROLE appuser WITH LOGIN PASSWORD 'pass123';
 END IF;
 END $$;

 DO $$ BEGIN
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='adminn')THEN
 CREATE ROLE adminn WITH LOGIN PASSWORD 'admin123' BYPASSRLS;
 END IF;
 END $$;

 DO $$ BEGIN
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='listener_free') THEN
 CREATE ROLE listener_free WITH LOGIN PASSWORD 'free123' NOSUPERUSER NOCREATEDB NOCREATEROLE;
 END IF;
 END $$;

 DO $$ BEGIN
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='listener_premium') THEN
 CREATE ROLE listener_premium WITH LOGIN PASSWORD 'premium_123' NOSUPERUSER NOCREATEDB NOCREATEROLE;
 END IF;
 END $$;

 --BASIC PERMISSION
 GRANT CONNECT ON DATABASE backup TO appuser,adminn,listener_free,listener_premium;
GRANT USAGE ON SCHEMA public TO appuser,adminn,listener_free,listener_premium;

--TABLE--
 --1.Tenants table
CREATE TABLE tenants (
tenant_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name        VARCHAR(120) NOT NULL,
location    VARCHAR(150) NOT NULL,
created_at  TIMESTAMPTZ  DEFAULT NOW(),
is_active   BOOLEAN DEFAULT TRUE
);

INSERT INTO tenants(name,location) VALUES
('RK Production', 'USA'),
('World SONG', 'UK'),
('Nepal Heart', 'Nepal');

--2.song table
CREATE TABLE songs(
song_id           SERIAL PRIMARY KEY,
title             VARCHAR(150) NOT NULL,
artist            VARCHAR(50) NOT NULL,
genre             VARCHAR(60) NOT NULL,
rating            NUMERIC(3,1) CHECK(rating BETWEEN 0 AND 5 ),
is_premium        BOOLEAN DEFAULT FALSE,
added_by          TEXT NOT NULL DEFAULT current_user,
tenant_id         UUID NOT NULL,
duration_seconds  INTEGER CHECK(duration_seconds>0),
updated_at        TIMESTAMPTZ DEFAULT NOW(),
FOREIGN KEY(tenant_id)
REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
--.TABLE DROP
DROP TABLE IF EXISTS premium_subscription CASCADE;
DROP TABLE IF EXISTS listener_profiles CASCADE;

--3.play_history table
CREATE TABLE play_history(
 history_id         SERIAL PRIMARY KEY,
 user_name          TEXT  NOT NULL,
 song_id            INTEGER NOT NULL,
 played_at          TIMESTAMPTZ DEFAULT NOW(),
 listen_duration    INTEGER CHECK (listen_duration>=0),
 tenant_id          UUID NOT NULL,
FOREIGN KEY(user_name)
REFERENCES users(user_name) ON DELETE CASCADE,
FOREIGN KEY(tenant_id)
REFERENCES tenants (tenant_id) ON DELETE CASCADE
 );

--4.playlist_members
CREATE TABLE IF NOT EXISTS playlist_members(
 playlist_id            UUID NOT NULL,
 user_name              TEXT NOT NULL,
 role                   TEXT CHECK(role IN('owner','editor','viewer')) NOT NULL DEFAULT 'viewer',
 tenant_id              UUID NOT NULL,
 added_at               TIMESTAMPTZ DEFAULT NOW(),
 PRIMARY KEY(playlist_id,user_name),
 FOREIGN KEY(tenant_id)
 REFERENCES tenants(tenant_id) ON DELETE CASCADE
 );

--5.playlists
CREATE TABLE IF NOT EXISTS playlists(
 playlist_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 name                   VARCHAR(100) NOT NULL,
 description            TEXT,
 is_public              BOOLEAN DEFAULT FALSE,
 tenant_id              UUID NOT NULL,
 created_by             TEXT NOT NULL DEFAULT current_user,
 created_at             TIMESTAMPTZ DEFAULT NOW(),
 song_ids               INTEGER[] DEFAULT'{}',
 FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
 );

--6.users
CREATE TABLE users(
 user_name          TEXT PRIMARY KEY,
 full_name          VARCHAR(50) NOT NULL,
 age                INT CHECK (age>=5 AND age<=120),
 password_hash      TEXT NOT NULL,
 role_type          TEXT NOT NULL CHECK(role_type IN ('listener_free','listener_premium')),
 tenant_id          UUID NOT NULL,
 created_at         TIMESTAMPTZ DEFAULT NOW(),
 FOREIGN KEY(tenant_id)
 REFERENCES tenants(tenant_id) ON DELETE CASCADE
 );

-----------------EXTENSION----------
CREATE EXTENSION IF NOT EXISTS pgcrypto;
----------RLS POLICY---
--DROPPING POLICIES
DO $$ 
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT policyname, tablename, schemaname
        FROM pg_policies 
        WHERE schemaname = 'public'
    ) LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', 
                      r.policyname, r.schemaname, r.tablename);
    END LOOP;
END $$;

----CREATING NEW POLICIES AGAIN
--tenants
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
CREATE POLICY admin_manage_tenants ON tenants
 FOR ALL TO adminn USING (true) WITH CHECK (true);

CREATE POLICY no_access_tenants ON tenants
 FOR ALL TO public USING(false);

---------------songs-----------
ALTER TABLE songs ENABLE ROW LEVEL SECURITY;
CREATE POLICY songs_admin_policy ON songs
 FOR ALL TO adminn USING(true) WITH CHECK(true);

CREATE POLICY songs_listener_premium_policy ON songs
 FOR SELECT TO listener_premium USING(true);

CREATE POLICY songs_appuser_policy ON songs
 FOR ALL TO appuser
 USING(tenant_id=current_setting('app.current_tenant',true)::uuid)
 WITH CHECK(tenant_id=current_setting('app.current_tenant',true)::uuid);

CREATE POLICY songs_default_deny ON songs
 FOR ALL TO public USING (false);

CREATE POLICY songs_listener_free_policy ON songs
 FOR SELECT TO listener_free USING(is_premium=false);
------------playlists-----------
ALTER TABLE playlists ENABLE ROW LEVEL SECURITY;
CREATE POLICY playlists_admin_policy ON playlists
FOR ALL TO adminn USING(true) WITH CHECK(true);

CREATE POLICY playlists_appuser_policy ON playlists
 FOR ALL TO appuser
 USING(tenant_id=current_setting('app.current_tenant',true)::uuid)
 WITH CHECK(tenant_id=current_setting('app.current_tenant',true)::uuid);

CREATE POLICY playlists_premium_policy ON playlists
 FOR ALL  TO listener_premium
 USING
 is_public=true
 OR created_by=current_setting('app.current_username',true)
 )
 WITH CHECK(
 created_by=current_setting('app.current_username',true)
 );
CREATE POLICY playlists_free_deny_policy ON playlists
 FOR ALL TO listener_free USING(false) WITH CHECK(false);

CREATE POLICY playlists_default_deny ON playlists
 FOR ALL TO public USING (false);
-----------------playlist_member
ALTER TABLE playlist_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY playlist_members_admin_policy ON playlist_members
 FOR ALL TO adminn USING(true) WITH CHECK (true);

CREATE POLICY playlist_members_appuser_policy ON playlist_members
 FOR ALL TO appuser
 USING(tenant_id=current_setting('app.current_tenant',true)::uuid)
 WITH CHECK(tenant_id=current_setting('app.current_tenant',true)::uuid);

CREATE POLICY playlist_members_premium_policy ON playlist_members
 FOR ALL TO listener_premium
 USING(
 EXISTS(
 SELECT 1 FROM playlists p
 WHERE p.playlist_id=playlist_members.playlist_id
 AND (p.is_public = true OR p.created_by=current_setting('app.current_username',true))
 )
 )
 WITH CHECK(
 EXISTS(
 SELECT 1 FROM playlists p
 WHERE p.playlist_id=playlist_members.playlist_id
 AND p.created_by=current_setting('app.current_username',true))
 );

CREATE POLICY playlist_members_free_deny_policy ON playlist_members
 FOR ALL TO listener_free USING (FALSE) WITH CHECK(FALSE);

CREATE POLICY playlist_members_default_deny ON playlist_members
 FOR ALL TO public USING (false);
---------------------------------------FUNCTION------------------------------------------------------

--1.get_avg_rating_per_genre
CREATE OR REPLACE FUNCTION get_avg_rating_per_genre()
RETURNS TABLE (genre_name VARCHAR, average_rating NUMERIC)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
        SELECT genre, ROUND(AVG(rating), 1)
        FROM songs
        WHERE tenant_id = current_setting('app.current_tenant')::uuid
        GROUP BY genre
        ORDER BY 2 DESC;
END;
$$;
---2.listener genre counts
CREATE OR REPLACE FUNCTION listener_genre_counts()
 RETURNS TABLE(genre_name VARCHAR,song_count BIGINT) AS $$
 SELECT genre,COUNT(*) FROM songs
 WHERE tenant_id=current_setting('app.current_tenant')::uuid
 GROUP BY genre ORDER BY COUNT(*) DESC;
$$ LANGAUGE sql;

--3.add_song--------------------------
CREATE OR REPLACE FUNCTION add_song(
    p_title      VARCHAR(150),
    p_artist     VARCHAR(50),
    p_genre      VARCHAR(60),
    p_rating     NUMERIC(3,1) DEFAULT NULL,
    p_is_premium BOOLEAN DEFAULT FALSE
)
RETURNS TEXT 
LANGUAGE plpgsql 
-- SECURITY DEFINER is removed on purpose
AS $$
DECLARE
    v_tenant_id UUID;
BEGIN
    -- Safely get tenant_id
    v_tenant_id := current_setting('app.current_tenant', true)::UUID;

    IF v_tenant_id IS NULL THEN
        RETURN 'ERROR: Tenant not set. Please call set_config first.';
    END IF;

    -- Insert with correct added_by = current_user (the actual caller)
    INSERT INTO songs (title, artist, genre, rating, is_premium, tenant_id, added_by)
    VALUES (
        p_title, 
        p_artist, 
        p_genre, 
        p_rating, 
        p_is_premium, 
        v_tenant_id, 
        current_user                     -- This will be 'listener_free', 'appuser', etc.
    );

    RETURN 'SUCCESS: Song "' || p_title || '" added by ' || current_user || '.';

EXCEPTION 
    WHEN OTHERS THEN
        RETURN 'ERROR: ' || SQLERRM;
END;
$$;
--------------4.. record_song_play
CREATE OR REPLACE FUNCTION record_song_play(p_song_id integer,p_duration integer DEFAULT NULL)
 RETURNS TEXT AS $$
 DECLARE
    v_is_premium BOOLEAN;
BEGIN 
 SELECT is_premium INTO v_is_premium FROM songs WHERE song_id=p_song_id;
IF current_user='listener_free' AND v_is_premium=TRUE THEN
 RETURN "Permission Denied: Free users can't play premium songs.";
END IF;
INSERT INTO play_history(user_name,song_id,listen_duration,tenant_id)
VALUES(current_user,p_song_id,p_duration,current_setting('app.current_tenant',true)::uuid);
RETURN 'Play recorded successfully.';
EXCEPTION
 WHEN OTHERS THEN
      RETURN 'Error:' || SQLERRM;
END;
$$ LANGUAGE plpgsql;
 
 ----------5.get_age_based_recommendations
CREATE OR REPLACE FUNCTION get_age_based_recommendations()
RETURNS TABLE(
    title VARCHAR,
    artist VARCHAR,
    genre VARCHAR,
    rating NUMERIC,
    is_premium BOOLEAN,
    recommended_for TEXT
) AS $$
DECLARE
    v_age INTEGER;
    v_group TEXT;
BEGIN
    -- Get current logged-in user's age
    SELECT age INTO v_age 
    FROM users 
    WHERE user_name = current_user;

    -- Auto classify age group
    v_group := CASE 
        WHEN v_age IS NULL                    THEN 'all'
        WHEN v_age BETWEEN 5 AND 25           THEN 'kopila'
        WHEN v_age BETWEEN 26 AND 40          THEN 'phool'
        ELSE 'basanta'
    END;

    RETURN QUERY
    SELECT
        s.title,
        s.artist,
        s.genre,
        s.rating,
        s.is_premium,
        CASE 
            WHEN v_group = 'kopila' THEN '🌱 Kopila (Young & Energetic)'
            WHEN v_group = 'phool'  THEN '🌹 Phool (Romantic & Mature)'
            WHEN v_group = 'basanta'THEN '🌳 Basanta (Classic & Timeless)'
            ELSE '🎵 All Ages'
        END AS recommended_for
    FROM songs s
    WHERE s.tenant_id = current_setting('app.current_tenant', true)::uuid
      AND (
            (v_group = 'kopila' AND s.genre IN ('Pop', 'Hip Hop', 'Rock', 'Rap'))
         OR (v_group = 'phool'  AND s.genre IN ('Rock', 'Bollywood', 'Love', 'Indie'))
         OR (v_group = 'basanta'AND s.genre IN ('Classic', 'Folk', 'Country', 'Jazz', 'Ghazal'))
         OR (v_group = 'all')
      )
    ORDER BY s.rating DESC, RANDOM()
    LIMIT 12;
END;
$$ LANGUAGE plpgsql;

--------6."This Week's Famous Songs" based on actual plays"-------------
CREATE OR REPLACE FUNCTION this_week_famous()
 RETURNS TABLE(
   song_id    INT,
   title      VARCHAR,
   artist     VARCHAR,
   genre      VARCHAR,
   rating     NUMERIC,
   is_premium BOOLEAN,
   play_count BIGINT
 ) AS $$
 BEGIN
      RETURN QUERY
      SELECT
            s.song_id,
            s.title,
            s.artist,
            s.genre,
            s.rating,
            s.is_premium,
            COUNT(ph.history_id):: BIGINT AS play_count
 FROM songs s
 LEFT JOIN play_history ph ON s.song_id=ph.song_id
 WHERE s.tenant_id=current_setting('app.current_tenant',true)::uuid
 AND ph.played_at >= NOW() - INTERVAL '7 days'
 GROUP BY s.song_id,s.title,s.artist,s.genre,s.rating,s.is_premium
 ORDER BY play_count DESC, s.rating DESC
 LIMIT 12;
END;
$$ LANGUAGE plpgsql;

-----7.Popular Genres Function
CREATE OR REPLACE FUNCTION popular_genres()
 RETURNS TABLE(
 genre VARCHAR,
 song_count BIGINT,
 avg_rating NUMERIC
 ) AS $$
 BEGIN
  RETURN QUERY
  SELECT 
    s.genre,
 COUNT(*) :: BIGINT AS song_count,
 ROUND(AVG(s.rating),2) AS avg_rating
 FROM songs s
 WHERE s.tenant_id=current_setting('app.current_tenant',true)::uuid
 GROUP BY s.genre
 ORDER BY song_count DESC, avg_rating DESC
 LIMIT 8;
END;
$$ LANGUAGE plpgsql;
-----8. Popular Artists Function
CREATE OR REPLACE FUNCTION popular_artists()
 RETURNS TABLE(
        artist     VARCHAR,
        song_count  BIGINT,
        avg_rating  NUMERIC
 ) AS $$
 BEGIN 
   RETURN QUERY
   SELECT
       s.artist,
       COUNT(*)::BIGINT AS song_count,
       ROUND(AVG(s.rating),2) AS avg_rating
 FROM songs s
 WHERE s.tenant_id=current_setting('app.current_tenant',true)::uuid
 GROUP BY s.artist
 ORDER BY song_count DESC, avg_rating DESC
 LIMIT 8;
END;
$$ LANGUAGE plpgsql;
------9.user_login function
CREATE OR REPLACE FUNCTION user_login(p_username TEXT, p_password TEXT, p_tenant_id UUID DEFAULT NULL)
RETURNS TEXT AS $$
DECLARE 
 v_role_type TEXT;
 v_tenant_id UUID;
BEGIN
 IF p_username='adminn'
 THEN
 SET ROLE adminn;
IF p_tenant_id IS NOT NULL
 THEN PERFORM set_config('app.current_tenant',p_tenant_id::text,false);
END IF;
RETURN 'Login successfully as appuser';
END IF;
-------------LISTENER---------
SELECT role_type,tenant_id INTO v_role_type,v_tenant
 FROM users
 WHERE user_name=p_username
 AND password_hash=p_password;

IF v_role_type IS NULL THEN
 RETURN 'Invalid username or password';
END IF;

EXECUTE format('SET ROLE %I',v_role_type);
PERFORM set_config('app.current_tenant',v_tenant::text,false);

RETURN 'Login successful as' || v_role_type;
END;
$$ LANGUAGE plpgsql;
--10.top_songs
CREATE OR REPLACE FUNCTION top_songs_per_genre()
 RETURNS TABLE(rank BIGINT, genre VARCHAR,title VARCHAR,artist VARCHAR,rating NUMERIC)
 LANGUAGE sql AS $$
 SELECT DENSE_RANK() OVER (PARTITION BY genre ORDER BY rating DESC) AS rank,
 genre,title,artist,rating
 FROM songs
 ORDER BY genre,rank
 $$;
GRANT EXECUTE ON FUNCTION top_songs_per_genre TO adminn,appuser;
--11.get_listening_streak
CREATE OR REPLACE FUNCTION get_listening_streak(p_user_name TEXT)
 RETURNS TABLE(listen_date DATE, streak_number INTEGER) AS $$
 BEGIN
 RETURN QUERY
 WITH RECURSIVE streak AS(
 SELECT MAX(DATE(played_at)) AS dt, 1 as cnt
 FROM play_history WHERE user_name=p_user_name
 UNION ALL
 SELECT s.dt-1,s.cnt + 1
 FROM streak s
 WHERE EXISTS(
 SELECT 1 FROM play_history
 WHERE user_name=p.user_name AND DATE(played_at)=s.dt - 1
 ))
 SELECT dt,cnt FROM streak ORDER BY dt DESC;
END;
$$ LANGUAGE plpgsql;
GRANT EXECUTE ON FUNCTION get_listening_streak(TEXT) TO adminn,appuser,listener_premium,listener_free;
--12.add multiple songs
CREATE OR REPLACE FUNCTION add_multiple_songs(
 p_titles             TEXT[],
 p_artists            TEXT[],
 p_genres             TEXT[],
 p_ratings            NUMERIC[],
 p_is_premium         BOOLEAN[],
 p_durations          INTEGER[]
 )
 RETURNS TEXT AS $$
 DECLARE
 i INTEGER;
v_tenant_id UUID;
v_added INTEGER :=0;
BEGIN
 v_tenant_id:= current_setting('app.current_tenant',true)::UUID;
IF v_tenant_id IS NULL THEN
 RETURN 'ERROR:Tenant not set';
END IF;
FOR i IN 1....array_length(p_titles,1) LOOP
 array_length(p_titles,1)=3
 INSERT INTO songs(title,artist,genre,rating,is_premium,tenant_id,added_by,
 duration_seconds)
 VALUES(p_titles[i],p_artists[i],p_genres[i],p_ratings[i],p_is_premium[i],
 v_tenant_id,current_user,p_durations[i]);
v_added:=v_added + 1;
END LOOP;
RETURN format('Added %s songs',v_added);
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION add_multiple_songs TO appuser,adminn;


REVOKE EXECUTE ON FUNCTION add_song FROM listener_free, listener_premium;
GRANT EXECUTE ON FUNCTION add_song TO appuser, adminn;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO appuser, adminn, listener_free, listener_premium;
GRANT EXECUTE ON FUNCTION record_song_play TO listener_free,listener_premium;
GRANT EXECUTE ON FUNCTION get_age_based_recommendations TO listener_free,listener_premium;
GRANT EXECUTE ON FUNCTION this_week_famous TO listener_free, listener_premium, appuser, adminn;
GRANT EXECUTE ON FUNCTION user_login(TEXT,TEXT,UUID) TO app_login;
GRANT SELECT ON users TO app_login;
GRANT EXECUTE ON ALL FUNCTION IN SCHEMA public TO app_login;
---------------------------------------Index-------------------------------------------------------------
----SONGS TABLE INDEX----
CREATE INDEX idx_songs_tenant_id ON songs(tenant_id);
CREATE INDEX idx_songs_title_search ON songs(title);
CREATE INDEX idx_songs_artist_search ON songs(artist);
CREATE INDEX idx_songs_rating ON songs(rating DESC);
CREATE INDEX idx_songs_premium ON songs(is_premium);
------Playlists Table--------
CREATE INDEX idx_playlists_created_by ON playlists(created_by);
-------Play_history Table---------
CREATE INDEX idx_play_history_song_id ON play_history(song_id);
CREATE INDEX idx_play_history_user_name ON play_history(user_name);
CREATE INDEX idx_play_history_played_at ON play_history(played_at);

SELECT tablename, indexname FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY tablename;
-- This creates the variable for your current session
SELECT set_config('app.current_tenant', '006b1b19-c1bc-489f-902b-f7aa1034b244', false);
SELECT *FROM songs ;

SELECT *
FROM songs
WHERE tenant_id = current_setting('app.current_tenant')::uuid
AND title ILIKE 's%';


ALTER DATABASE backup
SET app.current_tenant = '';
SELECT *
FROM songs
WHERE tenant_id = current_setting('app.current_tenant')::uuid;

-----------------------------LONG RUNNING QUERIES----------------------
SELECT *FROM pg_stat_activity ;
SELECT *FROM pg_stat_activity WHERE state='idle';
SELECT *FROM pg_stat_activity WHERE state='active';
------------------current_timestamp for '5 min'-------------
SELECT current_timestamp-query_start AS  runtime,datname,usename,query FROM pg_stat_activity
WHERE state='active' AND current_timestamp-query_start> '5 mins'
ORDER BY 1 DESC;
-----------------current_timestamp for '30 min'--------------
SELECT current_timestamp-query_start AS runtime,datname,usename,query FROM pg_stat_activity
WHERE state='active' AND current_timestamp-query_start> '30 mins'
ORDER BY 1 DESC;
-----------------------------active state------------
SELECT current_timestamp-query_start AS runtime,datname,usename,query FROM pg_stat_activity
WHERE state='active' 
ORDER BY 1 DESC;
----------------------------pid---------------
SELECT pid,datname,usename,state,query FROM pg_stat_activity;

---------------------------DROP POLICY----------------------------
DROP POLICY IF EXISTS tenants_isolation_songs ON songs;
DROP POLICY IF EXISTS songs_owner ON songs;
DROP POLICY IF EXISTS listener_free_songs ON songs;
DROP POLICY IF EXISTS listener_premium_songs ON songs;

-----------------RESTRICTIVE POLICY FOR tenants_isolation_songs--------------
CREATE POLICY tenants_isolation_songs ON songs
AS RESTRICTIVE
FOR ALL
USING(tenant_id=current_setting('app.current_tenant')::uuid)
WITH CHECK(tenant_id=current_setting('app.current_tenant')::uuid);

CREATE POLICY songs_owner ON songs
FOR ALL
USING(added_by=current_user AND tenant_id=current_setting('app.current_tenant')::uuid)
WITH CHECK(added_by=current_user AND tenant_id=current_setting('app.current_tenant')::uuid);

CREATE POLICY listener_free_songs ON songs
FOR SELECT
USING(current_user='listener_free'
 AND is_premium=FALSE
 AND tenant_id=current_setting('app.current_tenant')::uuid);

CREATE POLICY listener_premium_songs ON songs
FOR SELECT
USING(current_user='listener_premium'
 AND tenant_id=current_setting('app.current_tenant')::uuid);

--------------------VIEW POLICY-------------
 SELECT policyname,permissive,cmd,roles
FROM pg_policies
WHERE tablename= 'songs'
ORDER BY policyname;


------------------------------------------------COLUMN GRANT----------------------------------------------------------

REVOKE ALL ON TABLE songs FROM listener_free;

GRANT SELECT(id,title,artist,genre,rating,is_premium,tenant_id)
ON TABLE songs
TO listener_free;
---------------------------------VIEW-----------------------------------------


CREATE OR REPLACE VIEW dashboard_overview AS
 SELECT 'Total Songs' AS category,COUNT(*)::TEXT AS value FROM songs
 UNION ALL
 SELECT 'Premium Songs' AS COUNT(*)::TEXT FROM songs WHERE is_premium=TRUE
 UNION ALL
 SELECT 'Total User' AS COUNT(*)::TEXT FROM users
 UNION ALL
 SELECT ' Avg Rating', ROUND(AVG(rating), 1)::TEXT FROM songs
UNION ALL
SELECT ' Total Plays', COUNT(*)::TEXT FROM play_history;

SELECT *FROM dashboard_overview;

CREATE OR REPLACE VIEW my_history AS
 SELECT s.title,
 s.artist,
 s.genre,
 s.rating,
 s.is_premium,
 ph.played_at,
 ph.listen_duration
 FROM play_history ph
 JOIN songs s ON ph.song_id=s.song_id
 WHERE ph.user_name=current_setting('app.current_username',true)
 ORDER BY ph.played_at DESC;
--------GRANT PERMISSION---
GRANT SELECT ON my_history TO listener_free,listener_premium;
 
 SELECT set_config('app.current_username', 'Samrin', false);

CREATE OR REPLACE VIEW song_listener_stats AS 
 SELECT s.song_id,s.title,s.artist,s.genre,s.rating,s.is_premium,COUNT(DISTINCT ph.user_name)
 FROM songs s
 LEFT JOIN play_history ph ON s.song_id=ph.song_id
 GROUP BY s.song_id,s.title,s.artist,s.genre,s.rating,s.is_premium;
GRANT SELECT ON song_listener_stats TO listener_premium,appuser,adminn;
---------------------TESTING-----------------------
SET ROLE=listener_free;
SELECT *FROM songs;
SELECT set_config('app.current_tenant','006b1b19-c1bc-489f-902b-f7aa1034b244',FALSE);
SELECT *FROM listener_songs_view;
RESET ROLE;

SET ROLE='listener_premium';
SET ROLE='listener_free';
SELECT set_config('app.current_tenant','006b1b19-c1bc-489f-902b-f7aa1034b244', FALSE);


---------------TEMP TABLE
CREATE TEMP TABLE temp_song_stats AS 
SELECT
song_id,
title,
artist,
genre,
rating,
is_premium
FROM songs;
----------------CHARTS---------------
SELECT genre,COUNT(*) FROM temp_song_stats GROUP BY genre;
SELECT rating,COUNT(*) FROM temp_song_stats GROUP BY rating;
SELECT is_premium, COUNT(*) FROM temp_song_stats GROUP BY is_premium;
SELECT artist, COUNT(*) FROM temp_song_stats GROUP BY artist;
SELECT title,rating FROM temp_song_stats ORDER BY rating DESC;
