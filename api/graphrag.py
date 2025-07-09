from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from .config import Settings, get_driver

# Query patterns using Neo4j native geospatial Point types
# NOTE: Order matters! More specific patterns should come first
GEOSPATIAL_RULES: List[tuple[re.Pattern[str], str]] = [
    

    
    # California specific (most specific geographic query)
    (
        re.compile(r"california assets|assets in california", re.I),
        """MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State {name: "California"})
           RETURN a.name AS asset_name, c.name AS city,
                  a.building_type AS building_type,
                  a.location.latitude AS latitude,
                  a.location.longitude AS longitude""",
    ),
    
    # Regional queries (more specific than city)
    (
        re.compile(r"assets in the (?P<region>west|east|northeast|southeast|midwest|southwest)", re.I),
        """MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State)-[:PART_OF]->(r:Region)
           WHERE toLower(r.name) = toLower($region)
           RETURN a.name AS asset_name, c.name + ', ' + s.name AS location,
                  a.building_type AS building_type""",
    ),
    
    # State queries (more specific than city)
    (
        re.compile(r"assets in (?P<state>.+) state", re.I),
        """MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State {name: $state})
           RETURN a.name AS asset_name, c.name AS city, 
                  a.building_type AS building_type""",
    ),
    
    # Platform queries
    (
        re.compile(r"(?P<platform>real estate|infrastructure|credit) assets", re.I),
        """MATCH (a:Asset)-[:BELONGS_TO]->(p:Platform)
           WHERE toLower(p.name) CONTAINS toLower($platform)
           RETURN a.name AS asset_name, p.name AS platform, 
                  a.building_type AS building_type""",
    ),
    
    # Investment type queries
    (
        re.compile(r"(?P<investment_type>direct real estate|infrastructure investment|real estate credit)", re.I),
        """MATCH (a:Asset)-[:HAS_INVESTMENT_TYPE]->(it:InvestmentType)
           WHERE toLower(it.name) = toLower($investment_type)
           RETURN a.name AS asset_name, it.name AS investment_type""",
    ),
    
    # Building type analysis
    (
        re.compile(r"(?P<building_type>commercial|residential|infrastructure|mixed use) buildings?", re.I),
        """MATCH (a:Asset)-[:HAS_TYPE]->(bt:BuildingType)
           WHERE toLower(bt.name) CONTAINS toLower($building_type)
           RETURN a.name AS asset_name, bt.name AS building_type""",
    ),
    
    # Portfolio analysis
    (
        re.compile(r"portfolio distribution|asset distribution", re.I),
        """MATCH (a:Asset)-[:BELONGS_TO]->(p:Platform),
                 (a)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State)-[:PART_OF]->(r:Region)
           RETURN p.name AS platform, r.name AS region, 
                  count(a) AS asset_count
           ORDER BY platform, asset_count DESC""",
    ),
    
    # Geospatial queries using native Point types
    (
        re.compile(r"assets within (?P<distance>\d+)\s*(?P<unit>km|miles?) of (?P<reference>.+)", re.I),
        """MATCH (ref:Asset)-[:LOCATED_IN]->(refCity:City)
           WHERE toLower(ref.name) CONTAINS toLower($reference) OR toLower(refCity.name) CONTAINS toLower($reference)
           WITH ref, toInteger($distance) AS distance, $unit AS unit
           MATCH (a:Asset)
           WHERE a <> ref AND a.location IS NOT NULL AND ref.location IS NOT NULL
           WITH a, ref, distance, unit,
                point.distance(a.location, ref.location) AS distance_meters
           WHERE (unit IN ['km', 'kilometer'] AND distance_meters <= distance * 1000) OR
                 (unit IN ['mile', 'miles'] AND distance_meters <= distance * 1609.34)
           RETURN a.name AS asset_name, ref.name AS reference_asset,
                  round(distance_meters/1000, 1) AS distance_km,
                  round(distance_meters/1609.34, 1) AS distance_miles
           ORDER BY distance_meters""",
    ),
    
    # Geographic clustering using native distance functions
    (
        re.compile(r"nearby assets|assets near|geographic clusters?", re.I),
        """MATCH (a1:Asset), (a2:Asset)
           WHERE a1 <> a2 AND a1.location IS NOT NULL AND a2.location IS NOT NULL
           WITH a1, a2, point.distance(a1.location, a2.location) AS distance_meters
           WHERE distance_meters < 50000
           RETURN a1.name AS asset1, a2.name AS asset2,
                  round(distance_meters/1000, 1) AS distance_km
           ORDER BY distance_meters LIMIT 10""",
    ),
    
    # Assets within a bounding box (geospatial envelope)
    (
        re.compile(r"assets in (?P<area>los angeles|la|bay area|san francisco|chicago|new york) area", re.I),
        """WITH CASE toLower($area)
             WHEN 'los angeles' THEN {minLat: 33.7, maxLat: 34.3, minLon: -118.7, maxLon: -118.0}
             WHEN 'la' THEN {minLat: 33.7, maxLat: 34.3, minLon: -118.7, maxLon: -118.0}
             WHEN 'bay area' THEN {minLat: 37.2, maxLat: 37.9, minLon: -122.6, maxLon: -121.5}
             WHEN 'san francisco' THEN {minLat: 37.2, maxLat: 37.9, minLon: -122.6, maxLon: -121.5}
             WHEN 'chicago' THEN {minLat: 41.6, maxLat: 42.0, minLon: -87.9, maxLon: -87.5}
             WHEN 'new york' THEN {minLat: 40.5, maxLat: 40.9, minLon: -74.3, maxLon: -73.7}
             ELSE {minLat: 0, maxLat: 0, minLon: 0, maxLon: 0}
           END AS area_bounds
           MATCH (a:Asset)
           WHERE a.location IS NOT NULL 
             AND area_bounds.minLat <= a.location.latitude <= area_bounds.maxLat
             AND area_bounds.minLon <= a.location.longitude <= area_bounds.maxLon
           RETURN a.name AS asset_name, 
                  a.location.latitude AS latitude,
                  a.location.longitude AS longitude,
                  a.building_type AS building_type""",
    ),
    
    # Count queries
    (
        re.compile(r"how many assets|asset count|total assets", re.I),
        "MATCH (a:Asset) RETURN count(a) AS total_assets",
    ),
    (
        re.compile(r"how many (?P<node_type>cities|states|regions|platforms)", re.I),
        """MATCH (c:City), (s:State), (r:Region), (p:Platform)
           RETURN count(DISTINCT c) AS cities, count(DISTINCT s) AS states, 
                  count(DISTINCT r) AS regions, count(DISTINCT p) AS platforms""",
    ),
    
    # City queries (most general, comes last)
    (
        re.compile(r"assets in (?P<city>.+)", re.I),
        """MATCH (a:Asset)-[:LOCATED_IN]->(c:City {name: $city})
           RETURN a.name AS asset_name, a.building_type AS building_type, 
                  a.investment_type AS investment_type""",
    ),
]


