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
            "city_filter": """
                MATCH (a:Asset) 
                WHERE a.city = $city_name
                RETURN a.name, a.city, a.state, a.building_type, a.platform
                ORDER BY a.name
            """,
            "region_filter": """
                MATCH (a:Asset)-[:LOCATED_IN]->(:City)-[:PART_OF]->(:State)-[:PART_OF]->(r:Region {{name: $region_name}})
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
                MATCH (mt:MetricType {{name: $metric_name}})-[:TAIL]->(mv:MetricValue)
                RETURN mt.name AS metric, mv.value AS current_value, mv.date AS current_date
            """,
            "trend_analysis": """
                MATCH (mt:MetricType {{name: $metric_name}})-[:HEAD]->(first:MetricValue)
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
        
        # Extract location mentions
        states = ["california", "texas", "illinois", "missouri", "wisconsin"]
        cities = ["los angeles", "houston", "austin", "chicago", "milwaukee", "appleton", "west hollywood"]
        regions = ["west", "southwest", "midwest", "northeast", "southeast"]
        
        for state in states:
            if state in question_lower:
                params["state_name"] = state.title()
                return self.geographic_templates["state_filter"], params
        
        for city in cities:
            if city in question_lower:
                params["city_name"] = city.title()
                return self.geographic_templates["city_filter"], params
                
        for region in regions:
            if region in question_lower:
                params["region_name"] = region.title()
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
        
        # Check for semantic keywords FIRST (highest priority)
        semantic_keywords = ["sustainable", "ESG", "renewable", "green", "luxury", "premium", "high-end", "environmental", "carbon", "solar", "energy", "eco-friendly", "similar to", "like", "comparable"]
        
        if any(keyword.lower() in question_lower for keyword in semantic_keywords):
            return IntentClassification(
                category=QueryCategory.SEMANTIC_SEARCH,
                confidence=0.95,
                reasoning=f"Contains semantic keywords requiring vector search"
            )
        
        # Portfolio analysis keywords (second priority)
        portfolio_keywords = ["portfolio", "distribution", "how many", "count", "platform", "breakdown"]
        if any(keyword in question_lower for keyword in portfolio_keywords):
            return IntentClassification(
                category=QueryCategory.PORTFOLIO_ANALYSIS,
                confidence=0.95,
                reasoning="Question asks about portfolio composition or asset counts"
            )
        
        # Geographic keywords (third priority - after semantic check)
        geographic_keywords = ["california", "texas", "los angeles", "houston", "austin", "properties in", "assets in", "located in"]
        if any(keyword in question_lower for keyword in geographic_keywords):
            # Check if it's ONLY geographic without semantic terms
            return IntentClassification(
                category=QueryCategory.GEOGRAPHIC_ASSETS,
                confidence=0.90,
                reasoning="Question refers to specific geographic locations"
            )
        
        # Economic keywords  
        economic_keywords = ["unemployment", "interest rate", "mortgage", "federal funds", "economic", "rate"]
        if any(keyword in question_lower for keyword in economic_keywords):
            return IntentClassification(
                category=QueryCategory.ECONOMIC_DATA,
                confidence=0.90,
                reasoning="Question asks about economic indicators"
            )
        
        # Trend keywords
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
                return f"Found {len(data)} semantically similar assets: " + ", ".join(results[:3])
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
            
            formatted_answer = self._format_asset_table(data)
            
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
                "system_used": "graphrag",
                "geospatial_enabled": True
            }
        except Exception as e:
            return {
                "answer": f"Geographic query failed: {str(e)}",
                "cypher": None,
                "data": [],
                "question": question,
                "pattern_matched": False,
                "error": str(e)
            }
    
    async def _handle_semantic_query(self, question: str, intent: IntentClassification) -> Dict[str, Any]:
        """Handle semantic search queries using vector similarity."""
        try:
            # Use vector search for semantic queries
            vector_result = await self._vector_search_tool(question)
            
            # Also try template-based semantic search as backup
            cypher, params = self.cypher_templates.generate_semantic_query(question)
            backup_data = await self.execute_cypher_query(cypher, params)
            
            # Prefer vector search results
            if "Found" in vector_result and "semantically similar" in vector_result:
                answer = vector_result
                data = backup_data  # Include backup data for context
                cypher_query = cypher.strip()
            elif backup_data:
                answer = self._format_asset_table(backup_data)
                data = backup_data
                cypher_query = cypher.strip()
            else:
                answer = "No assets found matching your semantic search criteria."
                data = []
                cypher_query = cypher.strip()
            
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
        
        # Extract columns
        rows = []
        for item in data:
            if isinstance(item, dict):
                # Handle different field name patterns
                name = item.get('name', item.get('a.name', 'Unknown Asset'))
                city = item.get('city', item.get('a.city', ''))
                state = item.get('state', item.get('a.state', ''))
                building_type = item.get('building_type', item.get('a.building_type', ''))
                
                location = ""
                if city and state:
                    location = f"{city}, {state}"
                elif city:
                    location = city
                elif state:
                    location = state
                
                rows.append((name, location, building_type))
        
        if not rows:
            return "No assets found."
        
        # Create table with proper columns
        lines = ["Asset Details:"]
        lines.append("=" * 75)
        lines.append(f"{'Asset Name':<30} {'Location':<20} {'Type':<20}")
        lines.append("-" * 75)
        
        for name, location, building_type in rows:
            lines.append(f"{name[:29]:<30} {location[:19]:<20} {building_type[:19]:<20}")
        
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


# Factory function for easy instantiation
async def create_graphrag() -> GraphRAG:
    """Create a GraphRAG instance with proper initialization."""
    return GraphRAG()
