# -*- coding: utf-8 -*-
"""
scripts/p2_seed_intelligence_db.py
---------------------------------
Seeds the Strategic Intelligence Reference Database used as the SQL source.

Run once before main.py:
    python scripts/p2_seed_intelligence_db.py

Tables seeded
-------------
  countries_of_interest   India's strategic neighbours + major powers
  threat_categories       Taxonomy of threat types
  border_regions          LAC sectors, LoC, maritime zones, flashpoints
  defence_assets          Key Indian defence platforms/systems
  strategic_events_ref    Historical geopolitical events for context
"""

import sqlite3
import sys
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sys
sys.path.insert(0, str(project_root))
from src.ingestion.p2_framework.p2_config import INTEL_DB_PATH  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def seed_countries(cur: sqlite3.Cursor) -> None:
    cur.execute("DROP TABLE IF EXISTS countries_of_interest")
    cur.execute("""
        CREATE TABLE countries_of_interest (
            id                  TEXT PRIMARY KEY,
            country_name        TEXT NOT NULL,
            iso3_code           TEXT,
            region              TEXT,
            threat_level        TEXT,   -- HIGH / MODERATE / MONITOR / REFERENCE / SELF
            alliance_status     TEXT,   -- ADVERSARY / NEUTRAL / PARTNER / ALLY / SELF
            border_length_km    INTEGER,
            shares_border       INTEGER DEFAULT 0,  -- 1=yes
            nuclear_power       INTEGER DEFAULT 0,  -- 1=yes
            un_security_council INTEGER DEFAULT 0,
            active_disputes     TEXT,   -- comma-separated dispute zones
            mil_personnel_est   INTEGER,
            notes               TEXT
        )
    """)
    countries = [
        # id    name               iso3  region           threat    alliance      border  border nuke  unsc  disputes                                             mil_est  notes
        ("IN", "India",            "IND","South Asia",    "SELF",   "SELF",       0,      0,     1,    0,    "",                                                 1450000, "Framework operator nation"),
        ("CN", "China",            "CHN","East Asia",     "HIGH",   "ADVERSARY",  3488,   1,     1,    1,    "LAC,Arunachal Pradesh,Aksai Chin,Doklam,Depsang",  2000000, "Primary strategic competitor; 1962 war; ongoing LAC tensions"),
        ("PK", "Pakistan",         "PAK","South Asia",    "HIGH",   "ADVERSARY",  3323,   1,     1,    0,    "LoC,Siachen,Sir Creek,Kashmir",                    650000,  "Multiple wars; proxy conflict; nuclear-armed; China ally"),
        ("NP", "Nepal",            "NPL","South Asia",    "MONITOR","NEUTRAL",    1751,   1,     0,    0,    "Susta,Kalapani,Limpiyadhura",                      96000,   "Recent China tilt; border disputes resurging"),
        ("BD", "Bangladesh",       "BGD","South Asia",    "MONITOR","PARTNER",    4096,   1,     0,    0,    "",                                                 160000,  "Generally friendly; monitor Rohingya spillover"),
        ("LK", "Sri Lanka",        "LKA","South Ocean",  "MONITOR","NEUTRAL",    0,      0,     0,    0,    "Katchatheevu",                                     260000,  "Chinese port at Hambantota; strategic Indian Ocean"),
        ("MM", "Myanmar",          "MMR","Southeast Asia","MODERATE","NEUTRAL",  1643,   1,     0,    0,    "Manipur insurgency spillover",                     400000,  "Junta-China ties; insurgent corridors into Northeast India"),
        ("AF", "Afghanistan",      "AFG","Central Asia",  "MODERATE","NEUTRAL",  106,    1,     0,    0,    "Durand Line disputes; proxy terror",               0,       "Taliban control; TTP; terror pipeline to J&K"),
        ("RU", "Russia",           "RUS","Eurasia",       "REFERENCE","PARTNER", 0,      0,     1,    1,    "",                                                 850000,  "Major arms supplier (60%+ Indian inventory); S-400"),
        ("US", "United States",    "USA","Americas",      "REFERENCE","ALLY",    0,      0,     1,    1,    "",                                                 1400000, "QUAD partner; defence cooperation; technology transfer"),
        ("IR", "Iran",             "IRN","Middle East",   "MODERATE","NEUTRAL",  0,      0,     0,    0,    "Chabahar port strategic interest",                 580000,  "Chabahar connectivity; Gulf of Oman"),
        ("SA", "Saudi Arabia",     "SAU","Middle East",   "REFERENCE","NEUTRAL", 0,      0,     0,    0,    "",                                                 230000,  "Gulf security; large Indian diaspora"),
        ("JP", "Japan",            "JPN","East Asia",     "REFERENCE","ALLY",    0,      0,     0,    0,    "",                                                 250000,  "QUAD partner; shared China concerns"),
        ("AU", "Australia",        "AUS","Oceania",       "REFERENCE","ALLY",    0,      0,     0,    0,    "",                                                 58000,   "QUAD partner; AUKUS; Indian Ocean cooperation"),
        ("IL", "Israel",           "ISR","Middle East",   "REFERENCE","PARTNER", 0,      0,     1,    0,    "",                                                 169500,  "Major defence supplier; drones, radar, missiles"),
    ]
    cur.executemany(
        "INSERT INTO countries_of_interest VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        countries,
    )
    print(f"  [OK] countries_of_interest: {len(countries)} rows")