async def answer_geospatial(question: str) -> Dict[str, Any]:
    """Return answer dictionary using geospatial patterns with Neo4j Point types."""
    # Try pattern matching first
    for pattern, cypher in GEOSPATIAL_RULES:
        match = pattern.search(question)
        if match:
            params = match.groupdict()
            driver = get_driver()
            settings = Settings()
            async with driver.session(database=settings.neo4j_db) as session:
                result = await session.run(cypher, params)
                data = await result.data()
            
            # Generate a natural language summary
            summary = generate_geospatial_summary(question, data, cypher)
            
            return {
                "answer": summary,
                "cypher": cypher,
                "data": data,
                "question": question,
                "pattern_matched": True,
                "geospatial_enabled": True
            }

    # If no pattern matches and OpenAI is available, use LLM-based approach
    if os.getenv("OPENAI_API_KEY"):
        raise NotImplementedError("LLM-based GraphRAG not yet implemented - coming soon!")
    
    # Fallback: suggest what kinds of questions can be answered
    suggestions = [
        "Assets in California",
        "Real estate assets", 
        "Infrastructure assets",
        "Credit assets",
        "Assets in Texas state",
        "Assets in the west",
        "Portfolio distribution",
        "Commercial buildings",
        "Nearby assets",
        "Assets within 50km of Los Angeles",
        "Assets in LA area",
        "How many assets",
    ]
    
    return {
        "answer": f"I couldn't understand that question. Try asking about: {', '.join(suggestions[:6])}",
        "cypher": None,
        "data": [],
        "question": question,
        "pattern_matched": False,
        "geospatial_enabled": False,
        "suggestions": suggestions
    }


def generate_geospatial_summary(question: str, data: List[Dict], cypher: str) -> str:
    """Generate a natural language summary of geospatial query results."""
    if not data:
        return "No results found for your query."
    
    result_count = len(data)
    
    # Customize response based on query type
    if "asset_count" in str(data[0]) or "total_assets" in str(data[0]):
        return f"Found {data[0].get('total_assets', data[0].get('asset_count', result_count))} assets total."
    
    if "distance_km" in str(data[0]):
        if "reference_asset" in str(data[0]):
            # Distance from reference query
            ref = data[0].get('reference_asset', 'reference point')
            examples = ", ".join([f"{item['asset_name']} ({item['distance_km']}km away)" for item in data[:3]])
            return f"Found {result_count} assets near {ref}: {examples}"
        else:
            # Clustering query
            pairs = [(item['asset1'], item['asset2'], item['distance_km']) for item in data[:3]]
            examples = ", ".join([f"{a1} and {a2} ({d}km apart)" for a1, a2, d in pairs])
            return f"Found {result_count} asset pairs within proximity. Examples: {examples}"
    
    if "platform" in str(data[0]) and "region" in str(data[0]):
        summary = "Portfolio distribution: "
        platform_summary = {}
        for item in data:
            platform = item.get('platform', 'Unknown')
            if platform not in platform_summary:
                platform_summary[platform] = 0
            platform_summary[platform] += item.get('asset_count', 1)
        
        distribution = ", ".join([f"{p}: {c} assets" for p, c in platform_summary.items()])
        return f"{summary}{distribution}"
    
    # Default summary for asset lists
    asset_names = [item.get('asset_name', 'Unknown') for item in data[:5]]
    if result_count <= 5:
        return f"Found {result_count} assets: {', '.join(asset_names)}"
    else:
        return f"Found {result_count} assets including: {', '.join(asset_names)} and {result_count - 5} more" 