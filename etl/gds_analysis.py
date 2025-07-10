#!/usr/bin/env python3
"""
GDS Community Detection Demo

This script demonstrates GDS capabilities for asset clustering and theme analysis.
"""

import asyncio
import os
from typing import Dict, List, Any

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


class GDSAnalyzer:
    """Demonstrates GDS community detection and analytics."""
    
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
    
    async def close(self):
        """Close the database connection."""
        await self.driver.close()
    
    async def verify_graph_structure(self):
        """Verify the current graph structure."""
        print("🔍 Verifying graph structure...")
        
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            # Check node counts
            queries = [
                ("Assets", "MATCH (a:Asset) RETURN count(a) as count"),
                ("Cities", "MATCH (c:City) RETURN count(c) as count"),
                ("States", "MATCH (s:State) RETURN count(s) as count"),
                ("Platforms", "MATCH (p:Platform) RETURN count(p) as count")
            ]
            
            for label, query in queries:
                result = await session.run(query)
                record = await result.single()
                count = record['count'] if record else 0
                print(f"   {label}: {count}")
            
            # Sample assets
            print("\n📋 Sample assets:")
            result = await session.run("""
                MATCH (a:Asset)-[:BELONGS_TO]->(p:Platform)
                RETURN a.name, p.name AS platform
                ORDER BY p.name, a.name 
                LIMIT 6
            """)
            async for record in result:
                print(f"   {record['a.name']} ({record['platform']})")
    
    async def setup_simplified_gds_projection(self):
        """Set up a simplified GDS projection for community detection."""
        print("\n🧠 Setting up GDS projection for community detection...")
        
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            # Drop existing projection if it exists
            try:
                result = await session.run("CALL gds.graph.exists('asset-platform-communities') YIELD exists")
                record = await result.single()
                if record and record['exists']:
                    await session.run("CALL gds.graph.drop('asset-platform-communities')")
                    print("🗑️ Dropped existing projection")
            except:
                pass
            
            # Create simple asset-platform projection
            print("📊 Creating asset-platform community projection...")
            await session.run("""
                CALL gds.graph.project(
                    'asset-platform-communities',
                    ['Asset', 'Platform'],
                    'BELONGS_TO'
                )
            """)
            
            print("✅ GDS projection created!")
    
    async def run_community_detection(self):
        """Run Louvain community detection to find asset clusters."""
        print("\n👥 Running Louvain community detection...")
        
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            # Run Louvain algorithm on asset-platform relationships
            result = await session.run("""
                CALL gds.louvain.stream('asset-platform-communities')
                YIELD nodeId, communityId
                WITH gds.util.asNode(nodeId) AS node, communityId
                WHERE node:Asset
                RETURN node.name AS asset_name, 
                       communityId,
                       node.platform AS platform,
                       node.building_type AS building_type
                ORDER BY communityId, asset_name
            """)
            
            communities: Dict[int, List[Dict[str, Any]]] = {}
            async for record in result:
                community_id = record['communityId']
                asset_info = {
                    'name': record['asset_name'],
                    'platform': record['platform'],
                    'building_type': record['building_type']
                }
                
                if community_id not in communities:
                    communities[community_id] = []
                communities[community_id].append(asset_info)
            
            print(f"🔍 Discovered {len(communities)} asset communities based on platform relationships:")
            print()
            
            for community_id, assets in communities.items():
                print(f"📦 Community {community_id} ({len(assets)} assets):")
                for asset in assets:
                    print(f"   • {asset['name']} - {asset['platform']} ({asset['building_type']})")
                print()
            
            return communities
    
    async def analyze_geographic_clustering(self):
        """Analyze how assets cluster geographically."""
        print("\n🗺️ Geographic clustering analysis...")
        
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            # Analyze geographic distribution by platform
            result = await session.run("""
                MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State),
                      (a)-[:BELONGS_TO]->(p:Platform)
                WITH p.name AS platform, s.name AS state, count(a) AS asset_count
                RETURN platform, state, asset_count
                ORDER BY platform, asset_count DESC
            """)
            
            platform_states: Dict[str, Dict[str, int]] = {}
            async for record in result:
                platform = record['platform']
                state = record['state']
                count = record['asset_count']
                
                if platform not in platform_states:
                    platform_states[platform] = {}
                platform_states[platform][state] = count
            
            for platform, states in platform_states.items():
                print(f"📊 {platform} Platform Geographic Distribution:")
                for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True):
                    print(f"   • {state}: {count} assets")
                print()


async def main():
    """Main GDS analysis function."""
    print("🏢 GDS Community Detection and Theme Analysis")
    print("=" * 60)
    
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        print("❌ Error: Missing Neo4j connection settings")
        return
    
    analyzer = GDSAnalyzer()
    
    try:
        # 1. Verify graph structure
        await analyzer.verify_graph_structure()
        
        # 2. Set up GDS projection
        await analyzer.setup_simplified_gds_projection()
        
        # 3. Run community detection
        await analyzer.run_community_detection()
        
        # 4. Geographic clustering analysis
        await analyzer.analyze_geographic_clustering()
        
        print("\n🎉 GDS analysis complete!")
        print("💡 Key insights: Assets cluster naturally by platform relationships")
        print("💡 Geographic distribution varies by platform")
        print("💡 Community detection reveals platform-based groupings")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    
    finally:
        await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main()) 