def seed_threat_categories(cur: sqlite3.Cursor) -> None:
    cur.execute("DROP TABLE IF EXISTS threat_categories")
    cur.execute("""
        CREATE TABLE threat_categories (
            id              INTEGER PRIMARY KEY,
            category        TEXT NOT NULL,
            subcategory     TEXT,
            description     TEXT,
            primary_actors  TEXT,
            threat_domains  TEXT,
            priority        TEXT   -- CRITICAL / HIGH / MEDIUM / LOW
        )
    """)
    threats = [
        (1,  "Conventional Military",  "Land Warfare",          "Large-scale ground force operations across international borders",        "China,Pakistan",              "LAC,LoC",                       "CRITICAL"),
        (2,  "Conventional Military",  "Air Power",             "Air strikes, air superiority operations, drone warfare",                  "China,Pakistan",              "Airspace",                      "CRITICAL"),
        (3,  "Conventional Military",  "Naval/Maritime",        "Sea-lane disruption, IOR presence, submarine activity",                   "China,Pakistan",              "Indian Ocean,Bay of Bengal",    "HIGH"),
        (4,  "Nuclear",                "Strategic Deterrence",  "Nuclear weapons capability, ballistic missile threats",                   "China,Pakistan",              "Entire country",                "CRITICAL"),
        (5,  "Cyber",                  "Infrastructure Attack", "Attacks on power grids, military networks, financial systems",            "China,Pakistan,non-state",    "Cyberspace",                    "HIGH"),
        (6,  "Cyber",                  "Espionage",             "Data exfiltration, intelligence gathering from defence networks",         "China",                       "Cyberspace",                    "HIGH"),
        (7,  "Hybrid",                 "Proxy Warfare",         "Funding/arming insurgent and terrorist groups",                           "Pakistan,China",              "J&K,Northeast India",           "HIGH"),
        (8,  "Terrorism",              "Cross-border",          "Infiltration of armed militants across LoC into India",                   "Pakistan (ISI)",              "J&K,Punjab",                    "HIGH"),
        (9,  "Terrorism",              "Domestic",              "Naxal insurgency, Northeast separatism",                                  "Non-state actors",            "Central India,Northeast",       "MEDIUM"),
        (10, "Information Warfare",    "Disinformation",        "Propaganda, fake news, social media manipulation targeting Indian public", "China,Pakistan",              "Social media,News",             "MEDIUM"),
        (11, "Economic Coercion",      "Trade/Supply Chain",    "Dependence on adversary supply chains; sanctions risk",                   "China",                       "Technology,Pharma,Electronics", "MEDIUM"),
        (12, "Space",                  "Anti-satellite",        "ASAT weapons, jamming of military satellites",                            "China",                       "Space,GPS",                     "HIGH"),
    ]
    cur.executemany(
        "INSERT INTO threat_categories VALUES (?,?,?,?,?,?,?)",
        threats,
    )
    print(f"  [OK] threat_categories: {len(threats)} rows")


