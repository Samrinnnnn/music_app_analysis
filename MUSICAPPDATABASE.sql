-- 1. Create roles
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'appuser') THEN
        CREATE ROLE appuser WITH LOGIN PASSWORD 'pass123';
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'adminn') THEN
        CREATE ROLE adminn WITH LOGIN PASSWORD 'admin123' BYPASSRLS;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'listener_free') THEN
        CREATE ROLE listener_free WITH LOGIN PASSWORD 'free123' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'listener_premium') THEN
        CREATE ROLE listener_premium WITH LOGIN PASSWORD 'premium456' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;

-- 2. Basic permissions
GRANT CONNECT ON DATABASE appformusic TO appuser, adminn, listener_free, listener_premium;
GRANT USAGE ON SCHEMA public TO appuser, adminn, listener_free, listener_premium;

-- 2.1 Tenants table
DROP TABLE IF EXISTS tenants CASCADE;
CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(120) NOT NULL,
    slug        VARCHAR(60)  UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    is_active   BOOLEAN DEFAULT TRUE
);

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY admin_manage_tenants ON tenants
    FOR ALL USING (current_user = 'adminn') WITH CHECK (current_user = 'adminn');

GRANT ALL ON tenants TO adminn;

-- 2.2 Helper to set current tenant
CREATE OR REPLACE FUNCTION set_app_current_tenant(p_tenant_id UUID)
RETURNS VOID LANGUAGE sql AS $$
    SELECT set_config('app.current_tenant', p_tenant_id::text, true);
$$;

GRANT EXECUTE ON FUNCTION set_app_current_tenant(UUID)
    TO appuser, adminn, listener_free, listener_premium;

-- 3. Songs (multi-tenant)
DROP TABLE IF EXISTS songs CASCADE;
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

ALTER TABLE songs ENABLE ROW LEVEL SECURITY;

-- Tenant isolation (strongest rule — must come first)
CREATE POLICY tenant_isolation_songs ON songs FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);

-- Owner rules (within tenant)
CREATE POLICY song_owner ON songs FOR ALL
    USING (added_by = current_user AND tenant_id = current_setting('app.current_tenant')::uuid)
    WITH CHECK (added_by = current_user AND tenant_id = current_setting('app.current_tenant')::uuid);

-- Listener access (within tenant)
CREATE POLICY listener_free_songs ON songs FOR SELECT
    USING (current_user = 'listener_free' AND is_premium = FALSE AND tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY listener_premium_songs ON songs FOR SELECT
    USING (current_user = 'listener_premium' AND tenant_id = current_setting('app.current_tenant')::uuid);

GRANT SELECT, INSERT, UPDATE ON songs TO appuser;
GRANT USAGE, SELECT ON SEQUENCE songs_id_seq TO appuser;
GRANT ALL ON songs TO adminn;
GRANT ALL ON SEQUENCE songs_id_seq TO adminn;
GRANT SELECT ON songs TO listener_free, listener_premium;

-- 4. Listener profiles (multi-tenant)
CREATE TABLE listener_profiles(
user_name     TEXT PRIMARY KEY ,
full_name     VARCHAR(50) NOT NULL,
address       VARCHAR(150) NOT NULL,
updated_at    TIMESTAMPTZ DEFAULT NOW(),
tenant_id     UUID NOT NULL,
FOREIGN KEY(tenant_id)
REFERENCES tenants(tenant_id)
);
ALTER TABLE listener_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_listener_profiles ON listener_profiles FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY own_profile ON listener_profiles FOR ALL
    USING (user_name = current_user AND tenant_id = current_setting('app.current_tenant')::uuid)
    WITH CHECK (user_name = current_user AND tenant_id = current_setting('app.current_tenant')::uuid);

GRANT SELECT, INSERT, UPDATE ON listener_profiles TO listener_free, listener_premium;

-- 5. Premium subscriptions (multi-tenant)
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


ALTER TABLE premium_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_subscriptions ON premium_subscriptions FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY own_subscription ON premium_subscriptions FOR ALL
    USING (user_name = current_user AND tenant_id = current_setting('app.current_tenant')::uuid)
    WITH CHECK (user_name = current_user AND tenant_id = current_setting('app.current_tenant')::uuid);

GRANT SELECT, INSERT, UPDATE ON premium_subscriptions TO listener_free, listener_premium;

-- 6. Functions (tenant-aware)

CREATE OR REPLACE FUNCTION get_avg_rating_per_genre()
RETURNS TABLE (genre_name VARCHAR, avg_rating NUMERIC)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT genre, ROUND(AVG(rating), 1)
    FROM songs
    WHERE added_by = current_user
      AND tenant_id = current_setting('app.current_tenant')::uuid
    GROUP BY genre
    ORDER BY avg_rating DESC;
END;
$$;

CREATE OR REPLACE FUNCTION listener_genre_counts()
RETURNS TABLE (genre_name VARCHAR, song_count BIGINT)
LANGUAGE sql SECURITY DEFINER AS $$
    SELECT genre, COUNT(*)
    FROM songs
    WHERE tenant_id = current_setting('app.current_tenant')::uuid
    GROUP BY genre HAVING COUNT(*) > 0
    ORDER BY COUNT(*) DESC;
$$;

CREATE OR REPLACE FUNCTION premium_recommendations(limit_count INT DEFAULT 6)
RETURNS TABLE (title VARCHAR, artist VARCHAR, genre VARCHAR, rating NUMERIC, is_premium BOOLEAN)
LANGUAGE sql SECURITY DEFINER AS $$
    SELECT title, artist, genre, rating, is_premium
    FROM songs
    WHERE is_premium = TRUE
      AND rating IS NOT NULL
      AND tenant_id = current_setting('app.current_tenant')::uuid
    ORDER BY rating DESC, RANDOM()
    LIMIT limit_count;
$$;

CREATE OR REPLACE FUNCTION get_listener_profile()
RETURNS TABLE (full_name VARCHAR(100), address TEXT)
LANGUAGE sql AS $$
    SELECT full_name, address
    FROM listener_profiles
    WHERE user_name = current_user
      AND tenant_id = current_setting('app.current_tenant')::uuid;
$$;

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

-- Function grants
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO appuser, adminn, listener_free, listener_premium;


--INDEX--

CREATE INDEX idx_tenants_song ON songs(tenant_id);
CREATE INDEX idx_added_by ON songs(added_by,tenant_id);



