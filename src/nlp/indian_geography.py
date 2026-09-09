"""
Indian Geography Knowledge Base
================================

Comprehensive dictionary of Indian administrative divisions, strategic
locations, military installations, and common location aliases.

Used by the location extractor for:
1. Normalization (Bombay → Mumbai, Madras → Chennai)
2. Hierarchy inference (city → district → state → country)
3. Location type classification (border area, military installation, etc.)
4. Recognition of strategic/military locations
"""

# ============================================================================
# LOCATION ALIASES / NORMALIZATION
# ============================================================================

LOCATION_ALIASES: dict[str, str] = {
    # Major cities — historical to modern
    "bombay": "Mumbai",
    "madras": "Chennai",
    "calcutta": "Kolkata",
    "bangalore": "Bengaluru",
    "poona": "Pune",
    "baroda": "Vadodara",
    "cawnpore": "Kanpur",
    "allahabad": "Prayagraj",
    "benares": "Varanasi",
    "mussoorie": "Mussoorie",
    "simla": "Shimla",
    "ooty": "Ooty",
    "pondicherry": "Puducherry",
    "trivandrum": "Thiruvananthapuram",
    "cochin": "Kochi",
    "calicut": "Kozhikode",
    "trichur": "Thrissur",
    "coimbatore": "Coimbatore",
    "trichy": "Tiruchirappalli",
    "tiruchirappalli": "Tiruchirappalli",
    "ahmednagar": "Ahilyanagar",
    "aurangabad": "Chhatrapati Sambhajinagar",
    "osmanabad": "Dharashiv",
    "ratnagiri": "Ratnagiri",

    # States — historical / regional spellings / common misspellings
    "tamilnadu": "Tamil Nadu",
    "tamil nadu": "Tamil Nadu",
    "maharashtra": "Maharashtra",
    "andhra": "Andhra Pradesh",
    "telangana": "Telangana",
    "telengana": "Telangana",
    "uttaranchal": "Uttarakhand",
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
    "j&k": "Jammu & Kashmir",
    "j & k": "Jammu & Kashmir",
    "jammu kashmir": "Jammu & Kashmir",
    "jammu and kashmir": "Jammu & Kashmir",
    "kashmeer": "Jammu & Kashmir",
    "kashmir": "Jammu & Kashmir",
    "ladak": "Ladakh",
    "arunachal": "Arunachal Pradesh",
    "chattisgarh": "Chhattisgarh",
    "chhattisgarh": "Chhattisgarh",
    "bengal": "West Bengal",
    "himachal": "Himachal Pradesh",
    "manipur": "Manipur",

    # International borders / regions
    "loc": "Line of Control",
    "line of control": "Line of Control",
    "lac": "Line of Actual Control",
    "line of actual control": "Line of Actual Control",
    "imb": "Indo-Myanmar Border",
    "ib": "International Border",
}


# ============================================================================
# KNOWN COUNTRIES
# ============================================================================

KNOWN_COUNTRIES: set[str] = {
    "India", "China", "Pakistan", "Russia", "United States", "USA",
    "France", "Israel", "Japan", "Australia", "United Kingdom", "UK",
    "Germany", "Italy", "Spain", "South Korea", "North Korea",
    "Iran", "Saudi Arabia", "UAE", "Turkey",
    "Bangladesh", "Nepal", "Sri Lanka", "Maldives", "Bhutan",
    "Myanmar", "Afghanistan",
    "Indonesia", "Vietnam", "Philippines", "Thailand", "Malaysia",
    "Singapore", "Taiwan", "Ukraine", "Canada", "Egypt",
}


# ============================================================================
# STATE / UNION TERRITORY LOOKUP
# ============================================================================

INDIAN_STATES: set[str] = {
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    # Union Territories
    "Jammu & Kashmir", "Ladakh", "Delhi", "Chandigarh",
    "Puducherry", "Dadra and Nagar Haveli and Daman and Diu",
    "Lakshadweep", "Andaman and Nicobar Islands",
}

