"""
Portal-only metro seeds — AHJ name + official portal URL, no invented fees/gotchas.

Used when there is no full city pack (Plano/Dallas/Austin). Improves free punch
citeability by giving the CRITICAL “confirm fees” line a real .gov link.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _norm(city: str = "", state: str = "") -> str:
    c = (city or "").strip().lower()
    s = (state or "").strip().lower()
    if s in ("texas",):
        s = "tx"
    if s in ("california",):
        s = "ca"
    if s in ("washington",):
        s = "wa"
    if s in ("new york",):
        s = "ny"
    if s in ("florida",):
        s = "fl"
    return f"{c}, {s}".strip(", ")


# Keys: "city, st" lowercase. portal_only packs are not full fee/gotcha packs.
METRO_PORTAL_SEEDS: Dict[str, Dict[str, Any]] = {
    # West
    "seattle, wa": {
        "city": "Seattle",
        "state": "WA",
        "name": "Seattle Department of Construction & Inspections (SDCI)",
        "portal_url": "https://www.seattle.gov/sdci",
        "phone": "206-684-8600",
    },
    "bellevue, wa": {
        "city": "Bellevue",
        "state": "WA",
        "name": "City of Bellevue Development Services",
        "portal_url": "https://bellevuewa.gov/city-government/departments/development",
    },
    "tacoma, wa": {
        "city": "Tacoma",
        "state": "WA",
        "name": "City of Tacoma Planning & Development Services",
        "portal_url": "https://www.cityoftacoma.org/government/city_departments/planning_and_development_services",
    },
    "portland, or": {
        "city": "Portland",
        "state": "OR",
        "name": "Portland Permitting & Development",
        "portal_url": "https://www.portland.gov/bds",
    },
    "san francisco, ca": {
        "city": "San Francisco",
        "state": "CA",
        "name": "SF Department of Building Inspection",
        "portal_url": "https://www.sf.gov/departments--department-building-inspection",
    },
    "san jose, ca": {
        "city": "San Jose",
        "state": "CA",
        "name": "City of San José Building Division",
        "portal_url": "https://www.sanjoseca.gov/your-government/departments-offices/planning-building-code-enforcement/building-division",
    },
    "los angeles, ca": {
        "city": "Los Angeles",
        "state": "CA",
        "name": "LADBS — Los Angeles Department of Building and Safety",
        "portal_url": "https://www.ladbs.org/",
    },
    "san diego, ca": {
        "city": "San Diego",
        "state": "CA",
        "name": "City of San Diego Development Services",
        "portal_url": "https://www.sandiego.gov/development-services",
    },
    "sacramento, ca": {
        "city": "Sacramento",
        "state": "CA",
        "name": "City of Sacramento Community Development",
        "portal_url": "https://www.cityofsacramento.gov/community-development",
    },
    "oakland, ca": {
        "city": "Oakland",
        "state": "CA",
        "name": "City of Oakland Planning & Building",
        "portal_url": "https://www.oaklandca.gov/departments/planning-and-building",
    },
    "phoenix, az": {
        "city": "Phoenix",
        "state": "AZ",
        "name": "City of Phoenix Planning & Development",
        "portal_url": "https://www.phoenix.gov/pdd",
    },
    "tucson, az": {
        "city": "Tucson",
        "state": "AZ",
        "name": "City of Tucson Planning & Development Services",
        "portal_url": "https://www.tucsonaz.gov/Departments/Planning-Development-Services",
    },
    "las vegas, nv": {
        "city": "Las Vegas",
        "state": "NV",
        "name": "City of Las Vegas Building & Safety",
        "portal_url": "https://www.lasvegasnevada.gov/Business/Building-Safety",
    },
    "denver, co": {
        "city": "Denver",
        "state": "CO",
        "name": "City and County of Denver Community Planning & Development",
        "portal_url": "https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Community-Planning-and-Development",
    },
    "salt lake city, ut": {
        "city": "Salt Lake City",
        "state": "UT",
        "name": "Salt Lake City Building Services",
        "portal_url": "https://www.slc.gov/buildingservices/",
    },
    "albuquerque, nm": {
        "city": "Albuquerque",
        "state": "NM",
        "name": "City of Albuquerque Planning Department",
        "portal_url": "https://www.cabq.gov/planning",
    },
    # Midwest / South
    "chicago, il": {
        "city": "Chicago",
        "state": "IL",
        "name": "City of Chicago Department of Buildings",
        "portal_url": "https://www.chicago.gov/city/en/depts/bldgs.html",
    },
    "columbus, oh": {
        "city": "Columbus",
        "state": "OH",
        "name": "City of Columbus Building & Zoning Services",
        "portal_url": "https://www.columbus.gov/bzs/",
    },
    "cleveland, oh": {
        "city": "Cleveland",
        "state": "OH",
        "name": "City of Cleveland Building & Housing",
        "portal_url": "https://www.clevelandohio.gov/city-hall/departments/building-housing",
    },
    "cincinnati, oh": {
        "city": "Cincinnati",
        "state": "OH",
        "name": "City of Cincinnati Buildings & Inspections",
        "portal_url": "https://www.cincinnati-oh.gov/buildings/",
    },
    "indianapolis, in": {
        "city": "Indianapolis",
        "state": "IN",
        "name": "City of Indianapolis Department of Business & Neighborhood Services",
        "portal_url": "https://www.indy.gov/agency/department-of-business-and-neighborhood-services",
    },
    "detroit, mi": {
        "city": "Detroit",
        "state": "MI",
        "name": "City of Detroit Buildings, Safety Engineering & Environmental",
        "portal_url": "https://detroitmi.gov/departments/buildings-safety-engineering-and-environmental-department",
    },
    "minneapolis, mn": {
        "city": "Minneapolis",
        "state": "MN",
        "name": "City of Minneapolis Community Planning & Economic Development",
        "portal_url": "https://www.minneapolismn.gov/government/departments/cped/",
    },
    "milwaukee, wi": {
        "city": "Milwaukee",
        "state": "WI",
        "name": "City of Milwaukee Department of Neighborhood Services",
        "portal_url": "https://city.milwaukee.gov/DNS",
    },
    "kansas city, mo": {
        "city": "Kansas City",
        "state": "MO",
        "name": "City of Kansas City City Planning & Development",
        "portal_url": "https://www.kcmo.gov/city-hall/departments/city-planning-development",
    },
    "st louis, mo": {
        "city": "St Louis",
        "state": "MO",
        "name": "City of St. Louis Building Division",
        "portal_url": "https://www.stlouis-mo.gov/government/departments/public-safety/building/",
    },
    "st. louis, mo": {
        "city": "St Louis",
        "state": "MO",
        "name": "City of St. Louis Building Division",
        "portal_url": "https://www.stlouis-mo.gov/government/departments/public-safety/building/",
    },
    "nashville, tn": {
        "city": "Nashville",
        "state": "TN",
        "name": "Metro Nashville Codes & Building Safety",
        "portal_url": "https://www.nashville.gov/departments/codes-administration",
    },
    "memphis, tn": {
        "city": "Memphis",
        "state": "TN",
        "name": "City of Memphis Division of Planning & Development",
        "portal_url": "https://www.memphistn.gov/government/planning-development/",
    },
    "atlanta, ga": {
        "city": "Atlanta",
        "state": "GA",
        "name": "City of Atlanta Office of Buildings",
        "portal_url": "https://www.atlantaga.gov/government/departments/city-planning/office-of-buildings",
    },
    "charlotte, nc": {
        "city": "Charlotte",
        "state": "NC",
        "name": "City of Charlotte Land Development / Code Enforcement",
        "portal_url": "https://www.charlottenc.gov/Growth-and-Development/Planning-and-Development",
    },
    "raleigh, nc": {
        "city": "Raleigh",
        "state": "NC",
        "name": "City of Raleigh Development Services",
        "portal_url": "https://raleighnc.gov/development-services",
    },
    "new orleans, la": {
        "city": "New Orleans",
        "state": "LA",
        "name": "City of New Orleans Safety & Permits",
        "portal_url": "https://nola.gov/next/safety-and-permits/homepage/",
    },
    "oklahoma city, ok": {
        "city": "Oklahoma City",
        "state": "OK",
        "name": "City of Oklahoma City Development Services",
        "portal_url": "https://www.okc.gov/departments/development-services",
    },
    # Texas metros beyond full packs
    "houston, tx": {
        "city": "Houston",
        "state": "TX",
        "name": "City of Houston Permitting Center / Houston Public Works",
        "portal_url": "https://www.houstonpermittingcenter.org/",
        "fees_url": "https://www.houstonpermittingcenter.org/",
        "apply_url": "https://www.houstonpermittingcenter.org/",
        "last_verified": "",
    },
    "san antonio, tx": {
        "city": "San Antonio",
        "state": "TX",
        "name": "City of San Antonio Development Services",
        "portal_url": "https://www.sa.gov/Directory/Departments/DSD",
        "fees_url": "https://www.sa.gov/Directory/Departments/DSD",
        "apply_url": "https://www.sa.gov/Directory/Departments/DSD",
        "last_verified": "",
    },
    "fort worth, tx": {
        "city": "Fort Worth",
        "state": "TX",
        "name": "City of Fort Worth Development Services",
        "portal_url": "https://www.fortworthtexas.gov/departments/development-services",
        "fees_url": "https://www.fortworthtexas.gov/departments/development-services",
        "apply_url": "https://www.fortworthtexas.gov/departments/development-services",
        "last_verified": "",
    },
    # East / Florida / Northeast
    "miami, fl": {
        "city": "Miami",
        "state": "FL",
        "name": "City of Miami Building Department",
        "portal_url": "https://www.miami.gov/My-Government/Departments/Building",
    },
    "orlando, fl": {
        "city": "Orlando",
        "state": "FL",
        "name": "City of Orlando Permitting Services",
        "portal_url": "https://www.orlando.gov/Building-Development/Permitting",
    },
    "tampa, fl": {
        "city": "Tampa",
        "state": "FL",
        "name": "City of Tampa Construction Services Center",
        "portal_url": "https://www.tampa.gov/construction-services",
    },
    "jacksonville, fl": {
        "city": "Jacksonville",
        "state": "FL",
        "name": "City of Jacksonville Building Inspection",
        "portal_url": "https://www.jacksonville.gov/departments/planning-and-development/building-inspection-division",
    },
    "bradenton, fl": {
        "city": "Bradenton",
        "state": "FL",
        "name": "City of Bradenton Building & Permitting",
        "portal_url": "https://cityofbradenton.com/index.asp?SEC=%7B36A732FE-19FC-4DB5-A162-DE823D72E1ED%7D",
        "phone": "941-932-9414",
    },
    "sarasota, fl": {
        "city": "Sarasota",
        "state": "FL",
        "name": "City of Sarasota Building & Permitting",
        "portal_url": "https://www.sarasotafl.gov/Department-Pages/Development-Services/Building-Permitting",
    },
    "new york, ny": {
        "city": "New York",
        "state": "NY",
        "name": "NYC Department of Buildings",
        "portal_url": "https://www.nyc.gov/site/buildings/index.page",
    },
    "buffalo, ny": {
        "city": "Buffalo",
        "state": "NY",
        "name": "City of Buffalo Permit & Inspection Services",
        "portal_url": "https://www.buffalony.gov/195/Permit-Inspection-Services",
    },
    "boston, ma": {
        "city": "Boston",
        "state": "MA",
        "name": "City of Boston Inspectional Services",
        "portal_url": "https://www.boston.gov/departments/inspectional-services",
    },
    "philadelphia, pa": {
        "city": "Philadelphia",
        "state": "PA",
        "name": "City of Philadelphia Department of Licenses and Inspections",
        "portal_url": "https://www.phila.gov/departments/department-of-licenses-and-inspections/",
    },
    "pittsburgh, pa": {
        "city": "Pittsburgh",
        "state": "PA",
        "name": "City of Pittsburgh Department of Permits, Licenses, and Inspections",
        "portal_url": "https://pittsburghpa.gov/pli/index.html",
    },
    "baltimore, md": {
        "city": "Baltimore",
        "state": "MD",
        "name": "Baltimore City Department of Housing / Permits",
        "portal_url": "https://dhcd.baltimorecity.gov/",
    },
    "washington, dc": {
        "city": "Washington",
        "state": "DC",
        "name": "DC Department of Buildings",
        "portal_url": "https://dob.dc.gov/",
    },
    "richmond, va": {
        "city": "Richmond",
        "state": "VA",
        "name": "City of Richmond Department of Planning & Development Review",
        "portal_url": "https://www.rva.gov/planning-development-review",
    },
    "virginia beach, va": {
        "city": "Virginia Beach",
        "state": "VA",
        "name": "City of Virginia Beach Planning / Permits",
        "portal_url": "https://www.vbgov.com/government/departments/planning/",
    },
    "charlotte, nc": {  # already above — keep single
        "city": "Charlotte",
        "state": "NC",
        "name": "City of Charlotte Land Development / Code Enforcement",
        "portal_url": "https://www.charlottenc.gov/Growth-and-Development/Planning-and-Development",
    },
    "honolulu, hi": {
        "city": "Honolulu",
        "state": "HI",
        "name": "City & County of Honolulu Department of Planning & Permitting",
        "portal_url": "https://www.honolulu.gov/dpp/",
    },
    "anchorage, ak": {
        "city": "Anchorage",
        "state": "AK",
        "name": "Municipality of Anchorage Development Services",
        "portal_url": "https://www.muni.org/Departments/OCPD/Pages/default.aspx",
    },
    "cheyenne, wy": {
        "city": "Cheyenne",
        "state": "WY",
        "name": "City of Cheyenne (confirm Planning & Development on city site)",
        "portal_url": "https://www.cheyennecity.org/",
    },
    # FL Gulf / sales metros
    "clearwater, fl": {
        "city": "Clearwater",
        "state": "FL",
        "name": "City of Clearwater Building & Permitting",
        "portal_url": "https://www.myclearwater.com/government/city-departments/planning-development/building-construction",
    },
    "st petersburg, fl": {
        "city": "St Petersburg",
        "state": "FL",
        "name": "City of St. Petersburg Construction Services & Permitting",
        "portal_url": "https://www.stpete.org/business/development/construction_services___permitting.php",
    },
    "st. petersburg, fl": {
        "city": "St Petersburg",
        "state": "FL",
        "name": "City of St. Petersburg Construction Services & Permitting",
        "portal_url": "https://www.stpete.org/business/development/construction_services___permitting.php",
    },
    "lakeland, fl": {
        "city": "Lakeland",
        "state": "FL",
        "name": "City of Lakeland Building Inspection",
        "portal_url": "https://www.lakelandgov.net/departments/community-economic-development/building-inspection/",
    },
    "fort myers, fl": {
        "city": "Fort Myers",
        "state": "FL",
        "name": "City of Fort Myers Community Development / Building",
        "portal_url": "https://www.fortmyers.gov/1633/Building",
    },
    "naples, fl": {
        "city": "Naples",
        "state": "FL",
        "name": "City of Naples Building Department",
        "portal_url": "https://www.naplesgov.com/building",
    },
    "fort lauderdale, fl": {
        "city": "Fort Lauderdale",
        "state": "FL",
        "name": "City of Fort Lauderdale Building Services",
        "portal_url": "https://www.fortlauderdale.gov/government/departments-a-h/development-services/building-services",
    },
    "west palm beach, fl": {
        "city": "West Palm Beach",
        "state": "FL",
        "name": "City of West Palm Beach Development Services",
        "portal_url": "https://www.wpb.org/government/development-services",
    },
    "tallahassee, fl": {
        "city": "Tallahassee",
        "state": "FL",
        "name": "City of Tallahassee Growth Management / Building",
        "portal_url": "https://www.talgov.com/place/pln-building.aspx",
    },
    # TX sales metros beyond full packs
    "arlington, tx": {
        "city": "Arlington",
        "state": "TX",
        "name": "City of Arlington Planning & Development Services",
        "portal_url": "https://www.arlingtontx.gov/city_hall/departments/planning_and_development_services",
        "fees_url": "https://www.arlingtontx.gov/city_hall/departments/planning_and_development_services",
        "apply_url": "https://www.arlingtontx.gov/city_hall/departments/planning_and_development_services",
        "last_verified": "",
    },
    "irving, tx": {
        "city": "Irving",
        "state": "TX",
        "name": "City of Irving Building Inspections",
        "portal_url": "https://www.cityofirving.org/353/Building-Inspections",
        "fees_url": "https://www.cityofirving.org/353/Building-Inspections",
        "apply_url": "https://www.cityofirving.org/353/Building-Inspections",
        "last_verified": "",
    },
    "garland, tx": {
        "city": "Garland",
        "state": "TX",
        "name": "City of Garland Building Inspection",
        "portal_url": "https://www.garlandtx.gov/353/Building-Inspection",
        "fees_url": "https://www.garlandtx.gov/353/Building-Inspection",
        "apply_url": "https://www.garlandtx.gov/353/Building-Inspection",
        "last_verified": "",
    },
    "mckinney, tx": {
        "city": "McKinney",
        "state": "TX",
        "name": "City of McKinney Building Inspections",
        "portal_url": "https://www.mckinneytexas.org/149/Building-Inspections",
        "fees_url": "https://www.mckinneytexas.org/149/Building-Inspections",
        "apply_url": "https://www.mckinneytexas.org/149/Building-Inspections",
        "last_verified": "",
    },
    "frisco, tx": {
        "city": "Frisco",
        "state": "TX",
        "name": "City of Frisco Building Inspections",
        "portal_url": "https://www.friscotexas.gov/147/Building-Inspections",
        "fees_url": "https://www.friscotexas.gov/147/Building-Inspections",
        "apply_url": "https://www.friscotexas.gov/147/Building-Inspections",
        "last_verified": "",
    },
    "round rock, tx": {
        "city": "Round Rock",
        "state": "TX",
        "name": "City of Round Rock Building Inspections",
        "portal_url": "https://www.roundrocktexas.gov/departments/building-inspections/",
        "fees_url": "https://www.roundrocktexas.gov/departments/building-inspections/",
        "apply_url": "https://www.roundrocktexas.gov/departments/building-inspections/",
        "last_verified": "",
    },
    "denton, tx": {
        "city": "Denton",
        "state": "TX",
        "name": "City of Denton Building Inspections",
        "portal_url": "https://www.cityofdenton.com/200/Building-Inspections",
        "fees_url": "https://www.cityofdenton.com/200/Building-Inspections",
        "apply_url": "https://www.cityofdenton.com/200/Building-Inspections",
        "last_verified": "",
    },
    "el paso, tx": {
        "city": "El Paso",
        "state": "TX",
        "name": "City of El Paso Planning & Inspections",
        "portal_url": "https://www.elpasotexas.gov/planning-and-inspections/",
        "fees_url": "https://www.elpasotexas.gov/planning-and-inspections/",
        "apply_url": "https://www.elpasotexas.gov/planning-and-inspections/",
        "last_verified": "",
    },
    "corpus christi, tx": {
        "city": "Corpus Christi",
        "state": "TX",
        "name": "City of Corpus Christi Development Services",
        "portal_url": "https://www.cctexas.com/departments/development-services",
        "fees_url": "https://www.cctexas.com/departments/development-services",
        "apply_url": "https://www.cctexas.com/departments/development-services",
        "last_verified": "",
    },
    "lubbock, tx": {
        "city": "Lubbock",
        "state": "TX",
        "name": "City of Lubbock Building Inspection",
        "portal_url": "https://ci.lubbock.tx.us/departments/planning/building-inspection",
        "fees_url": "https://ci.lubbock.tx.us/departments/planning/building-inspection",
        "apply_url": "https://ci.lubbock.tx.us/departments/planning/building-inspection",
        "last_verified": "",
    },
    "midlothian, tx": {
        "city": "Midlothian",
        "state": "TX",
        "name": "City of Midlothian Building Inspections / Development Services",
        "portal_url": "https://www.midlothian.tx.us/149/Building-Inspections",
        "fees_url": "https://www.midlothian.tx.us/149/Building-Inspections",
        "apply_url": "https://www.midlothian.tx.us/149/Building-Inspections",
        "last_verified": "",
        "phone": "972-775-3481",
    },
    # DFW / Austin suburbs — portal only (not full citeable packs)
    "richardson, tx": {
        "city": "Richardson",
        "state": "TX",
        "name": "City of Richardson Building Inspection",
        "portal_url": "https://www.cor.net/departments/development-services/building-inspection",
        "fees_url": "https://www.cor.net/departments/development-services/building-inspection",
        "apply_url": "https://www.cor.net/departments/development-services/building-inspection",
        "last_verified": "",
    },
    "allen, tx": {
        "city": "Allen",
        "state": "TX",
        "name": "City of Allen Building Inspections",
        "portal_url": "https://www.cityofallen.org/149/Building-Inspections",
        "fees_url": "https://www.cityofallen.org/149/Building-Inspections",
        "apply_url": "https://www.cityofallen.org/149/Building-Inspections",
        "last_verified": "",
    },
    "carrollton, tx": {
        "city": "Carrollton",
        "state": "TX",
        "name": "City of Carrollton Building Inspection",
        "portal_url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection",
        "fees_url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection",
        "apply_url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection",
        "last_verified": "",
    },
    "lewisville, tx": {
        "city": "Lewisville",
        "state": "TX",
        "name": "City of Lewisville Building Inspections",
        "portal_url": "https://www.cityoflewisville.com/government/departments/building-inspections",
        "fees_url": "https://www.cityoflewisville.com/government/departments/building-inspections",
        "apply_url": "https://www.cityoflewisville.com/government/departments/building-inspections",
        "last_verified": "",
    },
    "mesquite, tx": {
        "city": "Mesquite",
        "state": "TX",
        "name": "City of Mesquite Building Inspection",
        "portal_url": "https://www.cityofmesquite.com/149/Building-Inspection",
        "fees_url": "https://www.cityofmesquite.com/149/Building-Inspection",
        "apply_url": "https://www.cityofmesquite.com/149/Building-Inspection",
        "last_verified": "",
    },
    "cedar park, tx": {
        "city": "Cedar Park",
        "state": "TX",
        "name": "City of Cedar Park Building & Development",
        "portal_url": "https://www.cedarparktexas.gov/149/Building-Development",
        "fees_url": "https://www.cedarparktexas.gov/149/Building-Development",
        "apply_url": "https://www.cedarparktexas.gov/149/Building-Development",
        "last_verified": "",
    },
    "pflugerville, tx": {
        "city": "Pflugerville",
        "state": "TX",
        "name": "City of Pflugerville Development Services Center",
        "portal_url": "https://www.pflugervilletx.gov/149/Development-Services-Center",
        "fees_url": "https://www.pflugervilletx.gov/149/Development-Services-Center",
        "apply_url": "https://www.pflugervilletx.gov/149/Development-Services-Center",
        "last_verified": "",
    },
    "leander, tx": {
        "city": "Leander",
        "state": "TX",
        "name": "City of Leander Building Inspections",
        "portal_url": "https://www.leandertx.gov/buildinginspections",
        "fees_url": "https://www.leandertx.gov/buildinginspections",
        "apply_url": "https://www.leandertx.gov/buildinginspections",
        "last_verified": "",
    },
    "georgetown, tx": {
        "city": "Georgetown",
        "state": "TX",
        "name": "City of Georgetown Building Inspections",
        "portal_url": "https://georgetown.org/building-inspections/",
        "fees_url": "https://georgetown.org/building-inspections/",
        "apply_url": "https://georgetown.org/building-inspections/",
        "last_verified": "",
    },
    # Additional national sales metros
    "boise, id": {
        "city": "Boise",
        "state": "ID",
        "name": "City of Boise Planning & Development Services",
        "portal_url": "https://www.cityofboise.org/departments/planning-and-development-services/",
    },
    "omaha, ne": {
        "city": "Omaha",
        "state": "NE",
        "name": "City of Omaha Planning Department / Permits",
        "portal_url": "https://planning.cityofomaha.org/",
    },
    "louisville, ky": {
        "city": "Louisville",
        "state": "KY",
        "name": "Louisville Metro Codes & Regulations",
        "portal_url": "https://louisvilleky.gov/government/codes-regulations",
    },
    "birmingham, al": {
        "city": "Birmingham",
        "state": "AL",
        "name": "City of Birmingham Department of Planning, Engineering & Permits",
        "portal_url": "https://www.birminghamal.gov/about/city-directory/planning-engineering-and-permits",
    },
}


def resolve_metro_portal_pack(
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> Optional[Dict[str, Any]]:
    """Return a portal-only local pack, or None."""
    key = _norm(city, state)
    seed = METRO_PORTAL_SEEDS.get(key)
    if not seed and city:
        # Try city-only fuzzy for "New York City" etc.
        c = (city or "").strip().lower()
        for k, v in METRO_PORTAL_SEEDS.items():
            if k.startswith(c + ",") and (
                not state or k.endswith(", " + (state or "").strip().lower()[:2])
            ):
                seed = v
                key = k
                break
    if not seed:
        return None

    portal = str(seed.get("portal_url") or "").strip()
    if not portal:
        return None

    name = str(seed.get("name") or f"{seed.get('city')} AHJ")
    fees_url = str(seed.get("fees_url") or portal).strip()
    return {
        "pack_key": f"portal:{key}",
        "citeable": False,  # portal known; fees/gotchas not curated
        "portal_only": True,
        "city": seed.get("city") or city,
        "state": seed.get("state") or state,
        "ahj": {
            "name": name,
            "portal_url": portal,
            "fees_url": fees_url,
            "apply_url": str(seed.get("apply_url") or "").strip(),
            "inspections_url": str(seed.get("inspections_url") or "").strip(),
            "phone": seed.get("phone") or "",
            "notes": (
                "Portal seed — confirm fees, amendments, and submittals on the official "
                "AHJ schedule before bid. Not a full citeable city pack (no curated fees/gotchas)."
            ),
            "last_verified": str(seed.get("last_verified") or "").strip(),
        },
        "fees": [],
        "gotchas": [],
        "documents": [
            "Single-line diagram",
            "Load calculations",
            "Cut sheets",
            "Contractor license / registration",
        ],
        "inspection_sequence": [],
        "last_verified": str(seed.get("last_verified") or "").strip(),
        "timeline_hint": f"Confirm plan review and inspection windows with {name}",
    }