def seed_border_regions(cur: sqlite3.Cursor) -> None:
    cur.execute("DROP TABLE IF EXISTS border_regions")
    cur.execute("""
        CREATE TABLE border_regions (
            id              INTEGER PRIMARY KEY,
            region_name     TEXT NOT NULL,
            border_type     TEXT,        -- LAC / LOC / IB / Maritime / Disputed
            adjacent_country TEXT,
            length_km       INTEGER,
            status          TEXT,        -- Active / Stable / Tense / Frozen
            key_flashpoints TEXT,
            terrain         TEXT,
            strategic_importance TEXT,
            last_major_incident TEXT
        )
    """)
    borders = [
        # LAC Sectors (China)
        (1,  "Western LAC (Ladakh)",       "LAC",      "China",    1597, "TENSE",  "Depsang,Gogra,Hot Springs,Galwan", "High altitude desert",    "CRITICAL - Aksai Chin access; 2020 Galwan clash",      "June 2020 Galwan Valley clash"),
        (2,  "Depsang Plains",             "LAC",      "China",    120,  "TENSE",  "Y-junction,Bottleneck",            "High altitude plains",    "HIGH - Chinese incursions restricting patrolling",     "2022 face-off"),
        (3,  "Doklam Plateau",             "LAC",      "China",    89,   "TENSE",  "Doklam,Gymochen",                  "High altitude plateau",   "HIGH - Bhutan corridor; Siliguri Chicken Neck threat", "2017 Doklam standoff"),
        (4,  "Central LAC (Uttarakhand)",  "LAC",      "China",    545,  "STABLE", "Barahoti",                         "Himalayan alpine",        "MEDIUM - Relatively quiet but monitored",              "2015 Barahoti"),
        (5,  "Eastern LAC (Arunachal)",    "LAC",      "China",    1126, "TENSE",  "Tawang,Asaphila,Yangtse",          "Dense forest highland",   "CRITICAL - China claims entire Arunachal Pradesh",     "Dec 2022 Yangtse clash"),
        (6,  "Sikkim LAC",                 "LAC",      "China",    220,  "STABLE", "Nathu La,Jelep La",                "Mountain passes",         "HIGH - Strategic passes; trade corridor",              "2017 Doklam"),
        # LoC (Pakistan)
        (7,  "Kashmir LoC (North)",        "LOC",      "Pakistan", 740,  "ACTIVE", "Gurez,Keran,Kupwara",              "Dense forest mountain",   "CRITICAL - Heavy infiltration zone",                   "Ongoing ceasefire violations"),
        (8,  "Kashmir LoC (Central)",      "LOC",      "Pakistan", 420,  "ACTIVE", "Uri,Baramulla,Tangdhar",           "River valley mountain",   "CRITICAL - 2016 Uri attack corridor",                  "2016 Uri terror attack"),
        (9,  "Kashmir LoC (South)",        "LOC",      "Pakistan", 380,  "ACTIVE", "Poonch,Rajouri,Nowshera",          "Mountain ridge",          "HIGH - Infiltration; IED corridor",                    "2021 Poonch ambush"),
        (10, "Siachen Glacier",            "LOC",      "Pakistan", 76,   "FROZEN", "NJ9842,Saltoro Ridge,Bilafond La", "Extreme altitude glacier", "HIGH - World's highest battlefield; AGPL",            "1984 Operation Meghdoot"),
        (11, "Sir Creek",                  "Maritime", "Pakistan", 96,   "STABLE", "Sir Creek estuary",                "Tidal mudflat/marsh",     "MEDIUM - Maritime boundary dispute",                   "Ongoing arbitration"),
        # International Borders
        (12, "India-Nepal IB",             "IB",       "Nepal",    1751, "STABLE", "Kalapani,Limpiyadhura,Susta",      "Terai plains + hills",   "MEDIUM - Resurging disputes; Nepal-China proximity",   "2020 Kalapani dispute"),
        (13, "India-Bangladesh IB",        "IB",       "Bangladesh",4096,"STABLE", "Chitmahal (resolved)",             "Riverine/flat",           "MEDIUM - Rohingya spillover; smuggling corridors",     "Land boundary agreement 2015"),
        (14, "India-Myanmar IB",           "IB",       "Myanmar",  1643, "TENSE",  "Manipur FMR zone,Mizoram",         "Jungle/Hill",             "HIGH - Insurgent free movement; arms smuggling",       "2023 FMR removal announced"),
        (15, "India-Afghanistan IB",       "IB",       "Afghanistan",106, "TENSE", "Durand Line (not recognised by Af)","Mountain",               "HIGH - Taliban; TTP; terror pipeline to J&K",          "2021 Taliban takeover"),
        # Maritime Zones
        (16, "Arabian Sea (West)",         "Maritime", "Pakistan", 0,    "ACTIVE", "Karachi approaches,Makran coast",  "Open ocean",              "HIGH - Pakistan submarine patrols; Chinese IOR presence","2024 P-8I patrol"),
        (17, "Bay of Bengal (East)",       "Maritime", "Bangladesh",0,   "STABLE", "Andaman Sea,Malacca approaches",   "Open ocean",              "HIGH - China String of Pearls; submarine tracking",    "Ongoing PLAN patrols"),
        (18, "Indian Ocean Region (IOR)",  "Maritime", "China",    0,    "TENSE",  "Hambantota,Gwadar,Djibouti",       "Open ocean",              "CRITICAL - PLAN IOR expansion; base development",      "2022 Chinese spy ship near Andamans"),
    ]
    cur.executemany(
        "INSERT INTO border_regions VALUES (?,?,?,?,?,?,?,?,?,?)",
        borders,
    )
    print(f"  [OK] border_regions: {len(borders)} rows")