# State aliases for lookup
STATE_ALIASES: dict[str, str] = {
    "j&k": "Jammu & Kashmir",
    "j & k": "Jammu & Kashmir",
    "jammu": "Jammu & Kashmir",
    "kashmir": "Jammu & Kashmir",
    "ap": "Andhra Pradesh",
    "mp": "Madhya Pradesh",
    "up": "Uttar Pradesh",
    "uk": "Uttarakhand",
    "hp": "Himachal Pradesh",
    "northeast": None,  # Region, not a state
    "north east": None,
    "north east india": None,
}


# ============================================================================
# CITY → STATE MAPPING (major cities)
# ============================================================================

CITY_TO_STATE: dict[str, str] = {
    # Maharashtra
    "Mumbai": "Maharashtra",
    "Pune": "Maharashtra",
    "Nagpur": "Maharashtra",
    "Nashik": "Maharashtra",
    "Aurangabad": "Maharashtra",
    "Chhatrapati Sambhajinagar": "Maharashtra",
    "Ahilyanagar": "Maharashtra",
    "Ahmednagar": "Maharashtra",
    "Kolhapur": "Maharashtra",
    "Solapur": "Maharashtra",
    "Nanded": "Maharashtra",
    "Amravati": "Maharashtra",
    "Thane": "Maharashtra",
    "Ratnagiri": "Maharashtra",
    "Sindhudurg": "Maharashtra",
    "Talegaon": "Maharashtra",
    "Deolali": "Maharashtra",
    "Kirkee": "Maharashtra",
    "Khadki": "Maharashtra",

    # Tamil Nadu
    "Chennai": "Tamil Nadu",
    "Coimbatore": "Tamil Nadu",
    "Madurai": "Tamil Nadu",
    "Tiruchirappalli": "Tamil Nadu",
    "Salem": "Tamil Nadu",
    "Tirunelveli": "Tamil Nadu",
    "Vellore": "Tamil Nadu",
    "Wellington": "Tamil Nadu",

    # Karnataka
    "Bengaluru": "Karnataka",
    "Mysuru": "Karnataka",
    "Hubballi": "Karnataka",
    "Dharwad": "Karnataka",
    "Belagavi": "Karnataka",

    # Rajasthan
    "Jaipur": "Rajasthan",
    "Jodhpur": "Rajasthan",
    "Udaipur": "Rajasthan",
    "Bikaner": "Rajasthan",
    "Alwar": "Rajasthan",
    "Kota": "Rajasthan",
    "Barmer": "Rajasthan",
    "Jaisalmer": "Rajasthan",
    "Pokhran": "Rajasthan",
    "Suratgarh": "Rajasthan",

    # Punjab
    "Amritsar": "Punjab",
    "Ludhiana": "Punjab",
    "Chandigarh": "Punjab",
    "Pathankot": "Punjab",
    "Jalandhar": "Punjab",
    "Firozpur": "Punjab",
    "Bhatinda": "Punjab",
    "Adampur": "Punjab",

    # Haryana
    "Gurugram": "Haryana",
    "Faridabad": "Haryana",
    "Ambala": "Haryana",
    "Hisar": "Haryana",
    "Sirsa": "Haryana",

    # Delhi
    "Delhi": "Delhi",
    "New Delhi": "Delhi",

    # Uttar Pradesh
    "Lucknow": "Uttar Pradesh",
    "Agra": "Uttar Pradesh",
    "Varanasi": "Uttar Pradesh",
    "Prayagraj": "Uttar Pradesh",
    "Kanpur": "Uttar Pradesh",
    "Mathura": "Uttar Pradesh",
    "Meerut": "Uttar Pradesh",
    "Bareilly": "Uttar Pradesh",

    # Gujarat
    "Ahmedabad": "Gujarat",
    "Surat": "Gujarat",
    "Vadodara": "Gujarat",
    "Rajkot": "Gujarat",
    "Porbandar": "Gujarat",
    "Bhuj": "Gujarat",
    "Jamnagar": "Gujarat",
    "Kandla": "Gujarat",

    # Madhya Pradesh
    "Bhopal": "Madhya Pradesh",
    "Indore": "Madhya Pradesh",
    "Jabalpur": "Madhya Pradesh",
    "Gwalior": "Madhya Pradesh",
    "Sagar": "Madhya Pradesh",

    # Himachal Pradesh
    "Shimla": "Himachal Pradesh",
    "Dharamsala": "Himachal Pradesh",
    "Manali": "Himachal Pradesh",
    "Spiti": "Himachal Pradesh",
    "Kullu": "Himachal Pradesh",

    # Uttarakhand
    "Dehradun": "Uttarakhand",
    "Haridwar": "Uttarakhand",
    "Rishikesh": "Uttarakhand",
    "Nainital": "Uttarakhand",
    "Roorkee": "Uttarakhand",

    # Jammu & Kashmir
    "Srinagar": "Jammu & Kashmir",
    "Jammu": "Jammu & Kashmir",
    "Anantnag": "Jammu & Kashmir",
    "Kupwara": "Jammu & Kashmir",
    "Poonch": "Jammu & Kashmir",
    "Rajouri": "Jammu & Kashmir",
    "Baramulla": "Jammu & Kashmir",
    "Pulwama": "Jammu & Kashmir",
    "Sopore": "Jammu & Kashmir",
    "Bandipora": "Jammu & Kashmir",

    # Ladakh
    "Leh": "Ladakh",
    "Kargil": "Ladakh",
    "Diskit": "Ladakh",
    "Siachen": "Ladakh",
    "Daulat Beg Oldie": "Ladakh",

    # Sikkim
    "Gangtok": "Sikkim",
    "Namchi": "Sikkim",

    # West Bengal
    "Kolkata": "West Bengal",
    "Siliguri": "West Bengal",
    "Darjeeling": "West Bengal",
    "Jalpaiguri": "West Bengal",
    "Asansol": "West Bengal",

    # Assam
    "Guwahati": "Assam",
    "Dibrugarh": "Assam",
    "Jorhat": "Assam",
    "Tezpur": "Assam",
    "Silchar": "Assam",

    # Manipur
    "Imphal": "Manipur",
    "Churachandpur": "Manipur",
    "Moreh": "Manipur",
    "Bishnupur": "Manipur",

    # Meghalaya
    "Shillong": "Meghalaya",
    "Tura": "Meghalaya",

    # Nagaland
    "Kohima": "Nagaland",
    "Dimapur": "Nagaland",

    # Arunachal Pradesh
    "Itanagar": "Arunachal Pradesh",
    "Tawang": "Arunachal Pradesh",
    "Aalo": "Arunachal Pradesh",

    # Mizoram
    "Aizawl": "Mizoram",

    # Tripura
    "Agartala": "Tripura",

    # Andhra Pradesh / Telangana
    "Hyderabad": "Telangana",
    "Secunderabad": "Telangana",
    "Visakhapatnam": "Andhra Pradesh",
    "Vishakhapatnam": "Andhra Pradesh",
    "Vizag": "Andhra Pradesh",
    "Guntur": "Andhra Pradesh",
    "Vijayawada": "Andhra Pradesh",

    # Kerala
    "Thiruvananthapuram": "Kerala",
    "Kochi": "Kerala",
    "Kozhikode": "Kerala",
    "Thrissur": "Kerala",

    # Goa
    "Panaji": "Goa",
    "Vasco da Gama": "Goa",
    "Margao": "Goa",

    # Bihar
    "Patna": "Bihar",
    "Gaya": "Bihar",
    "Muzaffarpur": "Bihar",

    # Jharkhand
    "Ranchi": "Jharkhand",
    "Jamshedpur": "Jharkhand",

    # Odisha
    "Bhubaneswar": "Odisha",
    "Cuttack": "Odisha",
    "Puri": "Odisha",
    "Chandipur": "Odisha",

    # Chhattisgarh
    "Raipur": "Chhattisgarh",
    "Bilaspur": "Chhattisgarh",
    "Bastar": "Chhattisgarh",
}


