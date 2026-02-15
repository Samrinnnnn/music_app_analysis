A simple yet powerful console-based music application built in Python with PostgreSQL as the backend.
This project demonstrates Row Level Security (RLS), custom PostgreSQL functions, role-based access control, premium content gating, user profiles, simulated subscriptions, search, and personalized recommendations.

Features:
Multi-role access with RLS isolation:
1) appuser — adds and sees only their own songs + dashboard (averages + chart)
2) adminn — full access (sees all songs, bypasses RLS) + dashboard
3) listener_free — sees only non-premium songs + search (blocks premium content) + upgrade option
4) listener_premium — sees all songs + search + personalized recommendations
   
PostgreSQL Functions used in application:
1) get_avg_rating_per_genre() — average rating per genre for current user
2) listener_genre_counts() — genre counts for listeners
3) premium_recommendations() — top-rated premium songs
4) update_listener_profile() — save/update name & address
5) subscribe_to_premium() — simulate premium upgrade
6) User profile (name + address) — saved per listener role, shown on welcome
7) Premium gating — free users see only non-premium songs
8) Simulated premium subscription — upgrade prompt + record in premium_subscriptions

Search — title/artist search with gating for free users
Recommendations — top-rated premium tracks for premium users
Console-based app
