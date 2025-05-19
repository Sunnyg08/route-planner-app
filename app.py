# app.py
import streamlit as st
import googlemaps
from itertools import permutations


# Initialize Google Maps client
API_KEY = "AIzaSyDEMwIP-8B3Uu_lJFLlL4EQMBb6EOb_7Sw"
gmaps = googlemaps.Client(key=API_KEY)

st.title("🚗 Optimal Route Planner Kitchen K")
st.write("Enter multiple addresses and get the fastest route with directions.")

addresses_input = st.text_area("Enter one address per line:", height=200).strip()
addresses = [a.strip() for a in addresses_input.split('\n') if a.strip()]
stop_time = st.selectbox("Choose stop time at each location (minutes):", [5, 7, 10])

if st.button("Calculate Optimal Route"):
    if len(addresses) < 2:
        st.warning("Please enter at least two addresses.")
    else:
        try:
            # Build travel time matrix
            matrix = gmaps.distance_matrix(addresses, addresses, mode='driving')
            durations = [
                [cell['duration']['value'] for cell in row['elements']]
                for row in matrix['rows']
            ]

            # Find best route (brute-force)
            n = len(addresses)
            indices = list(range(n))
            best_order = None
            best_time = float('inf')

            for perm in permutations(indices[1:]):  # Fix start point at index 0
                order = [0] + list(perm)
                total = sum(durations[order[i]][order[i+1]] for i in range(n - 1))
                if total < best_time:
                    best_time = total
                    best_order = order

            # Display optimized route
            optimal_addresses = [addresses[i] for i in best_order]
            st.subheader("📍 Optimized Route Order")
            for i, addr in enumerate(optimal_addresses):
                st.write(f"{i+1}. {addr}")

            # Add stop time
            stop_seconds = stop_time * 60
            total_with_stops = best_time + stop_seconds * len(addresses)

            st.subheader("🕓 Time Estimates")
            st.write(f"Without stops: **{best_time // 60:.0f} minutes**")
            st.write(f"With {stop_time} mins/stop: **{total_with_stops // 60:.0f} minutes**")

            # Get directions between optimized stops
            st.subheader("🧭 Directions")
            for i in range(len(optimal_addresses) - 1):
                orig = optimal_addresses[i]
                dest = optimal_addresses[i+1]
                dir_result = gmaps.directions(orig, dest, mode="driving")[0]
                st.markdown(f"**From {orig} to {dest}**")
                for step in dir_result['legs'][0]['steps']:
                    instruction = step['html_instructions']
                    distance = step['distance']['text']
                    duration = step['duration']['text']
                    st.markdown(f"- {instruction} ({distance}, {duration})", unsafe_allow_html=True)

            # Add map link
            map_url = "https://www.google.com/maps/dir/" + "/".join(optimal_addresses).replace(" ", "+")
            st.subheader("🗺️ Map View")
            st.markdown(f"[Open Route in Google Maps]({map_url})")

        except Exception as e:
            st.error(f"Something went wrong: {e}")


