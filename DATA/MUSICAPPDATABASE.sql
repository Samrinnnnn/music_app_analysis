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
song_id  SERIAL PRIMARY KEY,
title    VARCHAR(150) NOT NULL,
artist   VARCHAR(50) NOT NULL,
genre    VARCHAR(60) NOT NULL,
rating   NUMERIC(3,1) CHECK(rating BETWEEN 0 AND 5 ),
is_premium BOOLEAN DEFAULT FALSE,
added_by  TEXT NOT NULL DEFAULT current_user,
tenant_id  UUID NOT NULL,
FOREIGN KEY(tenant_id)
REFERENCES tenants(tenant_id)
);
--3.listener profiles table
CREATE TABLE listener_profiles(
user_name     TEXT PRIMARY KEY ,
full_name     VARCHAR(50) NOT NULL,
address       VARCHAR(150) NOT NULL,
updated_at    TIMESTAMPTZ DEFAULT NOW(),
tenant_id     UUID NOT NULL,
FOREIGN KEY(tenant_id)
REFERENCES tenants(tenant_id)
);
--4.premium subscription table
CREATE TABLE premium_subscription(
user_name    TEXT,
amount       NUMERIC(10,2) DEFAULT 99.99,
payment_status  TEXT DEFAULT'completed',
subscribed_at  TIMESTAMPTZ DEFAULT NOW(),
expired_at     TIMESTAMPTZ,
added_by       TEXT DEFAULT current_user,
tenant_id      UUID NOT NULL,
FOREIGN KEY(user_name)
REFERENCES listener_profiles(user_name),
FOREIGN KEY(tenant_id)
REFERENCES tenants(tenant_id)
);
--5.play_history table
CREATE TABLE play_history(
 history_id         SERIAL PRIMARY KEY,
 user_name          TEXT  NOT NULL,
 song_id            INTEGER NOT NULL,
 played_at          TIMESTAMPTZ DEFAULT NOW(),
 listen_duration    INTEGER CHECK (listen_duration>=0),
 tenant_id          UUID NOT NULL,
FOREIGN KEY(user_name)
REFERENCES listener_profiles(user_name) ON DELETE CASCADE,
FOREIGN KEY(song_id)
REFERENCES songs (song_id) ON DELETE CASCADE,
FOREIGN KEY(tenant_id)
REFERENCES tenants (tenant_id) ON DELETE CASCADE
 );
 
----------RLS POLICY---
--TENANTS--
SELECT *FROM tenants;
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
CREATE POLICY admin_manage_tenants ON tenants
FOR ALL USING (current_user ='adminn') WITH CHECK (current_user ='adminn');

GRANT ALL ON tenants to adminn;

--SONGS--
ALTER TABLE songs ENABLE ROW LEVEL SECURITY;
--1.ISOLATION POLICY--
CREATE POLICY tenants_isolation_songs ON songs FOR ALL
USING (tenant_id=current_setting('app.current_tenant')::uuid)
WITH CHECK(tenant_id=current_setting('app.current_tenant')::uuid);
--2.owner's rules
CREATE POLICY songs_owner ON songs FOR ALL
USING(added_by= current_user AND tenant_id = current_setting('app.current_tenant')::uuid)
WITH CHECK(added_by= current_user AND tenant_id =current_setting('app.current_tenant')::uuid);
--3.Listener's rules
CREATE POLICY listener_free_songs ON songs FOR SELECT
USING(current_user='listener_free' AND is_premium=FALSE AND tenant_id=current_setting('app.current_tenant')::uuid );
CREATE POLICY listener_premium_songs ON songs FOR SELECT
USING(current_user ='listener_premium' AND  tenant_id=current_setting('app.current_tenant')::uuid);
-----------------------GRANT----------------------------------------
GRANT SELECT,INSERT,UPDATE ON songs TO appuser;
GRANT USAGE, SELECT ON SEQUENCE songs_song_id_seq TO appuser;
GRANT ALL ON songs TO adminn;
GRANT ALL ON SEQUENCE songs_song_id_seq TO adminn;
GRANT SELECT ON songs TO listener_free,listener_premium;
--LISTENER PROFILES--
ALTER TABLE listener_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_listener_profiles ON listener_profiles FOR ALL
USING (tenant_id=current_setting('app.current_tenant')::uuid)
WITH CHECK(tenant_id=current_setting('app.current_tenant')::uuid);

