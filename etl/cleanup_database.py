#!/usr/bin/env python3
"""
Database cleanup script to prepare for fresh knowledge graph loading
"""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


async def cleanup_database() -> None:
    """Clean up the Neo4j database for a fresh start."""
    print("🧹 Cleaning up Neo4j database for fresh start...")
    print("=" * 60)
    
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        print("❌ Error: Missing Neo4j connection settings")
        return

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    try:
        async with driver.session(database=NEO4J_DATABASE) as session:
            
            # 1. Check current state
            print("\n📊 Current database state:")
            result = await session.run("CALL db.labels() YIELD label RETURN label ORDER BY label")
            labels = [record["label"] async for record in result]
            print(f"   Node labels: {', '.join(labels) if labels else 'None'}")
            
            result = await session.run("MATCH (n) RETURN count(n) AS node_count")
            node_count = (await result.single())["node_count"]
            print(f"   Total nodes: {node_count}")
            
            result = await session.run("MATCH ()-[r]->() RETURN count(r) AS rel_count")
            rel_count = (await result.single())["rel_count"]
            print(f"   Total relationships: {rel_count}")
            
            if node_count == 0:
                print("✅ Database is already clean!")
                return
            
            # 2. Delete all nodes and relationships
            print("\n🗑️  Deleting all nodes and relationships...")
            result = await session.run("MATCH (n) DETACH DELETE n RETURN count(n) AS deleted")
            deleted_count = (await result.single())["deleted"]
            print(f"   Deleted {deleted_count} nodes and their relationships")
            
            # 3. Drop custom constraints (keep built-in ones)
            print("\n🔧 Dropping custom constraints...")
            constraints_to_drop = [
                "asset_id",
                "city_composite", 
                "state_name",
                "region_name",
                "platform_name",
                "building_type_name",
                "investment_type_name",
                "tenant_id",  # from old schema
                "partner_id"  # from old schema
            ]
            
            for constraint_name in constraints_to_drop:
                try:
                    await session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
                    print(f"   Dropped constraint: {constraint_name}")
                except Exception as e:
                    print(f"   Could not drop constraint {constraint_name}: {e}")
            
            # 4. Drop custom indexes (keep built-in ones)
            print("\n📇 Dropping custom indexes...")
            indexes_to_drop = [
                "asset_name",
                "asset_building_type",
                "asset_investment_type", 
                "asset_location",
                "asset_city",  # from old schema
                "city_name",
                "city_location",
                "state_name",
                "region_name",
                "platform_name",
                "building_type_name",
                "investment_type_name"
            ]
            
            for index_name in indexes_to_drop:
                try:
                    await session.run(f"DROP INDEX {index_name} IF EXISTS")
                    print(f"   Dropped index: {index_name}")
                except Exception as e:
                    print(f"   Could not drop index {index_name}: {e}")
            
            # 5. Verify cleanup
            print("\n✅ Cleanup verification:")
            result = await session.run("MATCH (n) RETURN count(n) AS node_count")
            final_node_count = (await result.single())["node_count"]
            print(f"   Remaining nodes: {final_node_count}")
            
            result = await session.run("MATCH ()-[r]->() RETURN count(r) AS rel_count")
            final_rel_count = (await result.single())["rel_count"]
            print(f"   Remaining relationships: {final_rel_count}")
            
            if final_node_count == 0 and final_rel_count == 0:
                print("🎉 Database successfully cleaned!")
            else:
                print("⚠️  Some nodes/relationships may remain")
                
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
    finally:
        await driver.close()
    
    print("\n" + "="*60)
    print("✅ Database cleanup complete!")
    print("📋 Next steps:")
    print("   1. Load enhanced data: make load")
    print("   2. Verify loading: make verify")


if __name__ == "__main__":
    asyncio.run(cleanup_database()) 