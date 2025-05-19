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


st.set_page_config(page_title="Route Optimizer App", layout="wide")
st.title("🚗 Multi-Stop Route Optimizer with Driver Split")

# Helper functions
def geocode_address(address):
    try:
        location = gmaps.geocode(address)
        if location:
            lat = location[0]['geometry']['location']['lat']
            lng = location[0]['geometry']['location']['lng']
            return (lat, lng)
    except Exception as e:
        return None

def get_drive_time(origin, destination):
    try:
        result = gmaps.distance_matrix(origin, destination, mode="driving")
        duration = result['rows'][0]['elements'][0]['duration']['value']
        return duration
    except Exception as e:
        return float('inf')

def optimize_route(addresses):
    if len(addresses) <= 1:
        return addresses, 0, 0, 0

    origin = addresses[0]
    rest = addresses[1:]
    n = len(rest)

    import itertools
    min_route = []
    min_time = float('inf')

    for perm in itertools.permutations(rest):
        route = [origin] + list(perm)
        time = sum(get_drive_time(route[i], route[i+1]) for i in range(len(route)-1))
        if time < min_time:
            min_time = time
            min_route = route

    return_time = get_drive_time(min_route[-1], origin)
    stop_duration = stop_time * 60 * len(min_route)
    total_time_with_stops = min_time + stop_duration

    return min_route, min_time, total_time_with_stops, return_time

def extract_addresses_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    addresses = re.findall(r"\d{1,5} .+", text)
    return list(set([addr.strip() for addr in addresses if len(addr.strip()) > 10]))

# Inputs
with st.sidebar:
    st.header("📍 Input Addresses")
    input_method = st.radio("Choose Input Method", ["Manual Entry", "Upload PDF"])

    if input_method == "Manual Entry":
        addresses_input = st.text_area("Enter one address per line")
        addresses = [addr.strip() for addr in addresses_input.split("\n") if addr.strip() != ""]
    else:
        uploaded_file = st.file_uploader("Upload PDF with addresses", type="pdf")
        addresses = extract_addresses_from_pdf(uploaded_file) if uploaded_file else []

    start_location = st.text_input("Starting Point", value="1600 Amphitheatre Parkway, Mountain View, CA")
    stop_time = st.selectbox("Stop Duration at Each Address (minutes)", [5, 7, 10])
    driver_count = st.selectbox("Number of Drivers", [1, 2, 3, 4])
    sort_option = st.selectbox("Sort by", ["Normal Optimized Route", "Farthest First Route"])
    calc = st.button("Calculate Route")
    reset = st.button("Reset")

if reset:
    st.experimental_rerun()

if calc and addresses:
    addresses = [start_location] + addresses

    if driver_count == 1:
        if sort_option == "Farthest First Route":
            coords = [geocode_address(addr) for addr in addresses]
            start_coord = coords[0]
            distances = [((c[0] - start_coord[0])**2 + (c[1] - start_coord[1])**2, i)
                         for i, c in enumerate(coords) if c is not None]
            sorted_indices = [i for _, i in sorted(distances, reverse=True)]
            addresses = [addresses[0]] + [addresses[i] for i in sorted_indices if i != 0]

        route, drive_time, total_time, return_time = optimize_route(addresses)

        st.subheader("🧭 Optimized Route")
        for i, addr in enumerate(route):
            st.write(f"{i}. {addr}")

        st.write(f"- 🕒 Driving Time: {drive_time // 60} mins")
        st.write(f"- ⏱️ Total Time (with {stop_time} min stops): {total_time // 60} mins")
        st.write(f"- ↩️ Return to Start Time: {return_time // 60} mins")

        st.subheader("🧭 Step-by-Step Directions")
        for i in range(len(route) - 1):
            orig = route[i]
            dest = route[i + 1]
            directions = gmaps.directions(orig, dest, mode="driving")[0]
            st.markdown(f"**From {orig} to {dest}:**")
            for step in directions['legs'][0]['steps']:
                instruction = step['html_instructions']
                distance = step['distance']['text']
                duration = step['duration']['text']
                st.markdown(f"- {instruction} ({distance}, {duration})", unsafe_allow_html=True)

        map_url = "https://www.google.com/maps/dir/" + "/".join(route).replace(" ", "+")
        st.markdown(f"[Open Route in Google Maps]({map_url})")

    else:
        address_coords = []
        valid_addresses = []

        for addr in addresses:
            coord = geocode_address(addr)
            if coord:
                address_coords.append(coord)
                valid_addresses.append(addr)

        if len(address_coords) < driver_count:
            st.error("❌ Not enough valid addresses to split between selected number of drivers.")
        else:
            kmeans = KMeans(n_clusters=driver_count, random_state=42).fit(address_coords)
            labels = kmeans.labels_

            clusters = {i: [] for i in range(driver_count)}
            for i, label in enumerate(labels):
                clusters[label].append(valid_addresses[i])

            driver_cols = st.columns(driver_count)
            for driver_num in range(driver_count):
                with driver_cols[driver_num]:
                    driver_addresses = [start_location] + clusters[driver_num]

                    if sort_option == "Farthest First Route":
                        coords = [geocode_address(addr) for addr in driver_addresses]
                        start_coord = coords[0]
                        distances = [((c[0] - start_coord[0])**2 + (c[1] - start_coord[1])**2, i)
                                     for i, c in enumerate(coords) if c is not None]
                        sorted_indices = [i for _, i in sorted(distances, reverse=True)]
                        driver_addresses = [driver_addresses[0]] + [driver_addresses[i] for i in sorted_indices if i != 0]

                    st.subheader(f"🧭 Driver {driver_num + 1} Route")
                    route, drive_time, total_time, return_time = optimize_route(driver_addresses)

                    for i, addr in enumerate(route):
                        st.write(f"{i}. {addr}")

                    st.write(f"- 🕒 Driving Time: {drive_time // 60} mins")
                    st.write(f"- ⏱️ Total Time (with {stop_time} min stops): {total_time // 60} mins")
                    st.write(f"- ↩️ Return to Start Time: {return_time // 60} mins")

                    st.subheader("🧭 Step-by-Step Directions")
                    for i in range(len(route) - 1):
                        orig = route[i]
                        dest = route[i + 1]
                        directions = gmaps.directions(orig, dest, mode="driving")[0]
                        st.markdown(f"**From {orig} to {dest}:**")
                        for step in directions['legs'][0]['steps']:
                            instruction = step['html_instructions']
                            distance = step['distance']['text']
                            duration = step['duration']['text']
                            st.markdown(f"- {instruction} ({distance}, {duration})", unsafe_allow_html=True)

                    map_url = "https://www.google.com/maps/dir/" + "/".join(route).replace(" ", "+")
                    st.markdown(f"[Open Route in Google Maps]({map_url})")
