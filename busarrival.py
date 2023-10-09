import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone
import time
 
# Constants
BASE_URL = "http://datamall2.mytransport.sg/ltaodataservice"
API_KEY = "TSY1rJcvXgzlQmm3KCPKAQ=="  # Replace with your actual API key

headers = {
    "AccountKey": API_KEY,
    "accept": "application/json"
}

def get_all_bus_stops():
    """Fetch all bus stops from the LTA DataMall API."""
    skip = 0
    bus_stops = []

    while True:
        response = requests.get(f"{BASE_URL}/BusStops?$skip={skip}", headers=headers)
        if response.status_code == 200:
            data = response.json()["value"]
            if not data:
                break
            bus_stops.extend([{"code": item["BusStopCode"], "description": item["Description"], "road": item["RoadName"]} for item in data])
            skip += len(data)
        else:
            st.error("Failed to fetch bus stops. Please try again later.")
            break
    
    return bus_stops

def get_bus_arrival_time(bus_stop_code):
    """Fetch bus arrival time from the LTA DataMall API."""
    response = requests.get(f"{BASE_URL}/BusArrivalv2?BusStopCode={bus_stop_code}", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch bus arrival times. Please try again later.")
        return None

def convert_to_minutes(iso_time):
    """Convert ISO 8601 time to minutes difference from current time."""
    bus_time = datetime.fromisoformat(iso_time)
    now = datetime.now(timezone.utc)
    difference = bus_time - now
    return int(difference.total_seconds() / 60)

# Streamlit UI
st.title("LTA Bus Arrival Time Checker")

bus_stops = get_all_bus_stops()

# Filter options based on search input
search_term = st.text_input("Search for Road Name or Bus Stop Description:")
filtered_bus_stops = [bs for bs in bus_stops if search_term.lower() in bs["road"].lower() or search_term.lower() in bs["description"].lower()]

# Dropdown list
options = [f"{bs['code']} - {bs['description']} ({bs['road']})" for bs in filtered_bus_stops]
selected_option = st.selectbox("Choose a Bus Stop:", options)
bus_stop_code = selected_option.split(" ")[0]

# Check bus arrival time
if st.button("Check Arrival Time"):
    if bus_stop_code:
        data = get_bus_arrival_time(bus_stop_code)
        if data:
            services = data.get('Services', [])
            if services:
                df = pd.DataFrame(columns=["ServiceNo", "Operator", "Arrival Time (mins)", "Load", "Type"])

                for service in services:
                    buses = [service.get('NextBus', {}), service.get('NextBus2', {}), service.get('NextBus3', {})]
                    for bus in buses:
                        minutes = float('inf')
                        if bus['EstimatedArrival']:
                            minutes = int(round(convert_to_minutes(bus['EstimatedArrival'])))
                            if minutes <= 0:
                                continue

                        load_translation = {
                            "SEA": "Seats Available",
                            "SDA": "Standing Available",
                            "LSD": "Limited Standing"
                        }
                        type_translation = {
                            "SD": "Single Deck",
                            "DD": "Double Deck",
                            "BD": "Bendy"
                        }

                        new_row = {
                            "ServiceNo": service['ServiceNo'],
                            "Operator": service['Operator'],
                            "Arrival Time (mins)": minutes,
                            "Load": load_translation.get(bus['Load'], bus['Load']),
                            "Type": type_translation.get(bus['Type'], bus['Type'])
                        }
                        df.loc[len(df)] = new_row

                df["Sort"] = pd.to_numeric(df["Arrival Time (mins)"], errors='coerce').fillna(9999)
                df = df.sort_values(by="Sort")
                df = df.drop(columns="Sort")
                df = df.reset_index(drop=True)
                df.index = df.index + 1

                st.table(df)
            else:
                st.warning("No bus services available for this stop currently.")
    else:
        st.warning("Please choose a bus stop from the dropdown.")