CREATE POLICY own_profile ON listener_profiles FOR ALL
USING (user_name =current_user AND tenant_id=current_setting('app.current_tenant')::uuid)
WITH CHECK(user_name=current_user AND tenant_id=current_setting('app.current_tenant')::uuid);
-------------------GRANT---------
GRANT SELECT,INSERT,UPDATE ON listener_profiles TO listener_free,listener_premium;
------PREMIUM SUBSCRIPTION------
ALTER TABLE premium_subscription ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_subscription ON premium_subscription FOR ALL
USING(tenant_id=current_setting('app.current_tenant')::uuid)
WITH CHECK(tenant_id=current_setting('app.current_tenant')::uuid);

CREATE POLICY own_tenant_subscription ON premium_subscription FOR ALL
USING(user_name= current_user AND tenant_id=current_setting('app.current_tenant')::uuid)
WITH CHECK(user_name=current_user AND tenant_id=current_setting('app.current_tenant')::uuid);
---------------GRANT---------------------------
GRANT SELECT, INSERT, UPDATE ON premium_subscription TO listener_free,listener_premium;

---------------------------------------FUNCTION------------------------------------------------------
--1.set_app_current_tenant
CREATE OR REPLACE FUNCTION set_app_current_tenant(p_tenant_id UUID)
RETURNS VOID 
LANGUAGE sql
AS $$
SELECT set_config('app.current_tenant', p_tenant_id::text,true);
$$;

GRANT EXECUTE ON FUNCTION set_app_current_tenant(UUID)
TO appuser,adminn,listener_free,listener_premium;
--2.get_avg_rating_per_genre
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
---3.listener genre counts
CREATE OR REPLACE FUNCTION listener_genre_counts()
RETURNS TABLE(genre_name VARCHAR,song_count BIGINT )
LANGUAGE sql SECURITY DEFINER 
AS $$
SELECT genre,COUNT(*)
FROM songs
WHERE tenant_id=current_setting('app.current_tenant')::uuid
GROUP BY genre HAVING COUNT(*) >0
ORDER BY COUNT(*) DESC;
$$;
----4.premium_recommendation
CREATE OR REPLACE FUNCTION premium_recommendation(limit_count INT DEFAULT 6)
RETURNS TABLE(title VARCHAR,artist VARCHAR, genre VARCHAR, rating NUMERIC, is_premium BOOLEAN)
LANGUAGE SQL SECURITY DEFINER
AS $$
SELECT title,artist,genre,rating, is_premium
FROM songs
where is_premium=TRUE
AND rating IS NOT NULL
AND tenant_id=current_setting('app.current_tenant')::uuid
ORDER BY rating DESC, RANDOM()
LIMIT limit_count;
$$;
--5.get_listener_profiles
CREATE OR REPLACE FUNCTION get_listener_profiles()
RETURNS TABLE (full_name VARCHAR(100), address TEXT)
LANGUAGE sql AS $$
    SELECT full_name, address
    FROM listener_profiles
    WHERE user_name = current_user
      AND tenant_id = current_setting('app.current_tenant')::uuid;
$$;
--6.update_listener_profile
CREATE OR REPLACE FUNCTION update_listener_profile(
    p_full_name VARCHAR(100),
    p_address   TEXT
)
RETURNS TEXT LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO listener_profiles (user_name, full_name, address, tenant_id)
    VALUES (current_user, p_full_name, p_address, current_setting('app.current_tenant')::uuid)
    ON CONFLICT (user_name) DO UPDATE SET
        full_name  = EXCLUDED.full_name,
        address    = EXCLUDED.address,
        updated_at = NOW();

    RETURN 'Profile updated successfully.';
EXCEPTION WHEN OTHERS THEN
    RETURN 'Error: ' || SQLERRM;
END;
$$;
--7.subscribe_to_premium
CREATE OR REPLACE FUNCTION subscribe_to_premium()
RETURNS TEXT LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO premium_subscriptions (user_name, tenant_id)
    VALUES (current_user, current_setting('app.current_tenant')::uuid)
    ON CONFLICT (user_name) DO UPDATE SET
        subscribed_at   = NOW(),
        payment_status  = 'completed';

    RETURN 'Premium subscription successful! (simulated)';
