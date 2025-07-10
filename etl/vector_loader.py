"""
Vector Embedding Loader for CIM Assets

This module creates OpenAI embeddings from enhanced property descriptions
and loads them into Neo4j with vector search capabilities.
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional

import openai
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ClientError

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # Dimension for text-embedding-3-small


class VectorEmbeddingLoader:
    """Handles creation and loading of vector embeddings for CIM assets."""
    
    def __init__(self):
        """Initialize the vector embedding loader."""
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize OpenAI client
        openai.api_key = OPENAI_API_KEY
        self.client = openai.OpenAI()
        
        # Initialize Neo4j driver
        self.driver = AsyncGraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
    
    async def create_vector_index(self) -> None:
        """Create vector index in Neo4j for efficient similarity search."""
        
        # Drop existing index if it exists
        drop_index_query = """
        DROP INDEX asset_description_vector IF EXISTS
        """
        
        # Create vector index for property descriptions
        create_index_query = f"""
        CREATE VECTOR INDEX asset_description_vector IF NOT EXISTS
        FOR (a:Asset)
        ON a.description_embedding
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {EMBEDDING_DIMENSION},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """
        
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            try:
                await session.run(drop_index_query)
                print("Dropped existing vector index (if any)")
            except ClientError as e:
                print(f"Note: Could not drop index (may not exist): {e}")
            
            try:
                await session.run(create_index_query)
                print(f"Created vector index with {EMBEDDING_DIMENSION} dimensions")
            except ClientError as e:
                print(f"Error creating vector index: {e}")
                raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text using OpenAI."""
        
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text.replace("\n", " "),  # Clean text
                encoding_format="float"
            )
            return response.data[0].embedding
        
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise
    
    async def load_asset_with_embedding(self, asset: Dict[str, Any]) -> None:
        """Load a single asset with its vector embedding into Neo4j."""
        
        # Generate embedding for property description
        description = asset.get("property_description", "")
        if not description:
            print(f"Warning: No description for asset {asset.get('name', 'Unknown')}")
            return
        
        print(f"Generating embedding for: {asset.get('name', 'Unknown')}")
        embedding = await self.generate_embedding(description)
        
        # Prepare asset data with embedding
        asset_data = {
            "id": asset.get("item_id"),
            "name": asset.get("name"),
            "city": asset.get("city"),
            "state": asset.get("state"),
            "platform": asset.get("platform"),
            "building_type": asset.get("building_type"),
            "property_description": description,

            "description_embedding": embedding,
            "img_url": asset.get("img_url"),
            "img_filename": asset.get("img_filename")
        }
        
        # Create/update asset with embedding
        cypher_query = """
        MERGE (a:Asset {id: $id})
        SET a.name = $name,
            a.city = $city,
            a.state = $state,
            a.platform = $platform,
            a.building_type = $building_type,
            a.property_description = $property_description,

            a.description_embedding = $description_embedding,
            a.img_url = $img_url,
            a.img_filename = $img_filename,
            a.embedding_model = $embedding_model,
            a.embedding_dimension = $embedding_dimension
        
        // Also maintain existing geographic relationships
        WITH a
        MERGE (c:City {name: $city, state: $state})
        MERGE (a)-[:LOCATED_IN]->(c)
        
        MERGE (s:State {name: $state})
        MERGE (c)-[:PART_OF]->(s)
        
        MERGE (p:Platform {name: $platform})
        MERGE (a)-[:BELONGS_TO]->(p)
        
        MERGE (bt:BuildingType {name: $building_type})
        MERGE (a)-[:HAS_TYPE]->(bt)
        """
        
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            try:
                await session.run(cypher_query, {
                    **asset_data,
                    "embedding_model": EMBEDDING_MODEL,
                    "embedding_dimension": EMBEDDING_DIMENSION
                })
                print(f"✓ Loaded asset: {asset.get('name', 'Unknown')}")
                
            except Exception as e:
                print(f"Error loading asset {asset.get('name', 'Unknown')}: {e}")
                raise
    
    async def load_all_assets_with_embeddings(self, descriptions_file: str = "etl/cim_assets_descriptions.jsonl") -> None:
        """Load all enhanced assets with embeddings into Neo4j."""
        
        # Read enhanced assets
        assets = []
        try:
            with open(descriptions_file, "r") as f:
                assets = [json.loads(line) for line in f]
        except FileNotFoundError:
            print(f"Error: {descriptions_file} not found. Run property_descriptions.py first.")
            return
        
        print(f"Loading {len(assets)} assets with vector embeddings...")
        
        # Create vector index first
        await self.create_vector_index()
        
        # Load each asset with embedding
        for i, asset in enumerate(assets, 1):
            print(f"Processing asset {i}/{len(assets)}")
            await self.load_asset_with_embedding(asset)
            
            # Rate limiting to be respectful to OpenAI API
            if i % 5 == 0:
                await asyncio.sleep(1)
        
        print(f"✅ Successfully loaded {len(assets)} assets with vector embeddings!")
    
    async def test_vector_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Test vector similarity search with a query."""
        
        print(f"Testing vector search for: '{query}'")
        
        # Generate embedding for the query
        query_embedding = await self.generate_embedding(query)
        
        # Perform vector similarity search
        search_query = """
        CALL db.index.vector.queryNodes('asset_description_vector', $limit, $query_embedding)
        YIELD node, score
        RETURN node.name AS asset_name,
               node.city AS city,
               node.state AS state,
               node.platform AS platform,
               node.building_type AS building_type,

               score AS similarity_score
        ORDER BY score DESC
        """
        
        async with self.driver.session(database=NEO4J_DATABASE) as session:
            result = await session.run(search_query, {
                "query_embedding": query_embedding,
                "limit": limit
            })
            
            records = await result.data()
            return records
    
    async def close(self):
        """Close the Neo4j driver connection."""
        await self.driver.close()


async def main():
    """Main function to load assets with vector embeddings."""
    
    loader = VectorEmbeddingLoader()
    
    try:
        # Load all assets with embeddings
        await loader.load_all_assets_with_embeddings()
        
        # Test vector search with some example queries
        test_queries = [
            "luxury urban development with premium amenities",
            "sustainable renewable energy infrastructure",
            "mixed-use development in growing tech markets",
            "ESG-focused environmental projects",
            "institutional quality office properties"
        ]
        
        print("\n" + "="*60)
        print("TESTING VECTOR SIMILARITY SEARCH")
        print("="*60)
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            results = await loader.test_vector_search(query, limit=3)
            
            for i, result in enumerate(results, 1):
                score = result['similarity_score']
                print(f"  {i}. {result['asset_name']} ({result['platform']}) - Score: {score:.3f}")
                print(f"     Location: {result['city']}, {result['state']}")
                print(f"     Type: {result['building_type']}")
                print(f"     Platform: {result['platform']}")
                print()
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await loader.close()


if __name__ == "__main__":
    asyncio.run(main()) 