# ============================================================================
# STRATEGIC LOCATIONS
# ============================================================================

STRATEGIC_LOCATIONS: dict[str, dict] = {
    # -----------------------------------------------------------------------
    # Border / LOC / LAC Locations
    # -----------------------------------------------------------------------
    "Nathu La": {
        "state": "Sikkim",
        "type": "border_pass",
        "region": "Northeast India",
        "strategic_note": "India-China border pass",
    },
    "Jelep La": {
        "state": "Sikkim",
        "type": "border_pass",
        "region": "Northeast India",
    },
    "Tawang": {
        "state": "Arunachal Pradesh",
        "type": "border_area",
        "region": "Northeast India",
        "strategic_note": "Disputed by China",
    },
    "Bumla": {
        "state": "Arunachal Pradesh",
        "type": "border_pass",
        "region": "Northeast India",
    },
    "Depsang": {
        "state": "Ladakh",
        "type": "border_area",
        "region": "Western Himalayas",
        "strategic_note": "LAC friction point",
    },
    "Galwan Valley": {
        "state": "Ladakh",
        "type": "border_area",
        "region": "Western Himalayas",
        "strategic_note": "June 2020 India-China clash site",
    },
    "Pangong Lake": {
        "state": "Ladakh",
        "type": "border_area",
        "region": "Western Himalayas",
    },
    "Pangong Tso": {
        "state": "Ladakh",
        "type": "border_area",
        "region": "Western Himalayas",
    },
    "Hot Springs": {
        "state": "Ladakh",
        "type": "border_area",
        "region": "Western Himalayas",
    },
    "Gogra": {
        "state": "Ladakh",
        "type": "border_area",
        "region": "Western Himalayas",
    },
    "Daulat Beg Oldie": {
        "state": "Ladakh",
        "type": "military_airstrip",
        "region": "Western Himalayas",
        "strategic_note": "World's highest airstrip",
    },
    "Siachen Glacier": {
        "state": "Ladakh",
        "type": "military_position",
        "region": "Western Himalayas",
        "strategic_note": "World's highest battlefield",
    },
    "Saltoro Ridge": {
        "state": "Ladakh",
        "type": "military_position",
        "region": "Western Himalayas",
    },

    # -----------------------------------------------------------------------
    # LOC — Jammu & Kashmir
    # -----------------------------------------------------------------------
    "Uri": {
        "state": "Jammu & Kashmir",
        "type": "border_area",
        "region": "Jammu & Kashmir",
        "strategic_note": "2016 Army base attack site",
    },
    "Balakot": {
        "state": None,
        "country": "Pakistan",
        "type": "military_target",
        "strategic_note": "2019 Indian Air Force strike target",
    },

    # -----------------------------------------------------------------------
    # Military Installations
    # -----------------------------------------------------------------------
    "NDA Pune": {
        "state": "Maharashtra",
        "type": "military_academy",
        "region": "Western India",
        "full_name": "National Defence Academy, Khadakwasla",
    },
    "Khadakwasla": {
        "state": "Maharashtra",
        "type": "military_academy",
        "region": "Western India",
    },
    "IMA Dehradun": {
        "state": "Uttarakhand",
        "type": "military_academy",
        "full_name": "Indian Military Academy",
    },
    "INS Vikrant": {
        "type": "naval_vessel",
        "strategic_note": "India's aircraft carrier",
    },
    "INS Vikramaditya": {
        "type": "naval_vessel",
        "strategic_note": "India's aircraft carrier",
    },
    "INS Arihant": {
        "type": "submarine",
        "strategic_note": "India's nuclear ballistic missile submarine",
    },
    "Eastern Naval Command": {
        "state": "Andhra Pradesh",
        "city": "Visakhapatnam",
        "type": "military_headquarters",
    },
    "Western Naval Command": {
        "state": "Maharashtra",
        "city": "Mumbai",
        "type": "military_headquarters",
    },
    "Southern Naval Command": {
        "state": "Kerala",
        "city": "Kochi",
        "type": "military_headquarters",
    },
    "Western Air Command": {
        "state": "Delhi",
        "type": "military_headquarters",
    },
    "Eastern Air Command": {
        "state": "Assam",
        "city": "Guwahati",
        "type": "military_headquarters",
    },

    # -----------------------------------------------------------------------
    # Testing Ranges
    # -----------------------------------------------------------------------
    "Pokhran": {
        "state": "Rajasthan",
        "type": "military_test_range",
        "strategic_note": "Nuclear test site",
    },
    "Chandipur": {
        "state": "Odisha",
        "type": "missile_test_range",
        "strategic_note": "Integrated Test Range",
    },
    "Sriharikota": {
        "state": "Andhra Pradesh",
        "type": "space_launch_facility",
        "strategic_note": "ISRO launch facility",
    },
    "Abdul Kalam Island": {
        "state": "Odisha",
        "type": "missile_test_range",
        "strategic_note": "Wheeler Island, DRDO test range",
    },

    # -----------------------------------------------------------------------
    # Northeast Strategic Locations
    # -----------------------------------------------------------------------
    "Moreh": {
        "state": "Manipur",
        "type": "border_town",
        "strategic_note": "India-Myanmar border",
    },
    "Zokhawthar": {
        "state": "Mizoram",
        "type": "border_town",
        "strategic_note": "India-Myanmar border",
    },
    "Dawki": {
        "state": "Meghalaya",
        "type": "border_crossing",
        "strategic_note": "India-Bangladesh border",
    },

    # -----------------------------------------------------------------------
    # Maritime Strategic Points
    # -----------------------------------------------------------------------
    "Andaman Islands": {
        "state": "Andaman and Nicobar Islands",
        "type": "strategic_island",
        "strategic_note": "Controls Malacca Strait access",
    },
    "Car Nicobar": {
        "state": "Andaman and Nicobar Islands",
        "type": "military_base",
    },
    "INS Baaz": {
        "state": "Andaman and Nicobar Islands",
        "type": "naval_air_station",
    },
    "Lakshadweep": {
        "state": "Lakshadweep",
        "type": "strategic_island",
    },
}


