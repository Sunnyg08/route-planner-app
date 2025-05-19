# app.py
import streamlit as st
import googlemaps
import pandas as pd
import fitz  # PyMuPDF
from sklearn.cluster import KMeans
from itertools import permutations
import numpy as np


# Initialize Google Maps client
API_KEY = "AIzaSyDEMwIP-8B3Uu_lJFLlL4EQMBb6EOb_7Sw"
gmaps = googlemaps.Client(key=API_KEY)


st.set_page_config(page_title="Multi-Driver Route Planner", layout="centered")
st.title("🚗 Optimal Route Planner (Kitchen K)")

# Session defaults
if "addresses_input" not in st.session_state:
    st.session_state.addresses_input = ""
if "start_address" not in st.session_state:
    st.session_state.start_address = ""

# Reset function
def reset_inputs():
    st.session_state.addresses_input = ""
    st.session_state.start_address = ""

# File uploader
st.subheader("📄 Upload Addresses")
uploaded_file = st.file_uploader("Upload PDF, CSV, or Excel with addresses (one per line):", type=["pdf", "csv", "xlsx"])

extracted_addresses = []

if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1]
    if file_type == "pdf":
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            text = "\n".join([page.get_text() for page in doc])
            extracted_addresses = [line.strip() for line in text.splitlines() if line.strip()]
    elif file_type == "csv":
        df = pd.read_csv(uploaded_file)
        extracted_addresses = df.iloc[:, 0].dropna().astype(str).tolist()
    elif file_type == "xlsx":
        df = pd.read_excel(uploaded_file)
        extracted_addresses = df.iloc[:, 0].dropna().astype(str).tolist()

# Driver count
num_drivers = st.selectbox("Select number of drivers:", [1, 2, 3, 4, 5, 6])

# Start and stop inputs
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
col1, col2 = st.columns([1, 1])
calculate_clicked = col1.button("Calculate Route")
reset_clicked = col2.button("Reset", on_click=reset_inputs)

# Helper: geocode
def geocode_address(address):
    geocode = gmaps.geocode(address)
    if geocode:
        loc = geocode[0]['geometry']['location']
        return (loc['lat'], loc['lng'])
    return None

# Helper: optimize route
def optimize_route(address_list, allow_no_map=False):
    all_addresses = [start_address] + address_list

    # Google limit: 100 elements => max 10 locations
    if len(all_addresses) > 10 and not allow_no_map:
        return "LIMIT_EXCEEDED", None, None, None

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

    optimal_addresses = [all_addresses[i] for i in optimal_order]
    route_drive_time = sum(durations[optimal_order[i]][optimal_order[i + 1]] for i in range(len(optimal_order) - 1))
    return_to_start_time = durations[optimal_order[-1]][0]
    total_stop_time = stop_time * 60 * len(address_list)
    total_time = route_drive_time + total_stop_time

    return optimal_addresses, route_drive_time, total_time, return_to_start_time

if calculate_clicked:
    if not start_address:
        st.warning("Please enter a starting address.")
    elif len(addresses) < 1:
        st.warning("Please enter at least one destination stop.")
    else:
        try:
            # Geocode all addresses
            coords = [geocode_address(addr) for addr in addresses]
            coords_valid = [c for c in coords if c is not None]
            if len(coords_valid) < num_drivers:
                st.error("Not enough valid addresses to split between drivers.")
            else:
                # Cluster
                kmeans = KMeans(n_clusters=num_drivers, random_state=42).fit(coords_valid)
                clusters = {i: [] for i in range(num_drivers)}
                for idx, label in enumerate(kmeans.labels_):
                    clusters[label].append(addresses[idx])

                for driver_num in range(num_drivers):
                    driver_addresses = clusters[driver_num]

                    st.subheader(f"🧭 Driver {driver_num + 1} Route")

                    if len(driver_addresses) + 1 > 10:
                        st.warning(
                            f"Driver {driver_num + 1} has {len(driver_addresses)} stops.\n\n"
                            "⚠️ Google Maps allows a maximum of **10 locations per route** (including start).\n\n"
                            "**Options:**\n"
                            "- Increase number of drivers\n"
                            "- Or use written directions only (no Google Maps link)"
                        )
                        allow_written_only = st.checkbox(f"Generate written directions only for Driver {driver_num + 1}", key=f"written_only_{driver_num}")
                        if not allow_written_only:
                            continue
                        allow_no_map = True
                    else:
                        allow_no_map = False

                    route_result = optimize_route(driver_addresses, allow_no_map=allow_no_map)

                    if route_result == "LIMIT_EXCEEDED":
                        st.error(f"Route for Driver {driver_num + 1} exceeds Google Maps limits.")
                        continue

                    route, drive_time, total_time, return_time = route_result

                    for i, addr in enumerate(route):
                        st.write(f"{i}. {addr}")

                    st.write(f"- 🕒 Driving Time: {drive_time // 60} mins")
                    st.write(f"- ⏱️ Total Time (with {stop_time} min stops): {total_time // 60} mins")
                    st.write(f"- ↩️ Return to Start Time: {return_time // 60} mins")

                    if not allow_no_map:
                        map_url = "https://www.google.com/maps/dir/" + "/".join(route).replace(" ", "+")
                        st.markdown(f"[Open Route in Google Maps]({map_url})")

        except Exception as e:
            st.error(f"❌ Error: {e}")
