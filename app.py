# app.py
import streamlit as st
import googlemaps
import pandas as pd
import fitz  # PyMuPDF
from sklearn.cluster import KMeans
from itertools import permutations
import numpy as np


# Initialize Google Maps client
API_KEY = "AIzaSyAXsCZX0UeX06qCcDN2WG7dGkrj4OD5J1A"
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

# Upload file (PDF, CSV, or Excel)

uploaded_file = st.file_uploader("Upload a PDF, CSV, or Excel file with addresses:", type=["pdf", "csv", "xlsx"])
extracted_addresses = []

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".pdf"):
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                text = "\n".join([page.get_text() for page in doc])
                extracted_addresses = [line.strip() for line in text.splitlines() if line.strip()]

        elif uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            address_column = 'Address' if 'Address' in df.columns else df.columns[0]
            extracted_addresses = df[address_column].dropna().astype(str).tolist()

        elif uploaded_file.name.endswith((".xls", ".xlsx")):
            df = pd.read_excel(uploaded_file)
            address_column = 'Address' if 'Address' in df.columns else df.columns[0]
            extracted_addresses = df[address_column].dropna().astype(str).tolist()

    except Exception as e:
        st.error(f"❌ Error reading file: {e}")

# Driver count
num_drivers = st.selectbox("Select number of drivers:", [1, 2, 3, 4])

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

# Helper: get lat/lng for clustering
def geocode_address(address):
    geocode = gmaps.geocode(address)
    if geocode:
        loc = geocode[0]['geometry']['location']
        return (loc['lat'], loc['lng'])
    return None

# Helper: optimize route
def optimize_route(address_list):
    all_addresses = [start_address] + address_list
    matrix = gmaps.distance_matrix(all_addresses, all_addresses, mode='driving')
    durations = [
        [cell['duration']['value'] if cell.get('duration') else float('inf') for cell in row['elements']]
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

# Route calculation
if calculate_clicked:
    if not start_address:
        st.warning("Please enter a starting address.")
    elif len(addresses) < 1:
        st.warning("Please enter at least one destination stop.")
    else:
        try:
            coords = [geocode_address(addr) for addr in addresses]
            coords_valid = [c for c in coords if c is not None]

            if len(coords_valid) < num_drivers:
                st.error("Not enough valid addresses to split between drivers.")
            else:
                if num_drivers == 1:
                    clusters = {0: addresses}
                else:
                    kmeans = KMeans(n_clusters=num_drivers, random_state=42).fit(coords_valid)
                    clusters = {i: [] for i in range(num_drivers)}
                    for idx, label in enumerate(kmeans.labels_):
                        clusters[label].append(addresses[idx])

                for driver_num in range(num_drivers):
                    driver_addresses = clusters[driver_num]
                    st.subheader(f"🧭 Driver {driver_num + 1} Route")

                    route, drive_time, total_time, return_time = optimize_route(driver_addresses)

                    for i, addr in enumerate(route):
                        st.write(f"{i}. {addr}")

                    st.write(f"- 🚘 Driving Time: {drive_time // 60} mins")
                    st.write(f"- ⏱️ Total Time (with {stop_time} min stops): {total_time // 60} mins")
                    st.write(f"- ↩️ Return to Start Time: {return_time // 60} mins")

                    map_url = "https://www.google.com/maps/dir/" + "/".join(route).replace(" ", "+")
                    st.markdown(f"[Open Route in Google Maps]({map_url})")

        except Exception as e:
            st.error(f"❌ Error: {e}")
