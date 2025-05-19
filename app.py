# app.py
import streamlit as st
import googlemaps
from itertools import permutations


# Initialize Google Maps client
API_KEY = "AIzaSyDEMwIP-8B3Uu_lJFLlL4EQMBb6EOb_7Sw"
gmaps = googlemaps.Client(key=API_KEY)

st.title("🚗 Optimal Route Planner")
st.write("Enter a starting point and a list of stops to find the fastest round-trip route.")

# Input: starting address
start_address = st.text_input("Starting Address:")

# Input: stops
addresses_input = st.text_area("Enter destination stops (one per line):", height=200).strip()
addresses = [a.strip() for a in addresses_input.split('\n') if a.strip()]

# Input: stop time
stop_time = st.selectbox("Stop duration at each location (minutes):", [5, 7, 10])

if st.button("Calculate Route"):
    if not start_address:
        st.warning("Please enter a starting address.")
    elif len(addresses) < 1:
        st.warning("Please enter at least one destination stop.")
    else:
        try:
            # Full list including start
            all_addresses = [start_address] + addresses

            # Get distance matrix for all points
            matrix = gmaps.distance_matrix(all_addresses, all_addresses, mode='driving')
            durations = [
                [cell['duration']['value'] for cell in row['elements']]
                for row in matrix['rows']
            ]

            n = len(all_addresses)
            indices = list(range(1, n))  # exclude start_address at index 0

            best_order = None
            best_time = float('inf')

            for perm in permutations(indices):
                order = [0] + list(perm)  # 0 is the fixed starting point
                total = sum(durations[order[i]][order[i+1]] for i in range(len(order)-1))
                return_time = durations[order[-1]][0]  # return to start
                total += return_time
                if total < best_time:
                    best_time = total
                    best_order = order

            # Final ordered addresses (including return)
            optimal_order = best_order + [0]  # add return leg to start
            optimal_addresses = [all_addresses[i] for i in optimal_order]

            st.subheader("📍 Optimized Round-Trip Route")
            for i, addr in enumerate(optimal_addresses):
                if i == 0:
                    st.write(f"Start: {addr}")
                elif i == len(optimal_addresses) - 1:
                    st.write(f"Return to Start: {addr}")
                else:
                    st.write(f"{i}. {addr}")

            stop_seconds = stop_time * 60
            total_stop_time = stop_seconds * len(addresses)
            drive_only_time = best_time
            total_time = drive_only_time + total_stop_time

            return_drive_time = durations[best_order[-1]][0]

            st.subheader("🕓 Time Estimates")
            st.write(f"Driving time (excluding stops): **{drive_only_time // 60:.0f} minutes**")
            st.write(f"Time from last stop back to starting point: **{return_drive_time // 60:.0f} minutes**")
            st.write(f"Total trip time with {stop_time}-minute stops: **{total_time // 60:.0f} minutes**")

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


