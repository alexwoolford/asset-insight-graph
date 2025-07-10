"""GraphRAG implementation using LangGraph workflow orchestration.

This module provides intelligent querying capabilities using:
- LangGraph workflow orchestration
- Template-based Cypher generation  
- Schema-aware query patterns
- Proper validation and fallbacks
- LLM-powered intent classification
"""

from __future__ import annotations

import os
import asyncio
import re
from typing import Any, Dict, List, Optional, TypedDict
from enum import Enum

import openai
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from pydantic import BaseModel
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

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

class AssetGraphState(TypedDict):
    """State for the asset analysis workflow."""
    question: str
    intent: Optional[IntentClassification]
    cypher_query: Optional[str]
    cypher_params: Optional[Dict]
    raw_data: Optional[List[Dict]]
    answer: str
    formatted_data: Optional[List[Dict]]
    workflow_steps: List[str]
    error_messages: List[str]
    query_type: str
    pattern_matched: bool

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
    """LangGraph-based GraphRAG with proper workflow orchestration"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.cypher_templates = CypherTemplate()
        self.workflow = self._build_workflow()
        
    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the LLM for intent classification"""
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with proper state transitions"""
        
        workflow = StateGraph(AssetGraphState)
        
        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("portfolio_analysis", self._portfolio_analysis_node)
        workflow.add_node("geographic_search", self._geographic_search_node)
        workflow.add_node("semantic_search", self._semantic_search_node)
        workflow.add_node("economic_data", self._economic_data_node)
        workflow.add_node("format_response", self._format_response_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        # Add conditional routing from intent classification
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "portfolio_analysis": "portfolio_analysis",
                "geographic_search": "geographic_search", 
                "semantic_search": "semantic_search",
                "economic_data": "economic_data",
                "error": "handle_error"
            }
        )
        
        # All processing nodes go to response formatting
        workflow.add_edge("portfolio_analysis", "format_response")
        workflow.add_edge("geographic_search", "format_response")
        workflow.add_edge("semantic_search", "format_response")
        workflow.add_edge("economic_data", "format_response")
        workflow.add_edge("handle_error", "format_response")
        
        # End at format_response
        workflow.set_finish_point("format_response")
        
        return workflow
    
    async def _execute_cypher_query(self, cypher: str, params: dict = None) -> List[Dict]:
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
    
    async def _classify_intent_node(self, state: AssetGraphState) -> AssetGraphState:
        """Node: Classify user intent using keyword detection with priority."""
        try:
            question = state["question"]
            steps = state.get("workflow_steps", [])
            steps.append("classify_intent")
            
            question_lower = question.lower()
            
            # Check for COMBINED geographic + semantic queries FIRST
            semantic_keywords = ["sustainable", "esg", "renewable", "green", "luxury", "premium", "high-end", "environmental", "carbon", "solar", "energy", "eco-friendly", "similar to", "like", "comparable"]
            geographic_keywords = ["california", "texas", "los angeles", "houston", "austin", "properties in", "assets in", "located in", "chicago", "milwaukee", "wisconsin", "missouri"]
            
            has_semantic = any(keyword.lower() in question_lower for keyword in semantic_keywords)
            has_geographic = any(keyword in question_lower for keyword in geographic_keywords)
            
            if has_semantic and has_geographic:
                intent = IntentClassification(
                    category=QueryCategory.GEOGRAPHIC_SEMANTIC_COMBINED,
                    confidence=0.98,
                    reasoning="Question combines geographic filtering with semantic search criteria"
                )
            elif has_semantic:
                intent = IntentClassification(
                    category=QueryCategory.SEMANTIC_SEARCH,
                    confidence=0.95,
                    reasoning=f"Contains semantic keywords requiring vector search"
                )
            elif any(keyword in question_lower for keyword in ["unemployment", "interest rate", "mortgage", "federal funds", "economic", "rate"]):
                intent = IntentClassification(
                    category=QueryCategory.ECONOMIC_DATA,
                    confidence=0.90,
                    reasoning="Question asks about economic indicators"
                )
            elif any(keyword in question_lower for keyword in ["portfolio", "distribution", "how many", "count", "platform", "breakdown"]):
                intent = IntentClassification(
                    category=QueryCategory.PORTFOLIO_ANALYSIS,
                    confidence=0.95,
                    reasoning="Question asks about portfolio composition or asset counts"
                )
            elif has_geographic:
                intent = IntentClassification(
                    category=QueryCategory.GEOGRAPHIC_ASSETS,
                    confidence=0.90,
                    reasoning="Question refers to specific geographic locations"
                )
            elif any(keyword in question_lower for keyword in ["trend", "change", "over time", "historical", "compare"]):
                intent = IntentClassification(
                    category=QueryCategory.TREND_ANALYSIS,
                    confidence=0.85,
                    reasoning="Question asks about trends or changes over time"
                )
            else:
                intent = IntentClassification(
                    category=QueryCategory.UNKNOWN,
                    confidence=0.5,
                    reasoning="Could not classify query into known categories"
                )
            
            return {
                **state,
                "intent": intent,
                "workflow_steps": steps
            }
            
        except Exception as e:
            error_messages = state.get("error_messages", [])
            error_messages.append(f"Intent classification error: {str(e)}")
            return {
                **state,
                "intent": IntentClassification(
                    category=QueryCategory.UNKNOWN,
                    confidence=0.0,
                    reasoning=f"Classification failed: {str(e)}"
                ),
                "workflow_steps": steps,
                "error_messages": error_messages
            }
    
    def _route_by_intent(self, state: AssetGraphState) -> str:
        """Route to appropriate processing node based on intent"""
        intent = state.get("intent")
        if not intent:
            return "error"
        
        if intent.category == QueryCategory.PORTFOLIO_ANALYSIS:
            return "portfolio_analysis"
        elif intent.category in [QueryCategory.GEOGRAPHIC_ASSETS, QueryCategory.GEOGRAPHIC_SEMANTIC_COMBINED]:
            return "geographic_search"
        elif intent.category == QueryCategory.SEMANTIC_SEARCH:
            return "semantic_search"
        elif intent.category == QueryCategory.ECONOMIC_DATA:
            return "economic_data"
        else:
            return "error" 

    async def _portfolio_analysis_node(self, state: AssetGraphState) -> AssetGraphState:
        """Node: Handle portfolio analysis queries"""
        try:
            question = state["question"]
            steps = state.get("workflow_steps", [])
            steps.append("portfolio_analysis")
            
            # Generate query using existing template logic
            cypher, params = self.cypher_templates.generate_portfolio_query(question)
            
            # Execute query
            data = await self._execute_cypher_query(cypher, params)
            
            return {
                **state,
                "cypher_query": cypher,
                "cypher_params": params,
                "raw_data": data,
                "formatted_data": data,  # Ensure formatted_data is set
                "query_type": "portfolio_template_generated",
                "pattern_matched": True,
                "workflow_steps": steps
            }
            
        except Exception as e:
            error_messages = state.get("error_messages", [])
            error_messages.append(f"Portfolio analysis error: {str(e)}")
            return {
                **state,
                "workflow_steps": steps,
                "error_messages": error_messages,
                "pattern_matched": False
            }

    async def _geographic_search_node(self, state: AssetGraphState) -> AssetGraphState:
        """Node: Handle geographic search queries including combined semantic+geographic"""
        try:
            question = state["question"]
            intent = state.get("intent")
            steps = state.get("workflow_steps", [])
            steps.append("geographic_search")
            
            # Handle combined geographic + semantic queries with PROPER vector search
            if intent and intent.category == QueryCategory.GEOGRAPHIC_SEMANTIC_COMBINED:
                try:
                    # Extract location from question
                    question_lower = question.lower()
                    location_state = None
                    location_city = None
                    
                    if "california" in question_lower:
                        location_state = "California"
                    elif "texas" in question_lower:
                        location_state = "Texas"
                    elif "los angeles" in question_lower:
                        location_city = "Los Angeles"
                        location_state = "California"
                    
                    # Use vector search for semantic matching, then filter by location
                    import openai
                    
                    # Get embeddings for the semantic part of the question
                    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                    embedding_response = await client.embeddings.create(
                        model="text-embedding-ada-002",
                        input=question
                    )
                    query_embedding = embedding_response.data[0].embedding
                    
                    # Search for semantically similar assets, then filter by location
                    if location_state and location_city:
                        cypher = """
                        CALL db.index.vector.queryNodes('asset_description_vector', 10, $embedding) 
                        YIELD node AS asset, score
                        WHERE asset.state = $state AND asset.city = $city
                        RETURN asset.name AS name, 
                               asset.city + ', ' + asset.state AS location,
                               asset.building_type AS type,
                               asset.platform AS platform,
                               score
                        ORDER BY score DESC
                        LIMIT 5
                        """
                        params = {"embedding": query_embedding, "state": location_state, "city": location_city}
                    elif location_state:
                        cypher = """
                        CALL db.index.vector.queryNodes('asset_description_vector', 10, $embedding) 
                        YIELD node AS asset, score
                        WHERE asset.state = $state
                        RETURN asset.name AS name, 
                               asset.city + ', ' + asset.state AS location,
                               asset.building_type AS type,
                               asset.platform AS platform,
                               score
                        ORDER BY score DESC
                        LIMIT 5
                        """
                        params = {"embedding": query_embedding, "state": location_state}
                    else:
                        # No location specified, just do semantic search
                        cypher = """
                        CALL db.index.vector.queryNodes('asset_description_vector', 5, $embedding) 
                        YIELD node AS asset, score
                        RETURN asset.name AS name, 
                               asset.city + ', ' + asset.state AS location,
                               asset.building_type AS type,
                               asset.platform AS platform,
                               score
                        ORDER BY score DESC
                        """
                        params = {"embedding": query_embedding}
                    
                    data = await self._execute_cypher_query(cypher, params)
                    
                    if data:
                        asset_list = []
                        for record in data:
                            asset_list.append(f"• {record['name']} ({record['location']}) - {record['type']} (similarity: {record['score']:.3f})")
                        answer = f"Found {len(data)} assets matching your criteria:\n" + "\n".join(asset_list)
                    else:
                        # More accurate response since we actually searched
                        if location_state:
                            answer = f"No assets in {location_state} match the semantic criteria '{question}'"
                        else:
                            answer = "No assets found matching the combined geographic and semantic criteria."
                    
                    return {
                        **state,
                        "cypher_query": "Vector similarity search with geographic filtering",
                        "cypher_params": params,
                        "raw_data": data,
                        "formatted_data": data,  # Ensure formatted_data is set
                        "answer": answer,
                        "query_type": "geographic_semantic_combined_vector",
                        "pattern_matched": bool(data),
                        "workflow_steps": steps
                    }
                    
                except Exception as combined_error:
                    error_messages = state.get("error_messages", [])
                    error_messages.append(f"Combined search error: {str(combined_error)}")
                    return {
                        **state,
                        "workflow_steps": steps,
                        "error_messages": error_messages,
                        "pattern_matched": False,
                        "raw_data": [],
                        "formatted_data": []
                    }
            else:
                # Regular geographic query
                cypher, params = self.cypher_templates.generate_geographic_query(question)
                data = await self._execute_cypher_query(cypher, params)
                
                return {
                    **state,
                    "cypher_query": cypher,
                    "cypher_params": params,
                    "raw_data": data,
                    "formatted_data": data,  # Ensure formatted_data is set
                    "query_type": "geographic_template_generated",
                    "pattern_matched": True,
                    "workflow_steps": steps
                }
                
        except Exception as e:
            error_messages = state.get("error_messages", [])
            error_messages.append(f"Geographic search error: {str(e)}")
            return {
                **state,
                "workflow_steps": steps,
                "error_messages": error_messages,
                "pattern_matched": False,
                "raw_data": [],
                "formatted_data": []
            }

    async def _semantic_search_node(self, state: AssetGraphState) -> AssetGraphState:
        """Node: Handle semantic search queries using vector search"""
        try:
            question = state["question"]
            steps = state.get("workflow_steps", [])
            steps.append("semantic_search")
            
            # Use vector search for semantic queries
            import openai
            
            # Get embeddings for the question
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            embedding_response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=question
            )
            query_embedding = embedding_response.data[0].embedding
            
            # Use vector similarity search
            cypher = """
            CALL db.index.vector.queryNodes('asset_description_vector', 5, $embedding) 
            YIELD node AS asset, score
            RETURN asset.name AS name, 
                   asset.city + ', ' + asset.state AS location,
                   asset.building_type AS type,
                   asset.platform AS platform,
                   score
            ORDER BY score DESC
            """
            params = {"embedding": query_embedding}
            
            data = await self._execute_cypher_query(cypher, params)
            
            if data:
                asset_list = []
                for record in data:
                    asset_list.append(f"• {record['name']} ({record['location']}) - {record['type']} (similarity: {record['score']:.3f})")
                answer = f"Found {len(data)} semantically similar assets:\n" + "\n".join(asset_list)
            else:
                answer = "No semantically similar assets found."
            
            return {
                **state,
                "cypher_query": "Vector similarity search",
                "cypher_params": params,
                "raw_data": data,
                "formatted_data": data,  # Ensure formatted_data is set
                "answer": answer,
                "query_type": "semantic_vector_search",
                "pattern_matched": bool(data),
                "workflow_steps": steps
            }
            
        except Exception as e:
            error_messages = state.get("error_messages", [])
            error_messages.append(f"Semantic search error: {str(e)}")
            return {
                **state,
                "workflow_steps": steps,
                "error_messages": error_messages,
                "pattern_matched": False,
                "raw_data": [],
                "formatted_data": [],
                "answer": "Error in semantic search",
                "query_type": "semantic_search_error"
            } 

    async def _economic_data_node(self, state: AssetGraphState) -> AssetGraphState:
        """Node: Handle economic data queries"""
        try:
            question = state["question"]
            steps = state.get("workflow_steps", [])
            steps.append("economic_data")
            
            # Generate query using existing template logic
            cypher, params = self.cypher_templates.generate_economic_query(question)
            
            # Execute query
            data = await self._execute_cypher_query(cypher, params)
            
            return {
                **state,
                "cypher_query": cypher,
                "cypher_params": params,
                "raw_data": data,
                "formatted_data": data,  # Ensure formatted_data is set
                "query_type": "economic_template_generated",
                "pattern_matched": True,
                "workflow_steps": steps
            }
            
        except Exception as e:
            error_messages = state.get("error_messages", [])
            error_messages.append(f"Economic data error: {str(e)}")
            return {
                **state,
                "workflow_steps": steps,
                "error_messages": error_messages,
                "pattern_matched": False
            }
    
    async def _handle_error_node(self, state: AssetGraphState) -> AssetGraphState:
        """Node: Handle errors gracefully"""
        steps = state.get("workflow_steps", [])
        steps.append("handle_error")
        
        # Provide helpful error response
        return {
            **state,
            "answer": "I couldn't process that question. Try asking about portfolio distribution, assets in specific locations, or economic indicators.",
            "raw_data": [],
            "formatted_data": [],  # Ensure formatted_data is set
            "query_type": "error_fallback",
            "pattern_matched": False,
            "workflow_steps": steps
        }
    
    async def _format_response_node(self, state: AssetGraphState) -> AssetGraphState:
        """Node: Format the final response"""
        try:
            steps = state.get("workflow_steps", [])
            steps.append("format_response")
            
            # If answer is already set (from semantic search), use it
            if state.get("answer"):
                return {
                    **state,
                    "workflow_steps": steps
                }
            
            # Otherwise format based on data and query type
            data = state.get("raw_data", [])
            query_type = state.get("query_type", "")
            question = state.get("question", "")
            
            # Serialize Neo4j types before formatting to prevent errors
            from api.main import serialize_neo4j_types
            serialized_data = serialize_neo4j_types(data)
            
            # Use formatting logic
            if "portfolio" in query_type:
                answer = self._format_portfolio_table(serialized_data)
            elif "geographic" in query_type:
                answer = self._format_geographic_answer(serialized_data, question)
            elif "economic" in query_type:
                answer = self._format_economic_data(serialized_data)
            else:
                answer = self._format_asset_table(serialized_data)
            
            return {
                **state,
                "answer": answer,
                "formatted_data": serialized_data,
                "workflow_steps": steps
            }
            
        except Exception as e:
            error_messages = state.get("error_messages", [])
            error_messages.append(f"Response formatting error: {str(e)}")
            return {
                **state,
                "answer": f"Error formatting response: {str(e)}",
                "workflow_steps": steps,
                "error_messages": error_messages
            }
    
    async def answer_question(self, question: str) -> Dict[str, Any]:
        """Main entry point for answering questions using LangGraph workflow"""
        try:
            # Compile workflow if not already done
            if not hasattr(self, '_compiled_workflow'):
                self._compiled_workflow = self.workflow.compile()
            
            # Initialize state
            initial_state = AssetGraphState(
                question=question,
                intent=None,
                cypher_query=None,
                cypher_params=None,
                raw_data=None,
                answer="",
                formatted_data=None,
                workflow_steps=[],
                error_messages=[],
                query_type="",
                pattern_matched=False
            )
            
            # Execute workflow
            final_state = await self._compiled_workflow.ainvoke(initial_state)
            
            # Return in expected format
            intent = final_state.get("intent")
            
            # Ensure data field is properly set - prefer formatted_data, fallback to raw_data, ensure it's not None
            data = final_state.get("formatted_data") or final_state.get("raw_data") or []
            
            return {
                "answer": final_state.get("answer", "No answer generated"),
                "cypher": final_state.get("cypher_query", ""),
                "data": data,
                "question": question,
                "pattern_matched": final_state.get("pattern_matched", False),
                "query_type": final_state.get("query_type", "unknown"),
                "workflow_steps": final_state.get("workflow_steps", []),
                "intent_classification": {
                    "category": intent.category.value if intent and hasattr(intent.category, 'value') else (intent.category if intent else "unknown"),
                    "confidence": intent.confidence if intent else 0.0,
                    "reasoning": intent.reasoning if intent else "No intent classification"
                },
                "system_used": "langgraph",
                "geospatial_enabled": True
            }
            
        except Exception as e:
            return {
                "answer": f"Workflow execution failed: {str(e)}",
                "cypher": None,
                "data": [],
                "question": question,
                "pattern_matched": False,
                "error": str(e),
                "system_used": "langgraph",
                "workflow_steps": ["error"]
            }
    
    def generate_workflow_diagram(self, output_path: str = "docs/workflows/langgraph_workflow.png"):
        """Generate automatic workflow diagram"""
        try:
            if not hasattr(self, '_compiled_workflow'):
                self._compiled_workflow = self.workflow.compile()
            
            # Generate mermaid diagram
            self._compiled_workflow.get_graph().draw_mermaid_png(output_file_path=output_path)
            print(f"✅ LangGraph workflow diagram generated: {output_path}")
            
        except Exception as e:
            print(f"❌ Failed to generate workflow diagram: {e}")

    # Formatting methods from original implementation
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