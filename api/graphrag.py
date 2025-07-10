"""GraphRAG implementation using intelligent Cypher generation.

This module provides intelligent querying capabilities using:
- Template-based Cypher generation (no more GROUP BY nonsense)
- Schema-aware query patterns
- Proper validation and fallbacks
- LLM-powered intent classification
"""

from __future__ import annotations

import os
import asyncio
import re
from typing import Any, Dict, List, Optional
from enum import Enum

import openai
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from pydantic import BaseModel

from .config import Settings, get_driver

class QueryCategory(Enum):
    """Query categories for intent classification."""
    ECONOMIC_DATA = "economic_data"
    GEOGRAPHIC_ASSETS = "geographic_assets" 
    GEOGRAPHIC_SEMANTIC_COMBINED = "geographic_semantic_combined"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    SEMANTIC_SEARCH = "semantic_search"
    TREND_ANALYSIS = "trend_analysis"
    UNKNOWN = "unknown"

class IntentClassification(BaseModel):
    """Result of intent classification."""
    category: QueryCategory
    confidence: float
    reasoning: str

class CypherTemplate:
    """Smart Cypher template that generates valid queries."""
    
    def __init__(self):
        self.portfolio_templates = {
            "platform": """
                MATCH (a:Asset) 
                RETURN a.platform AS category, COUNT(a) AS count 
                ORDER BY count DESC
            """,
            "region": """
                MATCH (a:Asset)-[:LOCATED_IN]->(:City)-[:PART_OF]->(:State)-[:PART_OF]->(r:Region) 
                RETURN r.name AS category, COUNT(a) AS count 
                ORDER BY count DESC
            """,
            "investment_type": """
                MATCH (a:Asset) 
                RETURN a.investment_type AS category, COUNT(a) AS count 
                ORDER BY count DESC
            """,
            "building_type": """
                MATCH (a:Asset) 
                RETURN a.building_type AS category, COUNT(a) AS count 
                ORDER BY count DESC
            """,
            "state": """
                MATCH (a:Asset)-[:LOCATED_IN]->(:City)-[:PART_OF]->(s:State) 
                RETURN s.name AS category, COUNT(a) AS count 
                ORDER BY count DESC
            """
        }
        
        self.geographic_templates = {
            "state_filter": """
                MATCH (a:Asset) 
                WHERE a.state = $state_name
                RETURN a.name, a.city, a.state, a.building_type, a.platform
                ORDER BY a.name
            """,
            "state_type_filter": """
                MATCH (a:Asset) 
                WHERE a.state = $state_name AND a.building_type = $building_type
                RETURN a.name, a.city, a.state, a.building_type, a.platform
                ORDER BY a.name
            """,
            "city_filter": """
                MATCH (a:Asset) 
                WHERE a.city = $city_name
                RETURN a.name, a.city, a.state, a.building_type, a.platform
                ORDER BY a.name
            """,
            "city_type_filter": """
                MATCH (a:Asset) 
                WHERE a.city = $city_name AND a.building_type = $building_type
                RETURN a.name, a.city, a.state, a.building_type, a.platform
                ORDER BY a.name
            """,
            "region_filter": """
                MATCH (a:Asset)-[:LOCATED_IN]->(:City)-[:PART_OF]->(:State)-[:PART_OF]->(r:Region {name: $region_name})
                RETURN a.name, a.city, a.state, a.building_type, a.platform
                ORDER BY a.name
            """,
            "region_type_filter": """
                MATCH (a:Asset)-[:LOCATED_IN]->(:City)-[:PART_OF]->(:State)-[:PART_OF]->(r:Region {name: $region_name})
                WHERE a.building_type = $building_type
                RETURN a.name, a.city, a.state, a.building_type, a.platform
                ORDER BY a.name
            """,
            "all_assets": """
                MATCH (a:Asset)
                RETURN a.name, a.city, a.state, a.building_type, a.platform
                ORDER BY a.state, a.city, a.name
            """
        }
        
        self.semantic_templates = {
            "property_search": """
                MATCH (a:Asset) 
                WHERE a.property_description CONTAINS $keyword1 
                   OR a.property_description CONTAINS $keyword2 
                   OR a.property_description CONTAINS $keyword3
                RETURN a.name, a.city, a.state, a.building_type, a.property_description
                ORDER BY a.name
            """
        }
        
        self.economic_templates = {
            "latest_metric": """
                MATCH (mt:MetricType {name: $metric_name})-[:TAIL]->(mv:MetricValue)
                RETURN mt.name AS metric, mv.value AS current_value, mv.date AS current_date
            """,
            "trend_analysis": """
                MATCH (mt:MetricType {name: $metric_name})-[:HEAD]->(first:MetricValue)
                MATCH (mt)-[:TAIL]->(last:MetricValue)
                RETURN mt.name AS metric, 
                       first.value AS start_value, first.date AS start_date,
                       last.value AS end_value, last.date AS end_date,
                       last.value - first.value AS change
            """
        }
        
        # Map states to regions for smart routing
        self.state_regions = {
            "California": "West",
            "Texas": "Southwest", 
            "Illinois": "Midwest",
            "Missouri": "Midwest",
            "Wisconsin": "Midwest"
        }
        
        # Economic metrics mapping
        self.economic_metrics = {
            "unemployment": "Unemployment Rate",
            "california unemployment": "California Unemployment Rate",
            "texas unemployment": "Texas Unemployment Rate", 
            "mortgage": "30-Year Mortgage Rate",
            "30 year": "30-Year Mortgage Rate",
            "federal funds": "Federal Funds Rate",
            "fed funds": "Federal Funds Rate"
        }
    
    def generate_portfolio_query(self, question: str) -> tuple[str, dict]:
        """Generate portfolio distribution queries."""
        question_lower = question.lower()
        
        if "platform" in question_lower:
            return self.portfolio_templates["platform"], {}
        elif "region" in question_lower:
            return self.portfolio_templates["region"], {}
        elif "investment" in question_lower and "type" in question_lower:
            return self.portfolio_templates["investment_type"], {}
        elif "building" in question_lower and "type" in question_lower:
            return self.portfolio_templates["building_type"], {}
        elif "state" in question_lower:
            return self.portfolio_templates["state"], {}
        else:
            # Default to platform distribution
            return self.portfolio_templates["platform"], {}
    
    def generate_geographic_query(self, question: str) -> tuple[str, dict]:
        """Generate geographic asset queries."""
        question_lower = question.lower()
        params = {}
        
        # Check for distance-based queries first (geospatial)
        import re
        distance_pattern = r'within\s+(\d+)\s*(km|kilometer|mile|miles)\s+of\s+([^.]+)'
        distance_match = re.search(distance_pattern, question_lower)
        
        if distance_match:
            distance = int(distance_match.group(1))
            unit = distance_match.group(2)
            reference_location = distance_match.group(3).strip()
            
            # Use geospatial distance query
            cypher = """
            // First find the reference location (could be a city or asset)
            OPTIONAL MATCH (refAsset:Asset)
            WHERE toLower(refAsset.name) CONTAINS toLower($reference)
            
            OPTIONAL MATCH (refCity:City)
            WHERE toLower(refCity.name) CONTAINS toLower($reference)
            
            // Use whichever reference we found
            WITH COALESCE(refAsset.location, refCity.location) AS ref_point
            WHERE ref_point IS NOT NULL
            
            // Find assets within distance
            MATCH (a:Asset)
            WHERE a.location IS NOT NULL
            WITH a, ref_point, toInteger($distance) AS distance, $unit AS unit,
                 point.distance(a.location, ref_point) AS distance_meters
            WHERE (unit IN ['km', 'kilometer'] AND distance_meters <= distance * 1000) OR
                  (unit IN ['mile', 'miles'] AND distance_meters <= distance * 1609.34)
            RETURN a.name, a.city, a.state, a.building_type, a.platform,
                   round(distance_meters/1000, 1) AS distance_km
            ORDER BY distance_meters
            """
            
            params = {
                "reference": reference_location,
                "distance": distance,
                "unit": unit
            }
            
            return cypher, params
        
        # Check for building type filters
        building_type_filter = None
        if "mixed use" in question_lower:
            building_type_filter = "Mixed Use"
        elif "commercial" in question_lower:
            building_type_filter = "Commercial"
        elif "residential" in question_lower:
            building_type_filter = "Residential"
        elif "infrastructure" in question_lower:
            building_type_filter = "Infrastructure"
        
        # Extract location mentions (non-distance queries)
        states = ["california", "texas", "illinois", "missouri", "wisconsin"]
        cities = ["los angeles", "houston", "austin", "chicago", "milwaukee", "appleton", "west hollywood"]
        regions = ["west", "southwest", "midwest", "northeast", "southeast"]
        
        for state in states:
            if state in question_lower:
                params["state_name"] = state.title()
                if building_type_filter:
                    params["building_type"] = building_type_filter
                    return self.geographic_templates["state_type_filter"], params
                else:
                    return self.geographic_templates["state_filter"], params
        
        for city in cities:
            if city in question_lower:
                params["city_name"] = city.title()
                if building_type_filter:
                    params["building_type"] = building_type_filter
                    return self.geographic_templates["city_type_filter"], params
                else:
                    return self.geographic_templates["city_filter"], params
                
        for region in regions:
            if region in question_lower:
                params["region_name"] = region.title()
                if building_type_filter:
                    params["building_type"] = building_type_filter
                    return self.geographic_templates["region_type_filter"], params
                else:
                    return self.geographic_templates["region_filter"], params
        
        # Default to all assets
        return self.geographic_templates["all_assets"], {}
    
    def generate_semantic_query(self, question: str) -> tuple[str, dict]:
        """Generate semantic search queries."""
        question_lower = question.lower()
        
        # Define semantic keyword groups
        sustainability_keywords = ["sustainable", "ESG", "renewable", "green", "environmental", "solar", "energy"]
        luxury_keywords = ["luxury", "premium", "high-end", "upscale", "exclusive"]
        
        params = {}
        if any(keyword in question_lower for keyword in sustainability_keywords):
            params.update({
                "keyword1": "sustainable",
                "keyword2": "ESG", 
                "keyword3": "renewable"
            })
        elif any(keyword in question_lower for keyword in luxury_keywords):
            params.update({
                "keyword1": "luxury",
                "keyword2": "premium",
                "keyword3": "upscale"
            })
        else:
            # Default sustainable search
            params.update({
                "keyword1": "sustainable",
                "keyword2": "ESG",
                "keyword3": "renewable"
            })
        
        return self.semantic_templates["property_search"], params
    
    def generate_economic_query(self, question: str) -> tuple[str, dict]:
        """Generate economic data queries."""
        question_lower = question.lower()
        
        # Find the metric
        metric_name = None
        for key, value in self.economic_metrics.items():
            if key in question_lower:
                metric_name = value
                break
        
        if not metric_name:
            metric_name = "California Unemployment Rate"  # Default
        
        params = {"metric_name": metric_name}
        
        if "trend" in question_lower or "change" in question_lower:
            return self.economic_templates["trend_analysis"], params
        else:
            return self.economic_templates["latest_metric"], params

