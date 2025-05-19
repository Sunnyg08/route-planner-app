# app.py
import streamlit as st
import googlemaps
import fitz  # PyMuPDF
from sklearn.cluster import KMeans
from itertools import permutations
import numpy as np


# Initialize Google Maps client
API_KEY = "AIzaSyDEMwIP-8B3Uu_lJFLlL4EQMBb6EOb_7Sw"
gmaps = googlemaps.Client(key=API_KEY)


st.set_page_config(page_title="Multi-Driver Route Planner", layout="centered")
st.title("🚗 Optimal Route Planner (Kitchen K)")

# --- Session State Defaults ---
if "addresses_input" not in st.session_state:
    st.session_state.addresses_input = ""
if "start_address" not in st.session_state:
    st.session_state.start_address = ""

# --- Reset Function ---
def reset_inputs():
    st.session_state.addresses_input = ""
    st.session_state.start_address = ""

# --- PDF Upload and Extraction ---
pdf_file = st.file_uploader("Upload a PDF with addresses (one per line):", type=["pdf"])
extracted_addresses = []
if pdf_file:
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        text = "\n".join([page.get_text() for page in doc])
        extracted_addresses = [line.strip() for line in text.splitlines() if line.strip()]

# --- Inputs ---
num_drivers = st.selectbox("Select number of drivers:", [1, 2, 3, 4])
start_address = st.text_input("Starting Address:", key="start_address")
addresses_input = st.text_area(
    "Enter destination stops (one per line):",
    value="\n".join(extracted_addresses) if extracted_addresses else st.session_state.addresses_input,
    height=200,
    key="addresses_input"
)
addresses = [a.strip() for a in addresses_input.split('\n') if a.strip()]
stop_time = st.selectbox("Stop duration at each location (minutes):", [5, 7, 10])
sort_method = st.selectbox("Sort by:", ["Normal Optimized Route", "Farthest First Route"])

# --- Buttons ---
col1, col2 = st.columns([1, 1])
calculate_clicked = col1.button("Calculate Route")
reset_clicked = col2.button("Reset", on_click=reset_inputs)

# --- Geocode Address Helper ---
def geocode_address(address):
    try:
        geocode = gmaps.geocode(address)
        if geocode:
            loc = geocode[0]['geometry']['location']
            return (loc['lat'], loc['lng'])
    except:
        pass
    return None

# --- Route Optimizer ---
def optimize_route(address_list):
    all_addresses = [start_address] + address_list
    matrix = gmaps.distance_matrix(all_addresses, all_addresses, mode='driving')

    # Parse durations with error handling
    durations = []
    for row_index, row in enumerate(matrix['rows']):
        row_durations = []
        for col_index, cell in enumerate(row['elements']):
            if cell.get("status") == "OK":
                row_durations.append(cell["duration"]["value"])
            else:
                st.warning(
                    f"⚠️ Could not get duration between address {row_index} and {col_index}. "
                    "Check if the address is valid or reachable by car."
                )
                row_durations.append(float('inf'))
        durations.append(row_durations)

    # Check if any durations are unreachable
    if any(float('inf') in row for row in durations):
        raise ValueError("Distance matrix contains unreachable destinations.")

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

    optimal_addresses = [all_addresses[i] for i in optimal_order]
    route_drive_time = sum(durations[optimal_order[i]][optimal_order[i + 1]] for i in range(len(optimal_order) - 1))
    return_to_start_time = durations[optimal_order[-1]][0]
    total_stop_time = stop_time * 60 * len(address_list)
    total_time = route_drive_time + total_stop_time

    return optimal_addresses, route_drive_time, total_time, return_to_start_time

# --- Route Calculation ---
if calculate_clicked:
    if not start_address:
        st.warning("Please enter a starting address.")
    elif len(addresses) < 1:
        st.warning("Please enter at least one destination stop.")
    else:
        try:
            # Geocode destination addresses
            coords = [geocode_address(addr) for addr in addresses]
            valid_data = [(addr, c) for addr, c in zip(addresses, coords) if c is not None]
            if len(valid_data) < num_drivers:
                st.error("❌ Not enough valid addresses to assign to all drivers.")
            else:
                # Clustering
                locations = [loc for _, loc in valid_data]
                kmeans = KMeans(n_clusters=num_drivers, random_state=42).fit(locations)
                clusters = {i: [] for i in range(num_drivers)}
                for (addr, _), label in zip(valid_data, kmeans.labels_):
                    clusters[label].append(addr)

                # Show routes per driver
                for driver_num in range(num_drivers):
                    driver_addresses = clusters[driver_num]
                    st.subheader(f"🧭 Driver {driver_num + 1} Route")

                    route, drive_time, total_time, return_time = optimize_route(driver_addresses)

                    for i, addr in enumerate(route):
                        st.write(f"{i}. {addr}")

                    st.subheader("🕓 Time Estimates")
                    st.write(f"🚘 Driving time (no stops): **{route_drive_time // 60} minutes**")
                    st.write(f"🕒 Total time with {stop_time}-minute stops: **{total_time // 60} minutes**")
                    st.write(f"↩️ Time to return to start from last stop: **{return_to_start_time // 60} minutes**")

                    map_url = "https://www.google.com/maps/dir/" + "/".join(route).replace(" ", "+")
                    st.markdown(f"[Open Route in Google Maps]({map_url})")

        except Exception as e:
            st.error(f"❌ Error: {e}")

