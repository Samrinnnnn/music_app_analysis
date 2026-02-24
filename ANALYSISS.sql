--SONG ANALYSIS
--1.Total songs per tenant
SELECT count(s.id) as total_songs, t.name as tenant_name
FROM songs s
JOIN tenants t ON s.tenant_id=t.tenant_id
GROUP BY tenant_id
ORDER BY total_songs DESC;

SELECT *FROM songs;

--2.Genre popularity per tenant
SELECT count(genre) as genre_popularity, tenant_id
FROM songs
GROUP BY tenant_id
ORDER BY genre_popularity;

--3.Premium vs Free song ratio
SELECT *FROM songs;
SELECT
SUM(CASE WHEN is_premium='true' THEN 1 ELSE 0 END)  AS premium_songs,
SUM(CASE WHEN is_premium='false' THEN 1 ELSE 0 END)  AS free_songs
FROM SONGS;

--4.Average rating per tenants
SELECT avg(rating) as average_rating, tenant_id
FROM songs 
GROUP BY tenant_id;

--5.Top rated songs
SELECT rating, title
FROM SONGS
ORDER BY rating DESC
LIMIT 10;
--LISTENER ANALYSIS
--6.Total listeners per tenant
SELECT *FROM premium_subscriptions;

SELECT COUNT(id) as total_listener,tenant_id
FROM listener_profiles
GROUP BY tenant_id;
--7.Premium subscription count per tenant

SELECT COUNT(id) as total_premium_subscription, tenant_id
FROM premium_subscriptions
GROUP BY tenant_id;

--8.Subscription revenue per tenant
SELECT SUM(amount) as revenue, tenant_id 
FROM premium_subscriptions
where payment_status='completed'
GROUP BY tenant_id;

--Business Analysis
--9. Conversion rate (Free → Premium)
SELECT *from listener_profiles;

/*SELECT COUNT(payment_status) as conversion_rate ,
FROM premium_subscriptions
where payment_status='completed';*/

SELECT 
    l.tenant_id,
    COUNT(DISTINCT l.user_name) AS total_users,
    COUNT(DISTINCT p.user_name) AS premium_users
FROM listener_profiles l
LEFT JOIN premium_subscriptions p
ON l.user_name = p.user_name
GROUP BY l.tenant_id;


--security analysis

--10.Who added most songs?
select *from songs;

SELECT COUNT(added_by) as total, added_by
FROM songs
GROUP BY added_by;

--ADVANCED ANALYSIS
--11.Find inactive tenants
SELECT s.title,t.id , COUNT(s.tenant_id) as tenants_contribution
FROM songs s
LEFT JOIN tenants t ON s.tenant_id=t.id
GROUP BY  s.title, t.id
ORDER BY tenants_contribution ASC;