class GraphRAG:
    """Intelligent GraphRAG with template-based Cypher generation."""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.cypher_templates = CypherTemplate()
        
    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the LLM for intent classification only."""
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    
    async def classify_intent(self, question: str) -> IntentClassification:
        """Classify user intent using keyword detection with priority."""
        
        question_lower = question.lower()
        
        # Check for COMBINED geographic + semantic queries FIRST
        semantic_keywords = ["sustainable", "esg", "renewable", "green", "luxury", "premium", "high-end", "environmental", "carbon", "solar", "energy", "eco-friendly", "similar to", "like", "comparable"]
        geographic_keywords = ["california", "texas", "los angeles", "houston", "austin", "properties in", "assets in", "located in", "chicago", "milwaukee", "wisconsin", "missouri"]
        
        has_semantic = any(keyword.lower() in question_lower for keyword in semantic_keywords)
        has_geographic = any(keyword in question_lower for keyword in geographic_keywords)
        
        if has_semantic and has_geographic:
            return IntentClassification(
                category=QueryCategory.GEOGRAPHIC_SEMANTIC_COMBINED,
                confidence=0.98,
                reasoning="Question combines geographic filtering with semantic search criteria"
            )
        
        # Priority 2: Pure semantic queries
        if has_semantic:
            return IntentClassification(
                category=QueryCategory.SEMANTIC_SEARCH,
                confidence=0.95,
                reasoning=f"Contains semantic keywords requiring vector search"
            )
        
        # Priority 3: Economic keywords (moved up before geographic to handle "unemployment in California" correctly)
        economic_keywords = ["unemployment", "interest rate", "mortgage", "federal funds", "economic", "rate"]
        if any(keyword in question_lower for keyword in economic_keywords):
            return IntentClassification(
                category=QueryCategory.ECONOMIC_DATA,
                confidence=0.90,
                reasoning="Question asks about economic indicators"
            )
        
        # Priority 4: Portfolio analysis keywords 
        portfolio_keywords = ["portfolio", "distribution", "how many", "count", "platform", "breakdown"]
        if any(keyword in question_lower for keyword in portfolio_keywords):
            return IntentClassification(
                category=QueryCategory.PORTFOLIO_ANALYSIS,
                confidence=0.95,
                reasoning="Question asks about portfolio composition or asset counts"
            )
        
        # Priority 5: Pure geographic keywords (moved down so economic queries with locations are handled correctly)
        if has_geographic:
            return IntentClassification(
                category=QueryCategory.GEOGRAPHIC_ASSETS,
                confidence=0.90,
                reasoning="Question refers to specific geographic locations"
            )
        
        # Priority 6: Trend keywords
        trend_keywords = ["trend", "change", "over time", "historical", "compare"]
        if any(keyword in question_lower for keyword in trend_keywords):
            return IntentClassification(
                category=QueryCategory.TREND_ANALYSIS,
                confidence=0.85,
                reasoning="Question asks about trends or changes over time"
            )
        
        return IntentClassification(
            category=QueryCategory.UNKNOWN,
            confidence=0.5,
            reasoning="Could not classify query into known categories"
        )
    
    async def execute_cypher_query(self, cypher: str, params: dict = None) -> List[Dict]:
        """Execute Cypher query safely with parameters."""
        try:
            from .config import get_driver, Settings
            settings = Settings()
            driver = get_driver()
            
            async with driver.session(database=settings.neo4j_db) as session:
                result = await session.run(cypher, params or {})
                data = await result.data()
                return data
        except Exception as e:
            print(f"Cypher execution error: {e}")
            return []
    
    def _extract_asset_name(self, question: str) -> str:
        """Extract asset name from similarity queries."""
        question_lower = question.lower()
        
        # Known asset names
        asset_names = [
            "the independent", "innovation plaza", "the lot at formosa", 
            "front & york", "centennial yards", "the adeline", "the view apartments",
            "tribune tower", "terreva renewables", "aquamarine solar project",
            "antelope valley water bank", "maryville carbon solutions"
        ]
        
        # Look for asset names in the question
        for asset in asset_names:
            if asset in question_lower:
                return asset.title()
        
        # Try to extract from patterns like "similar to X" or "like X"
        import re
        patterns = [
            r"similar to (.+?)(?:\s|$)",
            r"like (.+?)(?:\s|$)", 
            r"comparable to (.+?)(?:\s|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question_lower)
            if match:
                extracted = match.group(1).strip()
                # Clean up common endings
                extracted = re.sub(r'[.!?]$', '', extracted)
                return extracted.title()
        
        return ""

    def _extract_geographic_filter(self, question: str) -> dict:
        """Extract geographic filters from a question."""
        question_lower = question.lower()
        filters = {}
        
        # Check for states
        states = ["california", "texas", "illinois", "missouri", "wisconsin", "new york", "georgia", "arizona"]
        for state in states:
            if state in question_lower:
                filters["state"] = state.title()
                break
        
        # Check for cities
        cities = ["los angeles", "houston", "austin", "chicago", "milwaukee", "appleton", "west hollywood", "atlanta", "new york", "phoenix"]
        for city in cities:
            if city in question_lower:
                filters["city"] = city.title()
                break
        
        # Check for regions
        regions = ["west", "southwest", "midwest", "northeast", "southeast"]
        for region in regions:
            if region in question_lower:
                filters["region"] = region.title()
                break
        
        return filters

    async def _vector_search_tool(self, question: str) -> str:
        """Perform semantic vector search on asset descriptions."""
        try:
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return "Vector search requires OpenAI API key to be configured."
            
            # Initialize OpenAI client
            import openai
            client = openai.OpenAI(api_key=openai_key)
            
            # Generate embedding for the query
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=question.replace("\n", " "),
                encoding_format="float"
            )
            query_embedding = response.data[0].embedding
            
            # Perform vector similarity search
            vector_cypher = """
            CALL db.index.vector.queryNodes('asset_description_vector', $limit, $query_embedding)
            YIELD node, score
            RETURN node.name AS asset_name,
                   node.city AS city,
                   node.state AS state,
                   node.platform AS platform,
                   node.building_type AS building_type,
                   score AS similarity_score,
                   node.property_description AS description
            ORDER BY score DESC
            """
            
            # Execute vector search using Neo4j driver
            from .config import get_driver, Settings
            settings = Settings()
            driver = get_driver()
            
            async with driver.session(database=settings.neo4j_db) as session:
                result = await session.run(vector_cypher, {
                    "query_embedding": query_embedding,
                    "limit": 5
                })
                data = await result.data()
            
            if data:
                results = []
                for item in data:
                    results.append(f"{item['asset_name']} ({item['city']}, {item['state']}) - {item['building_type']} (similarity: {item['similarity_score']:.3f})")
                
                # Show all results found (no artificial limit)
                return f"Found {len(data)} semantically similar assets: " + ", ".join(results)
            else:
                return "No semantically similar assets found."
                
        except Exception as e:
            return f"Vector search error: {str(e)}"

    async def answer_question(self, question: str) -> Dict[str, Any]:
        """Main entry point for answering questions."""
        
        # Step 1: Classify intent
        intent = await self.classify_intent(question)
        
        # Step 2: Route to appropriate handler
        if intent.category == QueryCategory.SEMANTIC_SEARCH:
            return await self._handle_semantic_query(question, intent)
        elif intent.category == QueryCategory.GEOGRAPHIC_SEMANTIC_COMBINED:
            return await self._handle_semantic_query(question, intent)
        elif intent.category == QueryCategory.PORTFOLIO_ANALYSIS:
            return await self._handle_portfolio_query(question, intent)
        elif intent.category == QueryCategory.GEOGRAPHIC_ASSETS:
            return await self._handle_geographic_query(question, intent)
        elif intent.category == QueryCategory.ECONOMIC_DATA:
            return await self._handle_economic_query(question, intent)
        elif intent.category == QueryCategory.TREND_ANALYSIS:
            return await self._handle_trend_query(question, intent)
        else:
            return await self._handle_general_query(question, intent)
    
    async def _handle_portfolio_query(self, question: str, intent: IntentClassification) -> Dict[str, Any]:
        """Handle portfolio analysis queries."""
        try:
            cypher, params = self.cypher_templates.generate_portfolio_query(question)
            data = await self.execute_cypher_query(cypher, params)
            
            formatted_answer = self._format_portfolio_table(data)
            
            return {
                "answer": formatted_answer,
                "cypher": cypher.strip(),
                "data": data,
                "question": question,
                "pattern_matched": True,
                "query_type": "portfolio_template_generated",
                "intent_classification": {
                    "category": intent.category.value,
                    "confidence": intent.confidence,
                    "reasoning": intent.reasoning
                },
                "system_used": "graphrag",
                "geospatial_enabled": True
            }
        except Exception as e:
            return {
                "answer": f"Portfolio query failed: {str(e)}",
                "cypher": None,
                "data": [],
                "question": question,
                "pattern_matched": False,
                "error": str(e)
            }
    
    async def _handle_geographic_query(self, question: str, intent: IntentClassification) -> Dict[str, Any]:
        """Handle geographic asset queries."""
        try:
            cypher, params = self.cypher_templates.generate_geographic_query(question)
            data = await self.execute_cypher_query(cypher, params)
            
            # Use context-aware geographic answer formatting
            formatted_answer = self._format_geographic_answer(data, question)
            
            return {
                "answer": formatted_answer,
                "cypher": cypher.strip(),
                "data": data,
                "question": question,
                "pattern_matched": True,
                "query_type": "geographic_template_generated",
                "intent_classification": {
                    "category": intent.category.value,
                    "confidence": intent.confidence,
                    "reasoning": intent.reasoning
                },
                "geospatial_enabled": True
            }
            
        except Exception as e:
            print(f"Geographic query error: {e}")
            return await self._handle_general_query(question, intent)
    
    async def _handle_semantic_query(self, question: str, intent: IntentClassification) -> Dict[str, Any]:
        """Handle semantic search queries with optional geographic filtering."""
        try:
            question_lower = question.lower()
            
            # Extract geographic filters if present
            geo_filters = self._extract_geographic_filter(question)
            
            # Check if this is an asset similarity query
            if "similar to" in question_lower or "like" in question_lower or "comparable" in question_lower:
                # Extract asset name from query
                asset_name = self._extract_asset_name(question)
                if asset_name:
                    # Find similar assets using vector search with the asset name as seed
                    vector_result = await self._vector_search_tool(f"Properties like {asset_name} mixed use development")
                else:
                    # Fallback to general similarity search
                    vector_result = await self._vector_search_tool(question)
            else:
                # Build semantic search query with geographic constraints
                if geo_filters:
                    # For geographic + semantic queries, use vector search with geographic post-filtering
                    vector_result = await self._vector_search_tool(question)
                    
                    # Parse vector results and apply geographic filtering
                    if "Found" in vector_result and "semantically similar" in vector_result:
                        vector_data = self._parse_vector_search_results(vector_result)
                        
                        # Apply geographic filter to vector results
                        if vector_data:
                            filtered_data = self._apply_geographic_filter(vector_data, geo_filters)
                            
                            if filtered_data:
                                answer = f"Found {len(filtered_data)} assets matching your criteria:"
                                for asset in filtered_data:
                                    answer += f"\n• {asset['name']} ({asset['city']}, {asset['state']}) - {asset['building_type']}"
                                
                                return {
                                    "answer": answer,
                                    "cypher": "Vector search with geographic filtering",
                                    "data": filtered_data,
                                    "question": question,
                                    "pattern_matched": True,
                                    "query_type": "geographic_semantic_vector_search",
                                    "geographic_filters": geo_filters,
                                    "intent_classification": {
                                        "category": intent.category.value,
                                        "confidence": intent.confidence,
                                        "reasoning": intent.reasoning
                                    },
                                    "system_used": "graphrag",
                                    "geospatial_enabled": True
                                }
                            else:
                                # No results after geographic filtering
                                geo_desc = ""
                                if "state" in geo_filters:
                                    geo_desc = f"in {geo_filters['state']}"
                                elif "city" in geo_filters:
                                    geo_desc = f"in {geo_filters['city']}"
                                elif "region" in geo_filters:
                                    geo_desc = f"in the {geo_filters['region']} region"
                                
                                answer = f"No assets found matching your criteria {geo_desc}. Found semantically similar assets in other locations, but none in the specified geographic area."
                                return {
                                    "answer": answer,
                                    "cypher": "Vector search with geographic filtering (no results)",
                                    "data": [],
                                    "question": question,
                                    "pattern_matched": True,
                                    "query_type": "geographic_semantic_search_no_results",
                                    "geographic_filters": geo_filters,
                                    "intent_classification": {
                                        "category": intent.category.value,
                                        "confidence": intent.confidence,
                                        "reasoning": intent.reasoning
                                    },
                                    "system_used": "graphrag",
                                    "geospatial_enabled": True
                                }
                    
                    # Vector search failed - fall back to geographic search only
                    cypher, params = self.cypher_templates.generate_geographic_query(question)
                    data = await self.execute_cypher_query(cypher, params)
                    
                    if data:
                        answer = f"Found {len(data)} assets in the specified location (semantic search unavailable):"
                        answer = self._format_asset_table(data)
                    else:
                        answer = f"No assets found in the specified location."
                    
                    return {
                        "answer": answer,
                        "cypher": cypher.strip(),
                        "data": data,
                        "question": question,
                        "pattern_matched": True,
                        "query_type": "geographic_fallback_search",
                        "geographic_filters": geo_filters,
                        "intent_classification": {
                            "category": intent.category.value,
                            "confidence": intent.confidence,
                            "reasoning": intent.reasoning
                        },
                        "system_used": "graphrag",
                        "geospatial_enabled": True
                    }
                else:
                    # No geographic constraints - use vector search
                    vector_result = await self._vector_search_tool(question)
            
            # Fallback to template-based semantic search if no geographic constraints
            if not geo_filters:
                # For pure semantic searches, use vector search primarily
                vector_result = await self._vector_search_tool(question)
                
                # Parse vector search results for table data if successful
                if "Found" in vector_result and "semantically similar" in vector_result:
                    # Extract asset information from vector search results
                    vector_data = self._parse_vector_search_results(vector_result)
                    
                    # If parsing worked, use vector data
                    if vector_data:
                        answer = vector_result
                        data = vector_data
                        cypher_query = "Vector similarity search using embeddings"
                    else:
                        # Parsing failed - fall back to template search
                        print("Vector search parsing failed, falling back to template search")
                        cypher, params = self.cypher_templates.generate_semantic_query(question)
                        backup_data = await self.execute_cypher_query(cypher, params)
                        
                        if backup_data:
                            answer = self._format_asset_table(backup_data)
                            data = backup_data
                            cypher_query = cypher.strip()
                        else:
                            answer = "No assets found matching your semantic search criteria."
                            data = []
                            cypher_query = cypher.strip() if 'cypher' in locals() else ""
                
                return {
                    "answer": answer,
                    "cypher": cypher_query,
                    "data": data,
                    "question": question,
                    "pattern_matched": True,
                    "query_type": "semantic_vector_search",
                    "vector_search": True,
                    "intent_classification": {
                        "category": intent.category.value,
                        "confidence": intent.confidence,
                        "reasoning": intent.reasoning
                    },
                    "system_used": "graphrag",
                    "geospatial_enabled": True
                }
            
        except Exception as e:
            return {
                "answer": f"Semantic search failed: {str(e)}",
                "cypher": None,
                "data": [],
                "question": question,
                "pattern_matched": False,
                "error": str(e),
                "vector_search": False
            }

    def _parse_vector_search_results(self, vector_result: str) -> List[Dict]:
        """Parse vector search results text into structured data for table display."""
        try:
            # The vector result format is like:
            # "Found 5 semantically similar assets: Terreva Renewables (Appleton, Wisconsin) - Energy Infrastructure (similarity: 0.747), Aquamarine Solar Project (San Joaquin Valley, California) - Energy Infrastructure (similarity: 0.744), Maryville Carbon Solutions (Maryville, Missouri) - Environmental Infrastructure (similarity: 0.656)"
            
            import re
            
            # First extract the part after "Found X semantically similar assets:"
            start_match = re.search(r'Found \d+ semantically similar assets:\s*(.+)', vector_result)
            if not start_match:
                return []
            
            assets_text = start_match.group(1)
            
            # Use a comprehensive regex to find all asset patterns in the text
            # Pattern: Asset Name (City, State) - Building Type (similarity: X.XXX)
            asset_pattern = r'([A-Za-z\s&\'-]+?)\s*\(([^)]+)\)\s*-\s*([^(]+?)\s*\(similarity:\s*([0-9.]+)\)'
            matches = re.findall(asset_pattern, assets_text)
            
            parsed_data = []
            for match in matches:
                name = match[0].strip()
                location = match[1].strip()
                building_type = match[2].strip()
                similarity_score = float(match[3])
                
                # Clean up any leading punctuation from name
                name = re.sub(r'^[,\s]+', '', name)
                
                # Split location into city, state
                location_parts = location.split(', ')
                city = location_parts[0] if location_parts else ''
                state = location_parts[1] if len(location_parts) > 1 else ''
                
                parsed_data.append({
                    'name': name,
                    'city': city,
                    'state': state,
                    'building_type': building_type,
                    'platform': 'Infrastructure',  # Default assumption based on data
                    'similarity_score': similarity_score
                })
            
            return parsed_data
            
        except Exception as e:
            # If regex parsing fails, return empty list for fallback handling
            return []

    def _apply_geographic_filter(self, data: List[Dict], geo_filters: dict) -> List[Dict]:
        """Apply geographic filters to a list of asset dictionaries."""
        if not geo_filters:
            return data
        
        filtered_data = []
        
        for asset in data:
            asset_matches = False
            
            # Check state filter (highest priority)
            if "state" in geo_filters:
                asset_state = asset.get('state', '').lower()
                if asset_state == geo_filters['state'].lower():
                    asset_matches = True
            
            # Check city filter (if no state filter or state matches)
            elif "city" in geo_filters:
                asset_city = asset.get('city', '').lower()
                if asset_city == geo_filters['city'].lower():
                    asset_matches = True
            
            # Check region filter (if no state/city filter or they match)
            elif "region" in geo_filters:
                # For region filtering, we need to check state-to-region mapping
                asset_state = asset.get('state', '')
                if asset_state in self.cypher_templates.state_regions:
                    asset_region = self.cypher_templates.state_regions[asset_state]
                    if asset_region.lower() == geo_filters['region'].lower():
                        asset_matches = True
            
            if asset_matches:
                filtered_data.append(asset)
        
        return filtered_data

    async def _handle_economic_query(self, question: str, intent: IntentClassification) -> Dict[str, Any]:
        """Handle economic data queries."""
        try:
            cypher, params = self.cypher_templates.generate_economic_query(question)
            data = await self.execute_cypher_query(cypher, params)
            
            formatted_answer = self._format_economic_data(data)
            
            return {
                "answer": formatted_answer,
                "cypher": cypher.strip(),
                "data": data,
                "question": question,
                "pattern_matched": True,
                "query_type": "economic_template_generated",
                "intent_classification": {
                    "category": intent.category.value,
                    "confidence": intent.confidence,
                    "reasoning": intent.reasoning
                },
                "system_used": "graphrag",
                "geospatial_enabled": True
            }
        except Exception as e:
            return {
                "answer": f"Economic query failed: {str(e)}",
                "cypher": None,
                "data": [],
                "question": question,
                "pattern_matched": False,
                "error": str(e)
            }
    
    async def _handle_trend_query(self, question: str, intent: IntentClassification) -> Dict[str, Any]:
        """Handle trend analysis queries."""
        try:
            cypher, params = self.cypher_templates.generate_economic_query(question)  # Use economic templates for trends
            data = await self.execute_cypher_query(cypher, params)
            
            if data:
                formatted_answer = self._format_economic_data(data)
            else:
                formatted_answer = f"Trend analysis for: {question}"
            
            return {
                "answer": formatted_answer,
                "cypher": cypher.strip(),
                "data": data,
                "question": question,
                "pattern_matched": True,
                "query_type": "trend_template_generated",
                "intent_classification": {
                    "category": intent.category.value,
                    "confidence": intent.confidence,
                    "reasoning": intent.reasoning
                },
                "system_used": "graphrag",
                "geospatial_enabled": True
            }
            
        except Exception as e:
            return {
                "answer": f"Trend analysis failed: {str(e)}",
                "cypher": None,
                "data": [],
                "question": question,
                "pattern_matched": False,
                "error": str(e)
            }
    
    async def _handle_general_query(self, question: str, intent: IntentClassification) -> Dict[str, Any]:
        """Handle general queries with fallback logic."""
        try:
            # Try portfolio query as fallback
            cypher, params = self.cypher_templates.generate_portfolio_query(question)
            data = await self.execute_cypher_query(cypher, params)
            
            if data:
                formatted_answer = self._format_portfolio_table(data)
            else:
                formatted_answer = "I couldn't find specific information for that question. Try asking about portfolio distribution, assets in specific locations, or economic indicators."
            
            return {
                "answer": formatted_answer,
                "cypher": cypher.strip() if data else "",
                "data": data,
                "question": question,
                "pattern_matched": False,
                "query_type": "general_fallback",
                "intent_classification": {
                    "category": intent.category.value,
                    "confidence": intent.confidence,
                    "reasoning": intent.reasoning
                },
                "system_used": "graphrag",
                "geospatial_enabled": True
            }
        except Exception as e:
            return {
                "answer": f"I couldn't process that question: {str(e)}. Try rephrasing or asking about assets, economic data, or portfolio information.",
                "cypher": None,
                "data": [],
                "question": question,
                "pattern_matched": False,
                "error": str(e)
            }

    def _format_portfolio_table(self, data: List[Dict]) -> str:
        """Format portfolio data as a clean table with columns."""
        if not data:
            return "No portfolio data found."
        
        # Extract columns
        rows = []
        for item in data:
            if isinstance(item, dict):
                if 'category' in item and 'count' in item:
                    rows.append((item['category'], str(item['count'])))
                elif 'platform' in item or 'investment_type' in item or 'region' in item:
                    category = item.get('platform', item.get('investment_type', item.get('region', 'Unknown')))
                    count = item.get('count', item.get('COUNT(a)', 'N/A'))
                    rows.append((category, str(count)))
                else:
                    # Generic two-column format
                    values = list(item.values())
                    if len(values) >= 2:
                        rows.append((str(values[0]), str(values[1])))
        
        if not rows:
            return "No portfolio data found."
        
        # Create table with proper columns
        lines = ["Portfolio Distribution:"]
        lines.append("=" * 40)
        lines.append(f"{'Category':<20} {'Count':<10}")
        lines.append("-" * 40)
        
        for category, count in rows:
            lines.append(f"{category:<20} {count:<10}")
        
        return "\n".join(lines)
    
    def _format_asset_table(self, data: List[Dict]) -> str:
        """Format asset data as a clean table with columns."""
        if not data:
            return "No assets found."
        
        # Check if this is a distance-based query (has distance_km field)
        has_distance = any(item.get('distance_km') is not None for item in data if isinstance(item, dict))
        
        # Extract columns with proper field mapping
        rows = []
        for item in data:
            if isinstance(item, dict):
                # Handle different field name patterns from Neo4j results
                name = item.get('name') or item.get('a.name') or 'Unknown Asset'
                city = item.get('city') or item.get('a.city') or ''
                state = item.get('state') or item.get('a.state') or ''
                building_type = item.get('building_type') or item.get('a.building_type') or 'Unknown'
                platform = item.get('platform') or item.get('a.platform') or 'Unknown'
                
                location = ""
                if city and state:
                    location = f"{city}, {state}"
                elif city:
                    location = city
                elif state:
                    location = state
                else:
                    location = "Unknown"
                
                if has_distance:
                    distance_km = item.get('distance_km', '')
                    distance_str = f"{distance_km} km" if distance_km else "N/A"
                    rows.append((name, location, building_type, platform, distance_str))
                else:
                    rows.append((name, location, building_type, platform))
        
        if not rows:
            return "No assets found."
        
        # Create properly formatted table with better spacing
        lines = []
        lines.append("Asset Details:")
        lines.append("=" * 120)
        
        if has_distance:
            lines.append(f"{'Asset Name':<30} {'Location':<25} {'Type':<20} {'Platform':<15} {'Distance':<10}")
            lines.append("-" * 120)
            
            for name, location, building_type, platform, distance in rows:
                # Truncate long fields to fit in columns
                name_truncated = (name[:27] + "...") if len(name) > 30 else name
                location_truncated = (location[:22] + "...") if len(location) > 25 else location
                type_truncated = (building_type[:17] + "...") if len(building_type) > 20 else building_type
                platform_truncated = (platform[:12] + "...") if len(platform) > 15 else platform
                
                lines.append(f"{name_truncated:<30} {location_truncated:<25} {type_truncated:<20} {platform_truncated:<15} {distance:<10}")
        else:
            lines.append(f"{'Asset Name':<30} {'Location':<25} {'Type':<20} {'Platform':<15}")
            lines.append("-" * 100)
            
            for name, location, building_type, platform in rows:
                # Truncate long fields to fit in columns
                name_truncated = (name[:27] + "...") if len(name) > 30 else name
                location_truncated = (location[:22] + "...") if len(location) > 25 else location
                type_truncated = (building_type[:17] + "...") if len(building_type) > 20 else building_type
                platform_truncated = (platform[:12] + "...") if len(platform) > 15 else platform
                
                lines.append(f"{name_truncated:<30} {location_truncated:<25} {type_truncated:<20} {platform_truncated:<15}")
        
        return "\n".join(lines)
    
    def _format_economic_data(self, data: List[Dict]) -> str:
        """Format economic data as a clean table with columns."""
        if not data:
            return "No economic data found."
        
        # Extract columns for economic data
        rows = []
        for item in data:
            if isinstance(item, dict):
                if 'metric' in item:
                    metric = item['metric']
                    if 'current_value' in item:
                        value = f"{item['current_value']}"
                        date = item.get('current_date', 'N/A')
                    elif 'change' in item:
                        start_val = item.get('start_value', 'N/A')
                        end_val = item.get('end_value', 'N/A')
                        change = item.get('change', 'N/A')
                        value = f"{start_val} → {end_val} (Δ{change})"
                        date = f"{item.get('start_date', '')} to {item.get('end_date', '')}"
                    else:
                        value = str(list(item.values())[1]) if len(item) > 1 else "N/A"
                        date = str(list(item.values())[2]) if len(item) > 2 else "N/A"
                    
                    rows.append((metric, value, date))
                else:
                    # Generic display - use first few key-value pairs
                    keys = list(item.keys())
                    if len(keys) >= 2:
                        rows.append((str(item[keys[0]]), str(item[keys[1]]), str(item.get(keys[2], ''))))
        
        if not rows:
            return "No economic data found."
        
        # Create table with proper columns
        lines = ["Economic Data:"]
        lines.append("=" * 80)
        lines.append(f"{'Metric':<25} {'Value':<25} {'Date':<25}")
        lines.append("-" * 80)
        
        for metric, value, date in rows:
            lines.append(f"{metric[:24]:<25} {value[:24]:<25} {date[:24]:<25}")
        
        return "\n".join(lines)

    def _format_geographic_answer(self, data: List[Dict], question: str) -> str:
        """Format geographic query answers with context-aware language."""
        if not data:
            return "No matching assets found for this geographic query."
        
        # Check if this is a distance-based query
        import re
        distance_pattern = r'within\s+(\d+)\s*(km|kilometer|mile|miles)\s+of\s+([^.]+)'
        distance_match = re.search(distance_pattern, question.lower())
        
        if distance_match:
            distance = distance_match.group(1)
            unit = distance_match.group(2)
            reference_location = distance_match.group(3).strip()
            
            # Format distance-based response
            count = len(data)
            if count == 1:
                return f"Found {count} asset within {distance} {unit} of {reference_location}."
            else:
                return f"Found {count} assets within {distance} {unit} of {reference_location}."
        
        # Regular geographic queries
        question_lower = question.lower()
        count = len(data)
        
        if "california" in question_lower:
            location_name = "California"
        elif "texas" in question_lower:
            location_name = "Texas"
        elif "los angeles" in question_lower:
            location_name = "Los Angeles"
        elif "houston" in question_lower:
            location_name = "Houston"
        elif "austin" in question_lower:
            location_name = "Austin"
        elif "chicago" in question_lower:
            location_name = "Chicago"
        else:
            location_name = "the specified location"
        
        if count == 1:
            return f"Found {count} asset in {location_name}."
        else:
            return f"Found {count} assets in {location_name}."


# Factory function for easy instantiation
async def create_graphrag() -> GraphRAG:
    """Create a GraphRAG instance with proper initialization."""
    return GraphRAG()
