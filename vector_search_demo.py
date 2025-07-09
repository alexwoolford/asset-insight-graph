#!/usr/bin/env python3
"""
Vector Search Demo for CIM Asset Insight Graph

This demo showcases the complete vector search implementation:
1. Enhanced property descriptions
2. OpenAI embeddings generation  
3. Neo4j vector indexing
4. Semantic similarity search

Prerequisites:
- Neo4j running with asset data loaded
- OpenAI API key in environment variable OPENAI_API_KEY
- Python dependencies installed (openai, neo4j)
"""

import asyncio
import os
import sys
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.property_descriptions import generate_enhanced_dataset
from etl.vector_loader import VectorEmbeddingLoader


class VectorSearchDemo:
    """Comprehensive demo of vector search capabilities for CIM assets."""
    
    def __init__(self):
        """Initialize the demo."""
        self.loader = None
        
    async def setup(self):
        """Set up the vector search demo."""
        print("🚀 CIM Asset Vector Search Demo")
        print("=" * 60)
        
        # Check prerequisites
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ Error: OPENAI_API_KEY environment variable is required")
            print("   Set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
            return False
        
        try:
            self.loader = VectorEmbeddingLoader()
            print("✅ Vector embedding loader initialized")
            return True
        except Exception as e:
            print(f"❌ Error initializing loader: {e}")
            return False
    
    async def generate_descriptions(self):
        """Step 1: Generate enhanced property descriptions."""
        print("\n📝 Step 1: Generating Enhanced Property Descriptions")
        print("-" * 50)
        
        try:
            # Change to etl directory to run the script
            original_dir = os.getcwd()
            etl_dir = os.path.join(os.path.dirname(__file__), "etl")
            os.chdir(etl_dir)
            
            # Generate enhanced descriptions
            enhanced_assets = generate_enhanced_dataset()
            
            # Save enhanced dataset
            with open("cim_assets_enhanced.jsonl", "w") as f:
                import json
                for asset in enhanced_assets:
                    f.write(json.dumps(asset) + "\n")
            
            print(f"✅ Generated descriptions for {len(enhanced_assets)} assets")
            
            # Show sample
            sample = enhanced_assets[0]
            print(f"\n📋 Sample Description for '{sample['name']}':")
            print(f"   Platform: {sample['platform']}")
            print(f"   Type: {sample['building_type']}")
            print(f"   Themes: {', '.join(sample['investment_themes'][:3])}...")
            print(f"   Description: {sample['property_description'][:200]}...")
            
            os.chdir(original_dir)
            return True
            
        except Exception as e:
            print(f"❌ Error generating descriptions: {e}")
            os.chdir(original_dir)
            return False
    
    async def load_vectors(self):
        """Step 2: Generate embeddings and load into Neo4j."""
        print("\n🧠 Step 2: Generating Vector Embeddings")
        print("-" * 50)
        
        try:
            # Change to etl directory
            original_dir = os.getcwd()
            etl_dir = os.path.join(os.path.dirname(__file__), "etl")
            os.chdir(etl_dir)
            
            # Load all assets with embeddings
            await self.loader.load_all_assets_with_embeddings()
            
            os.chdir(original_dir)
            print("✅ All assets loaded with vector embeddings")
            return True
            
        except Exception as e:
            print(f"❌ Error loading vectors: {e}")
            os.chdir(original_dir)
            return False
    
    async def test_semantic_search(self):
        """Step 3: Test semantic similarity search."""
        print("\n🔍 Step 3: Testing Semantic Similarity Search")
        print("-" * 50)
        
        # Test queries showcasing different search capabilities
        test_scenarios = [
            {
                "title": "ESG & Sustainability Search",
                "query": "sustainable renewable energy with environmental benefits",
                "description": "Find assets focused on environmental sustainability"
            },
            {
                "title": "Investment Strategy Search", 
                "query": "premium institutional quality urban development",
                "description": "Find high-quality real estate investments"
            },
            {
                "title": "Technology & Innovation Search",
                "query": "tech hub with modern amenities for startups",
                "description": "Find properties suitable for technology companies"
            },
            {
                "title": "Mixed-Use Community Search",
                "query": "live work play vibrant community development",
                "description": "Find mixed-use developments with community focus"
            },
            {
                "title": "Infrastructure & Utilities Search",
                "query": "essential infrastructure with stable contracted revenue",
                "description": "Find infrastructure assets with steady income"
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n🎯 {scenario['title']}")
            print(f"   Query: '{scenario['query']}'")
            print(f"   Goal: {scenario['description']}")
            
            try:
                results = await self.loader.test_vector_search(scenario['query'], limit=3)
                
                if results:
                    print(f"   Results: Found {len(results)} matches")
                    for i, result in enumerate(results, 1):
                        score = result['similarity_score']
                        print(f"   {i}. {result['asset_name']} - Score: {score:.3f}")
                        print(f"      📍 {result['city']}, {result['state']} ({result['platform']})")
                        print(f"      🏢 Type: {result['building_type']}")
                        
                        # Show matching themes
                        if result.get('investment_themes'):
                            themes = result['investment_themes'][:3]
                            print(f"      💡 Themes: {', '.join(themes)}")
                        print()
                else:
                    print("   No matches found")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        return True
    
    async def demonstrate_api_integration(self):
        """Step 4: Show API integration examples."""
        print("\n🌐 Step 4: API Integration Examples")
        print("-" * 50)
        
        print("The vector search is now integrated into the Asset Insight Graph API!")
        print("\nExample API calls that will trigger vector search:")
        
        api_examples = [
            "sustainable renewable energy projects",
            "luxury urban developments", 
            "ESG-focused investments",
            "properties similar to Tribune Tower",
            "assets with premium amenities"
        ]
        
        for query in api_examples:
            print(f"  POST /qa {{\"question\": \"{query}\"}}")
        
        print(f"\n💡 The API will automatically detect semantic queries and use vector search")
        print(f"   when patterns like 'sustainable', 'luxury', 'similar to' are detected.")
        
        print(f"\n🎨 UI Integration:")
        print(f"   - New example questions added to Streamlit UI")
        print(f"   - Vector search results display similarity scores")
        print(f"   - Enhanced property descriptions shown in results")
        
        return True
    
    async def show_architecture_summary(self):
        """Show the complete architecture overview."""
        print("\n🏗️  Complete Vector Search Architecture")
        print("=" * 60)
        
        print("📊 Data Flow:")
        print("  1. Raw asset metadata → Enhanced descriptions (property_descriptions.py)")
        print("  2. Descriptions → OpenAI embeddings → Neo4j vector index (vector_loader.py)")
        print("  3. User query → Embedding → Vector similarity search → Ranked results")
        
        print("\n🧩 Components:")
        print("  • Enhanced Property Descriptions: Rich, contextual asset descriptions")
        print("  • OpenAI text-embedding-3-small: 1536-dimension vectors")
        print("  • Neo4j Vector Index: Cosine similarity search")
        print("  • API Integration: Automatic pattern detection")
        print("  • UI Integration: Semantic example questions")
        
        print("\n🔍 Search Capabilities:")
        print("  • Semantic Property Discovery: 'Find luxury developments'")
        print("  • Investment Strategy Matching: 'ESG-focused sustainable assets'")
        print("  • Market Similarity: 'Properties in tech innovation hubs'")
        print("  • Asset Comparison: 'Assets similar to Tribune Tower'")
        
        print("\n✨ Benefits:")
        print("  • Goes beyond keyword matching to understand meaning")
        print("  • Discovers unexpected connections between assets")
        print("  • Supports investment strategy alignment")
        print("  • Enables natural language asset exploration")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.loader:
            await self.loader.close()
    
    async def run_complete_demo(self):
        """Run the complete vector search demo."""
        try:
            # Setup
            if not await self.setup():
                return
            
            # Step 1: Generate descriptions
            if not await self.generate_descriptions():
                return
            
            # Step 2: Load vectors (requires OpenAI API key)
            print("\n⚠️  Note: Step 2 requires OpenAI API key and will make API calls")
            response = input("Continue with vector embedding generation? (y/N): ")
            if response.lower() == 'y':
                if not await self.load_vectors():
                    return
                
                # Step 3: Test search
                await self.test_semantic_search()
            else:
                print("⏭️  Skipping vector generation - showing integration examples only")
            
            # Step 4: Show API integration
            await self.demonstrate_api_integration()
            
            # Architecture summary
            await self.show_architecture_summary()
            
            print("\n🎉 Vector Search Demo Complete!")
            print("Your CIM Asset Insight Graph now supports semantic similarity search!")
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Demo interrupted by user")
        except Exception as e:
            print(f"\n❌ Demo error: {e}")
        finally:
            await self.cleanup()


async def main():
    """Run the vector search demo."""
    demo = VectorSearchDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main()) 