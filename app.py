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


# --- UI Setup ---
st.set_page_config(page_title="Multi-Driver Route Planner", layout="centered")
st.title("🚗 Optimal Route Planner (Kitchen K)")

# --- Session Defaults ---
if "addresses_input" not in st.session_state:
    st.session_state.addresses_input = ""
if "start_address" not in st.session_state:
    st.session_state.start_address = ""

# --- Reset Inputs ---
def reset_inputs():
    st.session_state.addresses_input = ""
    st.session_state.start_address = ""

# Upload file (PDF, CSV, or Excel)

uploaded_file = st.file_uploader("Upload a PDF, CSV, or Excel file with addresses:", type=["pdf", "csv", "xlsx"])
extracted_addresses = []

extracted_addresses = []

# --- Parse Files ---
if pdf_file:
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        text = "\n".join([page.get_text() for page in doc])
        extracted_addresses = [line.strip() for line in text.splitlines() if line.strip()]
elif csv_file:
    df = pd.read_csv(csv_file)
    extracted_addresses = df.iloc[:, 0].dropna().astype(str).tolist()
elif excel_file:
    df = pd.read_excel(excel_file)
    extracted_addresses = df.iloc[:, 0].dropna().astype(str).tolist()

# --- User Inputs ---
num_drivers = st.selectbox("Number of drivers:", [1, 2, 3, 4, 5])
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

# --- Helpers ---
def geocode_address(address):
    geocode = gmaps.geocode(address)
    if geocode:
        loc = geocode[0]['geometry']['location']
        return (loc['lat'], loc['lng'])
    return None

def optimize_route(address_list, allow_maps=True):
    all_addresses = [start_address] + address_list
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
    else:
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
            coords = [geocode_address(addr) for addr in addresses]
            valid_coords = [c for c in coords if c is not None]

            if len(valid_coords) < num_drivers:
                st.error("Not enough valid addresses to split between drivers.")
            else:
                kmeans = KMeans(n_clusters=num_drivers, random_state=42).fit(valid_coords)
                clusters = {i: [] for i in range(num_drivers)}
                for idx, label in enumerate(kmeans.labels_):
                    clusters[label].append(addresses[idx])

                for driver_num in range(num_drivers):
                    driver_addresses = clusters[driver_num]
                    st.subheader(f"🚘 Driver {driver_num + 1} Route")
                    
                    if len(driver_addresses) > 10:
                        st.warning(f"Driver {driver_num + 1} has **{len(driver_addresses)} stops**, which exceeds Google Maps' 10-stop limit.")
                        st.info("👉 **Options**:\n- Increase number of drivers\n- Continue with **step-by-step written directions** (no Maps link)")

                        continue_text = st.checkbox(f"Continue with written directions for Driver {driver_num + 1}?", key=f"driver_{driver_num}")
                        if not continue_text:
                            continue
                        allow_maps = False
                    else:
                        allow_maps = True

                    route, drive_time, total_time, return_time = optimize_route(driver_addresses, allow_maps)

                    for i, addr in enumerate(route):
                        st.write(f"{i}. {addr}")
                    st.write(f"- 🕒 Driving Time: {drive_time // 60} mins")
                    st.write(f"- ⏱️ Total Time (with {stop_time}-min stops): {total_time // 60} mins")
                    st.write(f"- ↩️ Return to Start: {return_time // 60} mins")

                    if allow_maps:
                        map_url = "https://www.google.com/maps/dir/" + "/".join(route).replace(" ", "+")
                        st.markdown(f"[🗺️ Open in Google Maps]({map_url})")
                    else:
                        st.markdown("### 📋 Step-by-Step Directions")
                        for i in range(len(route) - 1):
                            orig = route[i]
                            dest = route[i + 1]
                            try:
                                dir_result = gmaps.directions(orig, dest, mode="driving")[0]
                                st.markdown(f"**From {orig} to {dest}**")
                                for step in dir_result['legs'][0]['steps']:
                                    instruction = step['html_instructions']
                                    distance = step['distance']['text']
                                    duration = step['duration']['text']
                                    st.markdown(f"- {instruction} ({distance}, {duration})", unsafe_allow_html=True)
                            except:
                                st.error(f"Couldn't get directions from {orig} to {dest}.")

        except Exception as e:
            st.error(f"❌ Error: {e}")