# ============================================================================
# REGIONS
# ============================================================================

REGION_MAP: dict[str, list[str]] = {
    "Northeast India": [
        "Assam", "Meghalaya", "Manipur", "Nagaland", "Tripura",
        "Mizoram", "Arunachal Pradesh", "Sikkim",
    ],
    "Western Himalayas": [
        "Ladakh", "Jammu & Kashmir", "Himachal Pradesh", "Uttarakhand",
    ],
    "Eastern Himalayas": [
        "Sikkim", "Arunachal Pradesh", "West Bengal",
    ],
    "Western India": [
        "Rajasthan", "Gujarat", "Maharashtra", "Goa",
    ],
    "Southern India": [
        "Tamil Nadu", "Kerala", "Karnataka", "Andhra Pradesh",
        "Telangana", "Puducherry",
    ],
    "North India": [
        "Punjab", "Haryana", "Delhi", "Uttar Pradesh", "Bihar",
        "Chandigarh",
    ],
    "Central India": [
        "Madhya Pradesh", "Chhattisgarh",
    ],
    "Eastern India": [
        "West Bengal", "Jharkhand", "Odisha",
    ],
    "Indo-Pacific": [],
    "Indian Ocean Region": [],
    "Line of Actual Control": [],
    "Line of Control": [],
}


# State → Region
STATE_TO_REGION: dict[str, str] = {}
for region, states in REGION_MAP.items():
    for state in states:
        STATE_TO_REGION[state] = region


def normalize_location(location: str) -> str:
    """
    Normalize a location string to its canonical name.
    """
    normalized = LOCATION_ALIASES.get(location.lower(), location)
    return normalized


def get_state_for_city(city: str) -> str | None:
    """Return the state for a given city, if known."""
    return CITY_TO_STATE.get(city)


def get_region_for_state(state: str) -> str | None:
    """Return the broader region for a given state."""
    return STATE_TO_REGION.get(state)


def get_strategic_info(location: str) -> dict | None:
    """Return strategic metadata for a known strategic location."""
    return STRATEGIC_LOCATIONS.get(location)


def is_indian_state(location: str) -> bool:
    """Check if a location is an Indian state or UT."""
    return location in INDIAN_STATES
