
import streamlit as st
import folium
import html
import re

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from streamlit_folium import st_folium


# ==================================================
# LOCATION TEXT CLEANING
# ==================================================

def clean_location(value):

    if value is None:
        return ""

    value = str(value).strip()

    if value.lower() in ["", "none", "nan"]:
        return ""

    return re.sub(r"\s+", " ", value)


# ==================================================
# OPENSTREETMAP GEOCODER
# ==================================================

@st.cache_resource
def get_geocoder():

    geolocator = Nominatim(
        user_agent="JANASHAKTI_AI_India_Community_Map"
    )

    return RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1.1,
        max_retries=2,
        error_wait_seconds=3,
        swallow_exceptions=True
    )


# ==================================================
# DYNAMIC INDIA-WIDE LOCATION SEARCH
# ==================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_coordinates(locality, district, state):

    locality = clean_location(locality)
    district = clean_location(district)
    state = clean_location(state)

    if not locality:
        return None

    geocode = get_geocoder()

    # Try progressively broader location queries.
    queries = []

    if district and state:
        queries.append(
            f"{locality}, {district}, {state}, India"
        )

    if state:
        queries.append(
            f"{locality}, {state}, India"
        )

    if district:
        queries.append(
            f"{locality}, {district}, India"
        )

    queries.append(
        f"{locality}, India"
    )

    # Remove duplicate queries.
    queries = list(dict.fromkeys(queries))

    for query in queries:

        try:

            location = geocode(
                query,
                timeout=20,
                country_codes=["in"],
                exactly_one=True
            )

            if location:

                latitude = float(location.latitude)
                longitude = float(location.longitude)

                # Basic geographic validation.
                if (
                    6.0 <= latitude <= 37.5
                    and 68.0 <= longitude <= 97.5
                ):

                    return (
                        latitude,
                        longitude
                    )

        except Exception:
            continue

    return None


# ==================================================
# COMPLAINT CATEGORY COLOURS
# ==================================================

CATEGORY_COLORS = {

    "water shortage": "blue",
    "water supply": "blue",
    "water": "blue",

    "waste management": "green",
    "waste": "green",
    "garbage": "green",

    "damaged roads": "orange",
    "road maintenance": "orange",
    "roads": "orange",

    "drainage": "purple",

    "electricity": "red",
    "power supply": "red",

    "streetlights": "cadetblue",
    "street lights": "cadetblue",

    "public safety": "darkred",

    "other": "gray"
}


# ==================================================
# CREATE INTERACTIVE COMPLAINT MAP
# ==================================================

def create_complaint_map(reports):

    complaint_map = folium.Map(
        location=[22.5, 82.0],
        zoom_start=5,
        tiles="OpenStreetMap"
    )

    plotted_locations = []
    skipped_locations = []

    # --------------------------------------------------
    # PROCESS EVERY SAVED COMPLAINT
    # --------------------------------------------------

    for report in reports:

        locality = clean_location(
            report.get("locality")
        )

        district = clean_location(
            report.get("district")
        )

        state = clean_location(
            report.get("state")
        )

        # Dynamically locate any Indian locality.
        coordinates = get_coordinates(
            locality,
            district,
            state
        )

        if coordinates is None:

            skipped_locations.append(
                locality or "Unknown location"
            )

            continue

        latitude, longitude = coordinates

        category = clean_location(
            report.get("category", "Other")
        )

        color = CATEGORY_COLORS.get(
            category.lower(),
            "gray"
        )

        report_id = html.escape(
            clean_location(
                report.get("report_id", "Unknown")
            )
        )

        safe_category = html.escape(category)

        safe_locality = html.escape(locality)

        safe_district = html.escape(district)

        safe_state = html.escape(state)

        safe_status = html.escape(
            clean_location(
                report.get("status", "Submitted")
            )
        )

        safe_priority = html.escape(
            clean_location(
                report.get(
                    "priority_level",
                    "Not Assessed"
                )
            )
        )

        safe_description = html.escape(
            clean_location(
                report.get("description", "")
            )[:300]
        )

        # --------------------------------------------------
        # MARKER POPUP
        # --------------------------------------------------

        popup_html = f"""
        <div style="
            width:260px;
            font-family:Arial,sans-serif;
            line-height:1.6;
        ">

            <h3 style="color:#2563eb;">
                Community Complaint
            </h3>

            <b>Report ID:</b> {report_id}<br>

            <b>Category:</b> {safe_category}<br>

            <b>Locality:</b> {safe_locality}<br>

            <b>District:</b> {safe_district}<br>

            <b>State:</b> {safe_state}<br>

            <b>Status:</b> {safe_status}<br>

            <b>Priority:</b> {safe_priority}<br>

            <hr>

            <b>Description:</b><br>

            {safe_description}

        </div>
        """

        # --------------------------------------------------
        # ADD MARKER
        # --------------------------------------------------

        folium.Marker(

            location=[
                latitude,
                longitude
            ],

            tooltip=(
                f"{safe_category} - "
                f"{safe_locality}"
            ),

            popup=folium.Popup(
                popup_html,
                max_width=320
            ),

            icon=folium.Icon(
                color=color,
                icon="info-sign"
            )

        ).add_to(complaint_map)

        plotted_locations.append(
            (latitude, longitude)
        )

    # --------------------------------------------------
    # FIT MAP TO ALL LOCATIONS
    # --------------------------------------------------

    if plotted_locations:

        complaint_map.fit_bounds(
            plotted_locations,
            padding=(40, 40)
        )

    return (
        complaint_map,
        len(plotted_locations),
        skipped_locations
    )


# ==================================================
# DISPLAY COMMUNITY ISSUE MAP
# ==================================================

def display_complaint_map(reports):

    st.subheader("Community Issue Map")

    st.caption(
        "Explore community complaints across India. "
        "Click a map marker to view its complaint details."
    )

    with st.spinner(
        "Searching for complaint locations across India..."
    ):

        (
            complaint_map,
            plotted,
            skipped_locations
        ) = create_complaint_map(reports)

    st_folium(

        complaint_map,

        use_container_width=True,

        height=550,

        returned_objects=[]

    )

    # --------------------------------------------------
    # MAP STATISTICS
    # --------------------------------------------------

    col1, col2 = st.columns(2)

    col1.metric(
        "Complaints on Map",
        plotted
    )

    col2.metric(
        "Locations Not Found",
        len(skipped_locations)
    )

    if plotted > 0:

        st.success(
            f"{plotted} complaint location(s) "
            "successfully displayed."
        )

    if skipped_locations:

        st.warning(
            "Some complaint locations could not be "
            "identified by OpenStreetMap."
        )

        with st.expander("View locations not found"):

            for location in skipped_locations:

                st.write(f"• {location}")

    st.caption(
        "Location markers represent approximate locality "
        "coordinates, not exact incident addresses. "
        "Geocoding is provided by OpenStreetMap Nominatim."
    )
