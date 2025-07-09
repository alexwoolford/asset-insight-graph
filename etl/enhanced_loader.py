"""
Enhanced Vector Embedding Loader for CIM Assets

This module loads enhanced property descriptions into Neo4j with vector embeddings.
Uses verified information from CIM Group sources enhanced with OpenAI.
"""

import asyncio
import json
import os
import time
from typing import Dict, Any, List

import openai

from vector_loader import VectorEmbeddingLoader


class EnhancedVectorEmbeddingLoader(VectorEmbeddingLoader):
    """Load enhanced CIM assets with vector embeddings into Neo4j."""
    
    def __init__(self):
        super().__init__()  # This will handle OpenAI client initialization
    
    async def load_all_enhanced_assets(self):
        """Load all enhanced assets with embeddings."""
        
        # Load enhanced asset data
        enhanced_file = "cim_assets_enhanced.jsonl"
        if not os.path.exists(enhanced_file):
            print(f"❌ Enhanced asset file not found: {enhanced_file}")
            print("   Run: python descriptions.py first")
            return
        
        print(f"📂 Loading enhanced assets with embeddings...")
        
        # Use parent class method with enhanced data file
        await self.load_all_assets_with_embeddings(enhanced_file)
        
        print(f"✅ Loaded enhanced assets with vector embeddings")
    
    async def verify_enhanced_setup(self):
        """Verify that enhanced vector search is working."""
        print("\n🧪 Testing enhanced vector search...")
        
        # Test vector search using parent class method
        test_query = "solar renewable energy projects"
        results = await self.test_vector_search(test_query, limit=3)
        
        if results:
            print("✅ Enhanced vector search working!")
            print("   Top matches for 'solar renewable energy projects':")
            for item in results:
                score = item['similarity_score']
                print(f"   - {item['asset_name']} (score: {score:.3f})")
        else:
            print("❌ No vector search results - check index creation")


async def main():
    """Load enhanced CIM assets with vector embeddings."""
    
    print("🏢 Loading Enhanced CIM Assets with Vector Embeddings")
    print("=" * 60)
    
    loader = EnhancedVectorEmbeddingLoader()
    
    try:
        # Load enhanced assets with embeddings
        print("\n📂 Loading enhanced assets...")
        await loader.load_all_enhanced_assets()
        
        # Verify setup
        await loader.verify_enhanced_setup()
        
        print("\n🎉 Enhanced vector loading complete!")
        print("💡 All descriptions are based on actual CIM Group website content")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await loader.close()


if __name__ == "__main__":
    asyncio.run(main()) 