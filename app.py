# app.py
import streamlit as st
import googlemaps
from itertools import permutations

# Initialize Google Maps client
API_KEY = AIzaSyDEMwIP-8B3Uu_lJFLlL4EQMBb6EOb_7Sw
gmaps = googlemaps.Client(key=API_KEY)

st.title("🚗 Optimal Route Planner")
st.write("Enter multiple addresses and get the fastest route with directions.")

# Input form
addresses = st.text_area("Enter one address per line:", height=200).strip().split("\n")
stop_time = st.selectbox("Choose stop time at each location:", [5, 7, 10])

if st.button("Calculate Optimal Route"):
    if len(addresses) < 2:
        st.warning("Please enter at least 2 addresses.")
    else:
        # Get all distance durations
        st.info("Calculating distances...")
        distance_matrix = gmaps.distance_matrix(addresses, addresses, mode="driving")
        times = [
            [elem['duration']['value'] for elem in row['elements']]
            for row in distance_matrix['rows']
        ]

        # Solve naive TSP (try all permutations)
        n = len(addresses)
        best_order = None
        min_time = float('inf')

        for perm in permutations(range(1, n)):
            order = [0] + list(perm)
            time = sum(times[order[i]][order[i + 1]] for i in range(n - 1))
            if time < min_time:
                min_time = time
                best_order = order

        optimal_addresses = [addresses[i] for i in best_order]
        stop_time_sec = stop_time * 60
        total_time_with_stops = min_time + stop_time_sec * len(addresses)

        # Directions from Google
        directions = []
        total_directions = []
        for i in range(len(best_order) - 1):
            origin = addresses[best_order[i]]
            destination = addresses[best_order[i + 1]]
            dir_segment = gmaps.directions(origin, destination, mode="driving")[0]
            directions.append(dir_segment)
            total_directions.append(dir_segment['legs'][0]['steps'])

        st.subheader("📍 Optimal Route Order")
        for i, addr in enumerate(optimal_addresses):
            st.write(f"{i+1}. {addr}")

        st.subheader("🕓 Total Travel Time")
        st.write(f"Without stops: **{min_time // 60:.0f} minutes**")
        st.write(f"With {stop_time} mins/stop: **{total_time_with_stops // 60:.0f} minutes**")

        st.subheader("🧭 Directions")
        for i, steps in enumerate(total_directions):
            st.markdown(f"**From {optimal_addresses[i]} to {optimal_addresses[i+1]}**")
            for step in steps:
                st.markdown(f"- {step['html_instructions']} ({step['distance']['text']}, {step['duration']['text']})", unsafe_allow_html=True)

        st.subheader("🗺️ Map")
        map_url = f"https://www.google.com/maps/dir/" + "/".join(optimal_addresses).replace(" ", "+")
        st.markdown(f"[View Route on Google Maps]({map_url})")