EXCEPTION WHEN OTHERS THEN
    RETURN 'Error: ' || SQLERRM;
END;
$$;
--8.Top leaderboard
CREATE OR REPLACE FUNCTION top_leaderboard()
RETURNS TABLE(
    uploader TEXT,
    total_songs BIGINT,
    rank BIGINT,
    tenants_name TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.added_by,
        COUNT(s.song_id),
        RANK() OVER (ORDER BY COUNT(s.song_id) DESC),
        t.name::TEXT   --  CAST FIX
    FROM songs s
    JOIN tenants t 
         ON s.tenant_id = t.tenant_id
    WHERE s.tenant_id = current_setting('app.current_tenant')::uuid
    GROUP BY s.added_by, t.name
    ORDER BY 3;
END;
$$;
--9.add_song--------------------------
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
--------------10. record_song_play
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
 
 ----------11.get_age_based_recommendations
CREATE OR REPLACE FUNCTION get_age_based_recommendations(p_age_group TEXT DEFAULT 'all')
 RETURNS TABLE(
 title VARCHAR,
 artist VARCHAR,
 genre  VARCHAR,
 rating NUMERIC,
 is_premium BOOLEAN,
 recommended_for TEXT
 ) AS $$
 BEGIN
  RETURN QUERY
  SELECT 
   s.title,
   s.artist,
   s.genre,
   s.rating,
   s.is_premium,
 CASE 
  WHEN p_age_group = 'Kopila' THEN 'Kopila(Young & Energetic)'
  WHEN p_age_group = 'Phool' THEN 'Phool(Mature)'
  WHEN p_age_group = 'Basanta' THEN 'Basanta(Calm & Balanced)'
 END AS recommended_for
 FROM songs s
 WHERE s.tenant_id=current_setting('app.current_tenant',true)::uuid
 AND(
     (p_age_group='Kopila' AND s.genre IN ('Pop','Hip Hop','Rock','Rap'))
   OR(p_age_group='Phool' AND s.genre IN ('Rock', 'Bollywood', 'Love', 'Indie'))
   OR (p_age_group = 'basanta' AND s.genre IN ('Classic', 'Folk', 'Country', 'Jazz', 'Ghazal'))
   OR (p_age_group = 'all')
      )
    ORDER BY s.rating DESC, RANDOM()
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;


REVOKE EXECUTE ON FUNCTION add_song FROM listener_free, listener_premium;
GRANT EXECUTE ON FUNCTION add_song TO appuser, adminn;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO appuser, adminn, listener_free, listener_premium;
GRANT EXECUTE ON FUNCTION record_song_play TO listener_free,listener_premium;
---------------------------------------Index-------------------------------------------------------------
SELECT *FROM tenants;

CREATE INDEX idx_tenants_song ON songs(tenant_id);
CREATE INDEX idx_added_by ON songs(added_by,tenant_id);

CREATE INDEX idx_tenants_user ON listener_profiles(tenant_id,user_name);
CREATE INDEX idx_subtenant_user ON premium_subscription(tenant_id,user_name);

CREATE INDEX idx_song_search
ON songs (tenant_id, title, artist);

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
DROP VIEW IF EXISTS listener_songs_view;
CREATE OR REPLACE VIEW listener_songs_view AS
SELECT id,title,artist,genre,rating,is_premium,tenant_id
FROM songs
WHERE tenant_id=current_setting('app.current_tenant',true)::uuid
AND(current_user!='listener_free' OR is_premium=FALSE);
ALTER VIEW listener_songs_view SET(security_barrier=true);
REVOKE SELECT ON songs FROM listener_free,listener_premium;
GRANT SELECT ON listener_songs_view TO listener_free,listener_premium;

---------------------TESTING-----------------------
SET ROLE=listener_free;
SELECT *FROM songs;
SELECT set_config('app.current_tenant','006b1b19-c1bc-489f-902b-f7aa1034b244',FALSE);
SELECT *FROM listener_songs_view;
RESET ROLE;

SET ROLE='listener_premium';
SET ROLE='listener_free';
SELECT set_config('app.current_tenant','006b1b19-c1bc-489f-902b-f7aa1034b244', FALSE);

SELECT COUNT(*) AS total,
COUNT(CASE WHEN is_premium THEN 1 END) AS premium_count
FROM listener_songs_view;