def seed_defence_assets(cur: sqlite3.Cursor) -> None:
    cur.execute("DROP TABLE IF EXISTS defence_assets")
    cur.execute("""
        CREATE TABLE defence_assets (
            id              INTEGER PRIMARY KEY,
            asset_name      TEXT NOT NULL,
            category        TEXT,      -- Aircraft / Missile / Ship / Ground / Space / Cyber
            service         TEXT,      -- Army / Navy / IAF / DRDO / Strategic Forces
            origin          TEXT,      -- India / Russia / France / Israel / USA
            status          TEXT,      -- Operational / Under induction / Development / Decommissioned
            quantity        TEXT,
            capability      TEXT,
            strategic_role  TEXT
        )
    """)
    assets = [
        # IAF Assets
        (1,  "Rafale",              "Aircraft",  "IAF",              "France",  "Operational",     "36 (+ 26 naval order)", "4.5 gen multirole; METEOR BVR; SCALP cruise missile",   "Air superiority vs PLAAF J-20; Pakistan JF-17"),
        (2,  "Su-30 MKI",          "Aircraft",  "IAF",              "Russia",  "Operational",     "260",                   "Air superiority; ground attack; BRAHMOS integration",    "Primary strike platform; LAC/LoC air defence"),
        (3,  "Tejas Mk1A",         "Aircraft",  "IAF/DRDO-HAL",    "India",   "Under induction", "83 ordered",            "4.5 gen light combat; AESA radar (ordered)",            "Atmanirbhar Bharat; replace MiG-21"),
        (4,  "AMCA",               "Aircraft",  "IAF/DRDO-ADA",    "India",   "Development",     "Prototype stage",       "5th gen stealth; twin engine; supercruise",              "Long term; counter J-20; sovereignty in air power"),
        (5,  "Prachand (LCH)",     "Helicopter","Army/IAF",         "India",   "Operational",     "15+ inducted",          "High altitude attack heli; operates at 6500m",          "Siachen/LAC; world's only high-altitude attack heli"),
        # Missile Systems
        (6,  "BRAHMOS",            "Missile",   "Army/Navy/IAF",    "India-Russia","Operational", "Fleet wide",            "Mach 2.8 supersonic cruise missile; 300-450km range",    "Precision strike; anti-ship; land attack"),
        (7,  "Agni-V",             "Missile",   "Strategic Forces", "India",   "Operational",     "Undisclosed",           "ICBM; 5000-8000km range; MIRV capable",                 "Nuclear deterrence vs China"),
        (8,  "Prithvi-II",         "Missile",   "Army",             "India",   "Operational",     "Undisclosed",           "SRBM; 350km; nuclear capable",                          "Battlefield nuclear deterrence vs Pakistan"),
        (9,  "S-400 Triumf",       "Missile",   "IAF",              "Russia",  "Operational",     "3 of 5 sqns inducted",  "400km range; engages aircraft/missiles/drones",         "Counter PLAAF/PAF; Lahore-Delhi threat axis"),
        (10, "Akash-NG",           "Missile",   "IAF/Army",         "India",   "Under induction", "Multiple batteries",    "Medium range SAM; Mach 3.5; AI-guided",                 "Atmanirbhar air defence; replace old Akash"),
        # Naval Assets
        (11, "INS Vikrant (IAC-1)","Ship",      "Navy",             "India",   "Operational",     "1 carrier",             "Aircraft carrier; 36 aircraft; Rafale-M in future",     "IOR power projection; counter PLAN carriers"),
        (12, "INS Vikramaditya",   "Ship",      "Navy",             "Russia",  "Operational",     "1 carrier",             "Aircraft carrier; 30 MiG-29K",                          "Arabian Sea; IOR presence"),
        (13, "Arihant class SSBN", "Ship",      "Navy",             "India",   "Operational",     "2+ (1 operational)",    "Nuclear ballistic missile submarine; K-15 (750km)",     "Sea-based nuclear deterrence; second strike"),
        (14, "P-8I Poseidon",      "Aircraft",  "Navy",             "USA",     "Operational",     "12",                    "Maritime patrol; ASW; ISR; anti-submarine",             "PLAN submarine tracking; IOR surveillance"),
        # Ground Systems
        (15, "T-90 Bhishma",       "Tank",      "Army",             "Russia",  "Operational",     "1600+",                 "MBT; 125mm smoothbore; reactive armour",                "Plains/desert warfare; Pakistan front"),
        (16, "Arjun Mk1A",         "Tank",      "Army/DRDO",        "India",   "Operational",     "118 ordered",           "MBT; 120mm rifle; ERA; Israeli thermal sight",          "Atmanirbhar; Thar desert vs Pakistan"),
        (17, "K9 Vajra SPH",       "Artillery", "Army",             "India-S.Korea","Operational","100+",                  "155mm self-propelled howitzer; 40km range",             "LAC; high altitude artillery modernisation"),
        (18, "Dhanush",            "Artillery", "Army/OFB",         "India",   "Operational",     "114 ordered",           "155mm towed howitzer; 38km range; Bofors lineage",      "Atmanirbhar artillery; LAC deployment"),
        # DRDO / Space / Cyber
        (19, "ASAT (Mission Shakti)","Space",   "DRDO/SFC",         "India",   "Operational",     "Capability demonstrated","Low earth orbit ASAT; direct-ascent kinetic kill",     "Counter Chinese and Pakistani military satellites"),
        (20, "RISAT-2BR1",         "Space",     "ISRO/Army",        "India",   "Operational",     "Constellation",         "Synthetic aperture radar; all-weather ISR",             "Border surveillance; LAC/LoC monitoring"),
        (21, "Tapas UAV",          "UAV",       "DRDO",             "India",   "Development",     "Certification stage",   "Medium altitude long endurance; ISR",                   "Replacement for Heron; Atmanirbhar surveillance"),
        (22, "Harop",              "UAV/Loitering","Army",          "Israel",  "Operational",     "Fleet inducted",        "Loitering munition; anti-radiation; kamikaze",          "Counter radar/AD; Pakistani forward assets"),
        (23, "Prachand LCH",       "Helicopter","Army",             "India",   "Operational",     "10+ Army order",        "High-altitude attack; 20mm cannon; air-to-air",         "LAC mountain warfare; anti-infantry/armour"),
        (24, "Naval LCA Tejas",    "Aircraft",  "Navy",             "India",   "Development",     "Prototype tested",      "Carrier-based combat aircraft; twin engine variant",    "INS Vikrant air wing; Atmanirbhar naval aviation"),
        (25, "ABHYAS target drone","UAV",       "DRDO",             "India",   "Operational",     "Fleet operational",     "Aerial target; radar cross-section simulation",         "Air defence training; SAM system testing"),
    ]
    cur.executemany(
        "INSERT INTO defence_assets VALUES (?,?,?,?,?,?,?,?,?)",
        assets,
    )
    print(f"  [OK] defence_assets: {len(assets)} rows")


