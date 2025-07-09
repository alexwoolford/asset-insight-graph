#!/usr/bin/env python3
"""
CIM loader with Neo4j native geospatial Point data types
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

SCHEMA_PATH = Path(__file__).with_name("schema.cypher")
DATA_PATH = Path(__file__).with_name("cim_assets.jsonl")

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


async def run_queries(driver, queries: list[str]) -> None:
    async with driver.session(database=NEO4J_DATABASE) as session:
        for q in queries:
            if q.strip():
                await session.run(q)


def parse_schema() -> list[str]:
    text = SCHEMA_PATH.read_text()
    return [stmt.strip() for stmt in text.split(";") if stmt.strip()]


def read_assets() -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    if DATA_PATH.exists():
        with DATA_PATH.open() as f:
            for line in f:
                assets.append(json.loads(line))
    return assets


async def geocode_location(city: str, state: str) -> dict[str, Any]:
    """
    Geocode a city, state location using OpenStreetMap Nominatim API.
    Returns dict with geospatial data for Neo4j Point types.
    """
    if not city or not state:
        return {}
    
    try:
        # Use free OpenStreetMap Nominatim API
        async with httpx.AsyncClient() as client:
            query = f"{city}, {state}, United States"
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
                "extratags": 1
            }
            headers = {
                "User-Agent": "AssetInsightGraph/1.0 (educational purposes)"
            }
            
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()
            
            if results:
                result = results[0]
                lat = float(result.get("lat", 0))
                lon = float(result.get("lon", 0))
                
                geo_data = {
                    "latitude": lat,  # Keep for backward compatibility
                    "longitude": lon,  # Keep for backward compatibility
                    "point_wgs84": {"latitude": lat, "longitude": lon, "crs": "WGS-84"},  # Neo4j Point
                    "display_name": result.get("display_name", ""),
                    "country": result.get("address", {}).get("country", "United States"),
                    "county": result.get("address", {}).get("county", ""),
                    "postcode": result.get("address", {}).get("postcode", ""),
                    "region": get_us_region(state)
                }
                return geo_data
                
    except Exception as e:
        print(f"Geocoding failed for {city}, {state}: {e}")
    
    return {}


def get_us_region(state: str) -> str:
    """Map US states to regions for better geographic categorization."""
    regions = {
        "Northeast": ["Connecticut", "Maine", "Massachusetts", "New Hampshire", "Rhode Island", 
                     "Vermont", "New Jersey", "New York", "Pennsylvania"],
        "Southeast": ["Delaware", "Florida", "Georgia", "Maryland", "North Carolina", 
                     "South Carolina", "Virginia", "West Virginia", "Kentucky", "Tennessee",
                     "Alabama", "Mississippi", "Arkansas", "Louisiana"],
        "Midwest": ["Illinois", "Indiana", "Michigan", "Ohio", "Wisconsin", "Iowa", "Kansas", 
                   "Minnesota", "Missouri", "Nebraska", "North Dakota", "South Dakota"],
        "Southwest": ["Arizona", "New Mexico", "Texas", "Oklahoma"],
        "West": ["Alaska", "California", "Colorado", "Hawaii", "Idaho", "Montana", "Nevada", 
                "Oregon", "Utah", "Washington", "Wyoming"]
    }
    
    for region, states in regions.items():
        if state in states:
            return region
    return "Other"


def extract_asset_characteristics(asset: dict) -> dict[str, Any]:
    """Extract characteristics from asset data."""
    characteristics = {}
    name = asset.get("name", "").lower()
    platform = asset.get("platform", "")
    
    # Asset type inference from name
    if any(word in name for word in ["tower", "building", "center", "plaza"]):
        characteristics["building_type"] = "Commercial"
    elif any(word in name for word in ["apartments", "residence", "homes"]):
        characteristics["building_type"] = "Residential"
    elif any(word in name for word in ["mall", "retail", "shopping"]):
        characteristics["building_type"] = "Retail"
    elif any(word in name for word in ["solar", "wind", "energy", "power"]):
        characteristics["building_type"] = "Energy Infrastructure"
    elif any(word in name for word in ["water", "utility"]):
        characteristics["building_type"] = "Water Infrastructure"
    else:
        characteristics["building_type"] = "Mixed Use"
    
    # Platform-based investment type
    if platform == "Real Estate":
        characteristics["investment_type"] = "Direct Real Estate"
    elif platform == "Infrastructure":
        characteristics["investment_type"] = "Infrastructure Investment"
    elif platform == "Credit":
        characteristics["investment_type"] = "Real Estate Credit"
    
    return characteristics





async def load_cim_assets() -> None:
    """Load CIM assets with Neo4j native geospatial Point data types."""
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        raise EnvironmentError("Missing Neo4j connection settings")

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    await run_queries(driver, parse_schema())

    assets = read_assets()
    print(f"Loading {len(assets)} CIM assets with native geospatial Point types...")
    
    async with driver.session(database=NEO4J_DATABASE) as session:
        for i, asset in enumerate(assets, 1):
            print(f"Processing asset {i}/{len(assets)}: {asset.get('name')}")
            
            # Geocode the location
            geo_data = await geocode_location(asset.get("city"), asset.get("state"))
            
            # Extract additional characteristics
            characteristics = extract_asset_characteristics(asset)
            
            # Asset creation with geospatial Point data
            cypher = """
            MERGE (a:Asset {id: $id}) 
            SET a.name = $name,
                a.img_url = $img_url,
                a.img_filename = $img_filename,
                a.building_type = $building_type,
                a.investment_type = $investment_type,
                a.location = point($point_wgs84),
                a.display_name = $display_name,
                a.postcode = $postcode
            
            MERGE (c:City {name: $city, state: $state})
            SET c.location = point($point_wgs84),
                c.county = $county,
                c.postcode = $postcode
            MERGE (a)-[:LOCATED_IN]->(c)
            
            MERGE (s:State {name: $state, country: $country})
            MERGE (c)-[:PART_OF]->(s)
            
            MERGE (r:Region {name: $region})
            MERGE (s)-[:PART_OF]->(r)
            
            MERGE (p:Platform {name: $platform})
            MERGE (a)-[:BELONGS_TO]->(p)
            
            MERGE (bt:BuildingType {name: $building_type})
            MERGE (a)-[:HAS_TYPE]->(bt)
            
            MERGE (it:InvestmentType {name: $investment_type})
            MERGE (a)-[:HAS_INVESTMENT_TYPE]->(it)
            """
            
            await session.run(
                cypher,
                {
                    "id": asset.get("item_id"),
                    "name": asset.get("name"),
                    "city": asset.get("city"),
                    "state": asset.get("state"),
                    "platform": asset.get("platform"),
                    "img_url": asset.get("img_url"),
                    "img_filename": asset.get("img_filename"),
                    "building_type": characteristics.get("building_type"),
                    "investment_type": characteristics.get("investment_type"),
                    "point_wgs84": geo_data.get("point_wgs84"),
                    "display_name": geo_data.get("display_name"),
                    "county": geo_data.get("county"),
                    "postcode": geo_data.get("postcode"),
                    "country": geo_data.get("country", "United States"),
                    "region": geo_data.get("region"),
                },
            )
            
            # Rate limiting to be respectful to the geocoding API
            if i % 5 == 0:
                await asyncio.sleep(1)
    
    await driver.close()
    print(f"✅ Successfully loaded {len(assets)} CIM assets!")


if __name__ == "__main__":    asyncio.run(load_cim_assets()) 
