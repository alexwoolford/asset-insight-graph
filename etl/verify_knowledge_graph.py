#!/usr/bin/env python3
"""
Verification script to explore the CIM Asset Knowledge Graph
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


async def run_query(session, query: str, description: str) -> list[dict[str, Any]]:
    """Run a query and return results with description."""
    print(f"\n🔍 {description}")
    print("=" * 60)
    
    result = await session.run(query)
    records = await result.data()
    
    if not records:
        print("No results found.")
        return []
    
    # Print results in a formatted way
    for i, record in enumerate(records, 1):
        if len(records) <= 10:  # Show all if 10 or fewer
            print(f"{i:2d}. {record}")
        elif i <= 5:  # Show first 5 if more than 10
            print(f"{i:2d}. {record}")
        elif i == 6 and len(records) > 10:
            print(f"    ... and {len(records) - 5} more")
            break
    
    print(f"\nTotal: {len(records)} results")
    return records


async def verify_knowledge_graph() -> None:
    """Verify and explore the loaded knowledge graph."""
    print("🏗️  CIM Asset Knowledge Graph Verification")
    print("=" * 60)
    
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        print("❌ Error: Missing Neo4j connection settings")
        return

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    try:
        async with driver.session(database=NEO4J_DATABASE) as session:
            
            # 1. Database Overview - Node Counts
            queries = [
                ("Asset", "MATCH (n:Asset) RETURN count(n) as count"),
                ("City", "MATCH (n:City) RETURN count(n) as count"),
                ("State", "MATCH (n:State) RETURN count(n) as count"),
                ("Region", "MATCH (n:Region) RETURN count(n) as count"),
                ("Platform", "MATCH (n:Platform) RETURN count(n) as count"),
                ("BuildingType", "MATCH (n:BuildingType) RETURN count(n) as count"),
                ("InvestmentType", "MATCH (n:InvestmentType) RETURN count(n) as count"),
            ]
            
            print(f"\n🔍 📊 Node Types and Counts")
            print("=" * 60)
            for label, query in queries:
                result = await session.run(query)
                record = await result.single()
                count = record[0] if record else 0
                print(f"{label:15}: {count:3d} nodes")
            print(f"\nDatabase successfully populated!")
            
            # 2. All Assets with Key Information
            await run_query(
                session,
                """
                MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State)-[:PART_OF]->(r:Region),
                      (a)-[:BELONGS_TO]->(p:Platform),
                      (a)-[:HAS_TYPE]->(bt:BuildingType)
                RETURN a.name as asset_name, 
                       c.name + ', ' + s.name as location,
                       r.name as region,
                       p.name as platform,
                       bt.name as building_type,
                       round(a.latitude, 3) as lat,
                       round(a.longitude, 3) as lon
                ORDER BY p.name, a.name
                """,
                "🏢 All CIM Assets with Enriched Data"
            )
            
            # 3. Geographic Distribution
            await run_query(
                session,
                """
                MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State)-[:PART_OF]->(r:Region)
                RETURN r.name as region, 
                       collect(DISTINCT s.name) as states,
                       count(a) as asset_count
                ORDER BY asset_count DESC
                """,
                "🗺️  Geographic Distribution by Region"
            )
            
            # 4. Platform Analysis
            await run_query(
                session,
                """
                MATCH (a:Asset)-[:BELONGS_TO]->(p:Platform),
                      (a)-[:HAS_TYPE]->(bt:BuildingType)
                RETURN p.name as platform,
                       collect(DISTINCT bt.name) as building_types,
                       count(a) as asset_count
                ORDER BY asset_count DESC
                """,
                "💼 Platform and Building Type Analysis"
            )
            
            # 5. Investment Type Distribution
            await run_query(
                session,
                """
                MATCH (a:Asset)-[:HAS_INVESTMENT_TYPE]->(it:InvestmentType)
                RETURN it.name as investment_type,
                       count(a) as asset_count,
                       collect(a.name)[0..3] as sample_assets
                ORDER BY asset_count DESC
                """,
                "💰 Investment Type Distribution"
            )
            
            # 6. Geographic Clusters (nearby assets)
            await run_query(
                session,
                """
                MATCH (a1:Asset), (a2:Asset)
                WHERE a1 <> a2 
                  AND a1.latitude IS NOT NULL AND a1.longitude IS NOT NULL
                  AND a2.latitude IS NOT NULL AND a2.longitude IS NOT NULL
                WITH a1, a2, 
                     point({latitude: a1.latitude, longitude: a1.longitude}) as p1,
                     point({latitude: a2.latitude, longitude: a2.longitude}) as p2
                                 WITH a1, a2, point.distance(p1, p2) as distance_meters
                WHERE distance_meters < 100000  // Within 100km
                RETURN a1.name as asset1, 
                       a2.name as asset2,
                       round(distance_meters/1000, 1) as distance_km
                ORDER BY distance_meters
                LIMIT 10
                """,
                "📍 Geographic Clusters (Assets within 100km)"
            )
            
            # 7. State-level Portfolio Summary
            await run_query(
                session,
                """
                MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State),
                      (a)-[:BELONGS_TO]->(p:Platform)
                WITH s.name as state, p.name as platform, count(a) as count
                ORDER BY state, count DESC
                RETURN state, 
                       collect({platform: platform, count: count}) as portfolio_mix,
                       sum(count) as total_assets
                ORDER BY total_assets DESC
                """,
                "🏛️  State-level Portfolio Summary"
            )
            
            # 8. Sample Spatial Query - California Assets
            await run_query(
                session,
                """
                MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State {name: "California"})
                RETURN a.name as asset_name,
                       c.name as city,
                       a.building_type,
                       round(a.latitude, 4) as latitude,
                       round(a.longitude, 4) as longitude
                ORDER BY a.name
                """,
                "🌴 California Assets (Sample Geographic Filter)"
            )
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await driver.close()
    
    print("\n" + "="*60)
    print("✅ Knowledge Graph Verification Complete!")
    print("📈 The CIM Asset Knowledge Graph is ready for analysis!")


if __name__ == "__main__":
    asyncio.run(verify_knowledge_graph()) 