def seed_strategic_events(cur: sqlite3.Cursor) -> None:
    cur.execute("DROP TABLE IF EXISTS strategic_events_ref")
    cur.execute("""
        CREATE TABLE strategic_events_ref (
            id              INTEGER PRIMARY KEY,
            event_date      TEXT,
            event_name      TEXT NOT NULL,
            category        TEXT,
            countries       TEXT,
            location        TEXT,
            outcome         TEXT,
            strategic_lesson TEXT
        )
    """)
    events = [
        (1,  "1962-10-20", "Sino-Indian War",                   "Conventional War",    "India,China",         "NEFA,Aksai Chin",       "Indian defeat; territory lost",                  "Border unresolved; never trust Chinese assurances"),
        (2,  "1965-08-01", "Indo-Pakistani War 1965",            "Conventional War",    "India,Pakistan",      "Kashmir,Punjab",        "Ceasefire; status quo ante",                     "Armour operations in Thar; Rann of Kutch lesson"),
        (3,  "1971-12-03", "Indo-Pakistani War 1971",            "Conventional War",    "India,Pakistan",      "East/West Pakistan",    "Pakistan split; Bangladesh created",             "Joint ops; naval blockade decisive; intelligence key"),
        (4,  "1974-05-18", "Operation Smiling Buddha",           "Nuclear Test",        "India",               "Pokhran, Rajasthan",    "India's first nuclear test",                     "Nuclear deterrence program established"),
        (5,  "1984-04-17", "Operation Meghdoot",                 "Military Ops",        "India,Pakistan",      "Siachen Glacier",       "India occupies Siachen; holds to date",          "Preemptive action; logistics at altitude critical"),
        (6,  "1987-01-01", "Operation Brasstacks",               "Crisis",              "India,Pakistan",      "Rajasthan border",      "De-escalation through diplomacy",                "Large scale exercises as coercion; back-channel vital"),
        (7,  "1988-06-01", "Operation Cactus",                   "Intervention",        "India,Maldives",      "Maldives",              "Coup foiled; CRPF deployed by air",              "Rapid deployment; IOR influence projection"),
        (8,  "1998-05-11", "Operation Shakti (Pokhran-II)",      "Nuclear Test",        "India",               "Pokhran, Rajasthan",    "India declared nuclear power; US sanctions",     "Nuclear triad; credible minimum deterrence doctrine"),
        (9,  "1999-05-01", "Kargil War",                         "Conventional War",    "India,Pakistan",      "Kargil, J&K",           "Pakistan ejected; Indian victory",               "High altitude warfare; air power key; ISR gaps exposed"),
        (10, "1999-08-10", "IC 814 Hijack",                      "Terrorism",           "Pakistan,Afghanistan","Kandahar",              "Hijackers freed; intelligence failure",          "Hostage situation; CT protocol gaps; Pakistan state role"),
        (11, "2001-12-13", "Parliament Attack",                  "Terrorism",           "India,Pakistan",      "New Delhi",             "Standoff; Operation Parakram mobilisation",      "Cross-border terror; coercive diplomacy limits"),
        (12, "2008-11-26", "26/11 Mumbai Attack",                "Terrorism",           "India,Pakistan",      "Mumbai",                "166 killed; diplomatic rupture",                 "Maritime infiltration; ISI-LeT; coastal security gaps"),
        (13, "2016-09-29", "Surgical Strikes",                   "Military Ops",        "India,Pakistan",      "LoC, J&K",              "Terror launch pads destroyed; escalation managed","Sub-conventional; para SF; information ops critical"),
        (14, "2017-06-18", "Doklam Standoff",                    "Crisis",              "India,China,Bhutan",  "Doklam Plateau",        "72-day standoff; mutual withdrawal",             "Proxy border; Siliguri corridor; multilateral signalling"),
        (15, "2019-02-14", "Pulwama Attack",                     "Terrorism",           "India,Pakistan",      "Pulwama, J&K",          "40 CRPF killed; national outrage",               "Vehicle-borne IED; intelligence failure; JeM role"),
        (16, "2019-02-26", "Balakot Air Strike",                 "Military Ops",        "India,Pakistan",      "Balakot, KPK, Pakistan","JeM camp hit; Pakistan F-16 downed; de-escalation","First cross-border air strike since 1971; escalation mgmt"),
        (17, "2020-06-15", "Galwan Valley Clash",                "Border Clash",        "India,China",         "Galwan, Ladakh",        "20 Indian+40+ Chinese soldiers killed",          "LAC patrol rights; buffer zones; PLA aggression pattern"),
        (18, "2020-08-05", "Kailash Range Occupation",           "Military Ops",        "India",               "South Pangong, Ladakh", "India occupied heights; China backed off in 2021","Preemptive ridge seizure; leverage in negotiations"),
        (19, "2022-12-09", "Yangtse Clash (Arunachal)",          "Border Clash",        "India,China",         "Yangtse, Arunachal",    "PLA repulsed; no territory lost",                "Eastern LAC vulnerability; drone recon gaps"),
        (20, "2023-06-01", "Manipur Violence",                   "Internal Security",   "India",               "Manipur",               "Ethnic conflict; army deployed",                 "Northeast security; Myanmar border; arms smuggling"),
        (21, "2024-01-01", "Red Sea Crisis",                     "Maritime Security",   "Multi-nation",        "Red Sea,Bab el-Mandeb", "Indian Navy deployed; escort missions",          "IOR/global trade lane security; expeditionary capability"),
        (22, "2024-09-01", "QUAD Summit",                        "Diplomacy",           "India,USA,Japan,AU",  "New Delhi",             "Indo-Pacific security framework advanced",       "Alliance building; counter-China; tech+mil cooperation"),
        (23, "2025-02-01", "Pahalgam Terror Attack",             "Terrorism",           "India,Pakistan",      "Pahalgam, J&K",         "Civilians killed; India-Pakistan crisis",         "Tourist targets; TRF-Pakistan link; escalation ladder"),
        (24, "2025-05-07", "Operation Sindoor",                  "Military Ops",        "India,Pakistan",      "Pakistan,PoK",          "Precision strikes on 9 terror camps; ceasefire",  "Multi-domain strike; S-400 tested; drone swarm use"),
        (25, "2026-01-01", "PLAN IOR Deployment Increase",       "Maritime Intel",      "China",               "Indian Ocean",          "PLA Navy expanded IOR footprint",                "String of Pearls; Gwadar-Djibouti submarine bases"),
    ]
    cur.executemany(
        "INSERT INTO strategic_events_ref VALUES (?,?,?,?,?,?,?,?)",
        events,
    )
    print(f"  [OK] strategic_events_ref: {len(events)} rows")


def main() -> None:
    print("\nSeeding Strategic Intelligence Reference Database...")
    INTEL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(INTEL_DB_PATH)
    cur  = conn.cursor()

    seed_countries(cur)
    seed_threat_categories(cur)
    seed_border_regions(cur)
    seed_defence_assets(cur)
    seed_strategic_events(cur)

    conn.commit()
    conn.close()
    print(f"\n  Database: {INTEL_DB_PATH}")
    print("  Intelligence DB seeded successfully.\n")


if __name__ == "__main__":
    main()
