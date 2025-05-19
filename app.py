# app.py
import streamlit as st
import googlemaps
from itertools import permutations


# Initialize Google Maps client
API_KEY = "AIzaSyDEMwIP-8B3Uu_lJFLlL4EQMBb6EOb_7Sw"
gmaps = googlemaps.Client(key=API_KEY)

st.title("🚗 Optimal Route Planner (Kitchen K)")
st.write("Enter a starting point and a list of stops. The app will find the fastest one-way route, then tell you how long it takes to get back to the start.")

# Inputs
start_address = st.text_input("Starting Address:")
addresses_input = st.text_area("Enter destination stops (one per line):", height=200).strip()
addresses = [a.strip() for a in addresses_input.split('\n') if a.strip()]
stop_time = st.selectbox("Stop duration at each location (minutes):", [5, 7, 10])

if st.button("Calculate Optimal Route"):
    if not start_address:
        st.warning("Please enter a starting address.")
    elif len(addresses) < 1:
        st.warning("Please enter at least one destination stop.")
    else:
        try:
            all_addresses = [start_address] + addresses

            # Get driving durations matrix
            matrix = gmaps.distance_matrix(all_addresses, all_addresses, mode='driving')
            durations = [
                [cell['duration']['value'] for cell in row['elements']]
                for row in matrix['rows']
            ]

            # Fix starting point, optimize only stop order
            stop_indices = list(range(1, len(all_addresses)))  # destinations only
            best_order = None
            best_time = float('inf')

            for perm in permutations(stop_indices):
                order = [0] + list(perm)  # start + permuted stops
                total = sum(durations[order[i]][order[i+1]] for i in range(len(order)-1))
                if total < best_time:
                    best_time = total
                    best_order = order

            optimal_addresses = [all_addresses[i] for i in best_order]
            last_stop_index = best_order[-1]
            return_to_start_time = durations[last_stop_index][0]

            st.subheader("📍 Optimized Route (One-Way)")
            for i, addr in enumerate(optimal_addresses):
                if i == 0:
                    st.write(f"Start: {addr}")
                else:
                    st.write(f"{i}. {addr}")

            stop_seconds = stop_time * 60
            total_stop_time = stop_seconds * len(addresses)
            total_time = best_time + total_stop_time

            st.subheader("🕓 Time Estimates")
            st.write(f"Driving time (excluding stops): **{best_time // 60:.0f} minutes**")
            st.write(f"Total time with {stop_time} mins/stop: **{total_time // 60:.0f} minutes**")
            st.write(f"Time to return to start from last stop: **{return_to_start_time // 60:.0f} minutes**")

            st.subheader("🧭 Step-by-Step Directions")
            for i in range(len(optimal_addresses) - 1):
                orig = optimal_addresses[i]
                dest = optimal_addresses[i + 1]
                dir_result = gmaps.directions(orig, dest, mode="driving")[0]
                st.markdown(f"**From {orig} to {dest}**")
                for step in dir_result['legs'][0]['steps']:
                    instruction = step['html_instructions']
                    distance = step['distance']['text']
                    duration = step['duration']['text']
                    st.markdown(f"- {instruction} ({distance}, {duration})", unsafe_allow_html=True)

            # Map link
            map_url = "https://www.google.com/maps/dir/" + "/".join(optimal_addresses).replace(" ", "+")
            st.subheader("🗺️ Map View")
            st.markdown(f"[Open Route in Google Maps]({map_url})")

        except Exception as e:
            st.error(f"An error occurred: {e}")

