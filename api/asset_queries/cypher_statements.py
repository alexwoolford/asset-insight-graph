from typing import Dict


def get_assets_in_state() -> str:
    return """
MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State {name: $state})
RETURN a.name AS asset_name, c.name AS city,
       a.building_type AS building_type
"""


def get_assets_in_region() -> str:
    return """
MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State)-[:PART_OF]->(r:Region)
WHERE toLower(r.name) = toLower($region)
RETURN a.name AS asset_name, c.name + ', ' + s.name AS location,
       a.building_type AS building_type
"""


def get_assets_within_distance() -> str:
    return """
MATCH (ref:Asset)-[:LOCATED_IN]->(refCity:City)
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
ORDER BY distance_meters
"""


def get_portfolio_distribution() -> str:
    return """
MATCH (a:Asset)-[:BELONGS_TO]->(p:Platform),
      (a)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State)-[:PART_OF]->(r:Region)
RETURN p.name AS platform, r.name AS region,
       count(a) AS asset_count
ORDER BY platform, asset_count DESC
"""


def get_assets_by_type() -> str:
    return """
MATCH (a:Asset)-[:HAS_TYPE]->(bt:BuildingType)
WHERE toLower(bt.name) CONTAINS toLower($building_type)
RETURN a.name AS asset_name, bt.name AS building_type
"""


def get_total_assets() -> str:
    return """
MATCH (a:Asset)
RETURN count(a) AS total_assets
"""


def get_cypher_statements_dictionary() -> Dict[str, str]:
    return {
        "get_assets_in_state": get_assets_in_state(),
        "get_assets_in_region": get_assets_in_region(),
        "get_assets_within_distance": get_assets_within_distance(),
        "get_portfolio_distribution": get_portfolio_distribution(),
        "get_assets_by_type": get_assets_by_type(),
        "get_total_assets": get_total_assets(),
    }
