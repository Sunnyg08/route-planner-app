# app.py
import streamlit as st
import googlemaps
from itertools import permutations


# Initialize Google Maps client
API_KEY = "AIzaSyDEMwIP-8B3Uu_lJFLlL4EQMBb6EOb_7Sw"
gmaps = googlemaps.Client(key=API_KEY)

import streamlit as st
import googlemaps
from itertools import permutations

# Initialize Google Maps API
API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)

st.set_page_config(page_title="Route Optimizer", layout="centered")
st.title("🚗 Optimal Route Planner")
st.write("Enter your starting point and multiple stops. Choose how to sort the route and how long you'll spend at each stop.")

# --- Session State Defaults ---
if "addresses_input" not in st.session_state:
    st.session_state.addresses_input = ""
if "start_address" not in st.session_state:
    st.session_state.start_address = ""

# --- Reset Function ---
def reset_inputs():
    st.session_state.addresses_input = ""
    st.session_state.start_address = ""

# --- Input Fields ---
start_address = st.text_input("Starting Address:", key="start_address")

addresses_input = st.text_area(
    "Enter destination stops (one per line):",
    height=200,
    key="addresses_input"
)
addresses = [a.strip() for a in addresses_input.split('\n') if a.strip()]

# --- Stop Duration ---
stop_time = st.selectbox("Stop duration at each location (minutes):", [5, 7, 10])

# --- Sort Option ---
sort_method = st.selectbox("Sort by:", ["Normal Optimized Route", "Farthest First Route"])

# --- Buttons ---
col1, col2 = st.columns([1, 1])
calculate_clicked = col1.button("Calculate Route")
reset_clicked = col2.button("Reset", on_click=reset_inputs)

# --- Route Calculation ---
if calculate_clicked:
    if not start_address:
        st.warning("Please enter a starting address.")
    elif len(addresses) < 1:
        st.warning("Please enter at least one destination stop.")
    else:
        try:
            all_addresses = [start_address] + addresses

            # Get durations between all address pairs
            matrix = gmaps.distance_matrix(all_addresses, all_addresses, mode='driving')
            durations = [
                [cell['duration']['value'] for cell in row['elements']]
                for row in matrix['rows']
            ]

            stop_indices = list(range(1, len(all_addresses)))

            if sort_method == "Normal Optimized Route":
                best_order = None
                best_time = float('inf')
                for perm in permutations(stop_indices):
                    order = [0] + list(perm)
                    total = sum(durations[order[i]][order[i + 1]] for i in range(len(order) - 1))
                    if total < best_time:
                        best_time = total
                        best_order = order
                optimal_order = best_order

            elif sort_method == "Farthest First Route":
                sorted_stops = sorted(stop_indices, key=lambda i: -durations[0][i])
                optimal_order = [0] + sorted_stops

            # Build final route
            optimal_addresses = [all_addresses[i] for i in optimal_order]
            last_stop_index = optimal_order[-1]
            return_to_start_time = durations[last_stop_index][0]

            st.subheader("📍 Route Order")
            for i, addr in enumerate(optimal_addresses):
                if i == 0:
                    st.write(f"Start: {addr}")
                else:
                    st.write(f"{i}. {addr}")

            # Time Estimates
            stop_seconds = stop_time * 60
            total_stop_time = stop_seconds * len(addresses)
            route_drive_time = sum(durations[optimal_order[i]][optimal_order[i+1]] for i in range(len(optimal_order)-1))
            total_time = route_drive_time + total_stop_time

            st.subheader("🕓 Time Estimates")
            st.write(f"🚘 Driving time (no stops): **{route_drive_time // 60} minutes**")
            st.write(f"🕒 Total time with {stop_time}-minute stops: **{total_time // 60} minutes**")
            st.write(f"↩️ Time to return to start from last stop: **{return_to_start_time // 60} minutes**")

            # Directions
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

            # Map Link
            map_url = "https://www.google.com/maps/dir/" + "/".join(optimal_addresses).replace(" ", "+")
            st.subheader("🗺️ Map View")
            st.markdown(f"[Open Route in Google Maps]({map_url})")

        except Exception as e:
            st.error(f"❌ Error: {e}")
