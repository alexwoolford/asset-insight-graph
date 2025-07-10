from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import openai

from .config import Settings, get_driver

# Add state mapping for abbreviations and case insensitivity
STATE_MAPPINGS = {
    # Full names (case insensitive)
    "california": "California",
    "texas": "Texas", 
    "new york": "New York",
    "georgia": "Georgia",
    "illinois": "Illinois",
    "wisconsin": "Wisconsin",
    "missouri": "Missouri",
    # Abbreviations
    "ca": "California",
    "tx": "Texas",
    "ny": "New York", 
    "ga": "Georgia",
    "il": "Illinois",
    "wi": "Wisconsin",
    "mo": "Missouri",
    # Common typos
    "californa": "California",
    "califorina": "California",
    "texsa": "Texas",
    "new yourk": "New York",
}

def normalize_state_name(state_input: str) -> str:
    """Normalize state name to handle case sensitivity, abbreviations, and typos."""
    if not state_input:
        return state_input
    
    # Try exact match first (case insensitive)
    normalized = state_input.lower().strip()
    if normalized in STATE_MAPPINGS:
        return STATE_MAPPINGS[normalized]
    
    # Try fuzzy matching for common typos
    for typo, correct in STATE_MAPPINGS.items():
        if abs(len(typo) - len(normalized)) <= 2:  # Similar length
            # Simple character difference check
            diff_count = sum(1 for a, b in zip(typo, normalized) if a != b)
            if diff_count <= 2:  # Allow 2 character differences
                return correct
    
    # If no match found, return capitalized version
    return state_input.title()

# Query patterns using Neo4j native geospatial Point types
# NOTE: Order matters! More specific patterns should come first
GEOSPATIAL_RULES: List[tuple[re.Pattern[str], str]] = [
    # California specific (most specific geographic query)
    (
        re.compile(r"california assets|assets in california", re.I),
        """MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State {name: "California"})
           RETURN a.name AS asset_name, c.name AS city,
                  a.building_type AS building_type,
                  a.location.latitude AS latitude,
                  a.location.longitude AS longitude""",
    ),
    # Regional queries (more specific than city)
    (
        re.compile(
            r"assets in the (?P<region>west|east|northeast|southeast|midwest|southwest)",
            re.I,
        ),
        """MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State)-[:PART_OF]->(r:Region)
           WHERE toLower(r.name) = toLower($region)
           RETURN a.name AS asset_name, c.name + ', ' + s.name AS location,
                  a.building_type AS building_type""",
    ),
    # State queries (more specific than city)
    (
        re.compile(r"assets in (?P<state>.+?)(?:\s+state)?$", re.I),
        """MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State {name: $normalized_state})
           RETURN a.name AS asset_name, c.name AS city, 
                  a.building_type AS building_type""",
    ),
    # Platform queries
    (
        re.compile(r"(?P<platform>real estate|infrastructure|credit) assets", re.I),
        """MATCH (a:Asset)-[:BELONGS_TO]->(p:Platform)
           WHERE toLower(p.name) CONTAINS toLower($platform)
           RETURN a.name AS asset_name, p.name AS platform, 
                  a.building_type AS building_type""",
    ),
    # Investment type queries
    (
        re.compile(
            r"(?P<investment_type>direct real estate|infrastructure investment|real estate credit)",
            re.I,
        ),
        """MATCH (a:Asset)-[:HAS_INVESTMENT_TYPE]->(it:InvestmentType)
           WHERE toLower(it.name) = toLower($investment_type)
           RETURN a.name AS asset_name, it.name AS investment_type""",
    ),
    # Combined building type and state queries (more specific)
    (
        re.compile(
            r"(?P<building_type>commercial|residential|infrastructure|mixed use)\s+(?:buildings?|properties?)\s+in\s+(?P<state>.+?)(?:\s+state)?$",
            re.I,
        ),
        """MATCH (a:Asset)-[:HAS_TYPE]->(bt:BuildingType), 
                 (a)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State)
           WHERE toLower(bt.name) CONTAINS toLower($building_type)
             AND toLower(s.name) = toLower($normalized_state)
           RETURN a.name AS asset_name, c.name AS city, 
                  bt.name AS building_type, s.name AS state""",
    ),
    # Building type analysis (general)
    (
        re.compile(
            r"(?P<building_type>commercial|residential|infrastructure|mixed use) buildings?",
            re.I,
        ),
        """MATCH (a:Asset)-[:HAS_TYPE]->(bt:BuildingType)
           WHERE toLower(bt.name) CONTAINS toLower($building_type)
           RETURN a.name AS asset_name, bt.name AS building_type""",
    ),
    # Portfolio analysis
    (
        re.compile(r"portfolio distribution|asset distribution", re.I),
        """MATCH (a:Asset)-[:BELONGS_TO]->(p:Platform),
                 (a)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State)-[:PART_OF]->(r:Region)
           RETURN p.name AS platform, r.name AS region, 
                  count(a) AS asset_count
           ORDER BY platform, asset_count DESC""",
    ),
    # Geospatial queries using native Point types
    (
        re.compile(
            r"assets within (?P<distance>\d+)\s*(?P<unit>km|miles?) of (?P<reference>.+)",
            re.I,
        ),
        """MATCH (ref:Asset)-[:LOCATED_IN]->(refCity:City)
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
           ORDER BY distance_meters""",
    ),
    # Geographic clustering using native distance functions
    (
        re.compile(r"nearby assets|assets near|geographic clusters?", re.I),
        """MATCH (a1:Asset), (a2:Asset)
           WHERE a1 <> a2 AND a1.location IS NOT NULL AND a2.location IS NOT NULL
           WITH a1, a2, point.distance(a1.location, a2.location) AS distance_meters
           WHERE distance_meters < 50000
           RETURN a1.name AS asset1, a2.name AS asset2,
                  round(distance_meters/1000, 1) AS distance_km
           ORDER BY distance_meters LIMIT 10""",
    ),
    # Assets within a bounding box (geospatial envelope)
    (
        re.compile(
            r"assets in (?P<area>los angeles|la|bay area|san francisco|chicago|new york) area",
            re.I,
        ),
        """WITH CASE toLower($area)
             WHEN 'los angeles' THEN {minLat: 33.7, maxLat: 34.3, minLon: -118.7, maxLon: -118.0}
             WHEN 'la' THEN {minLat: 33.7, maxLat: 34.3, minLon: -118.7, maxLon: -118.0}
             WHEN 'bay area' THEN {minLat: 37.2, maxLat: 37.9, minLon: -122.6, maxLon: -121.5}
             WHEN 'san francisco' THEN {minLat: 37.2, maxLat: 37.9, minLon: -122.6, maxLon: -121.5}
             WHEN 'chicago' THEN {minLat: 41.6, maxLat: 42.0, minLon: -87.9, maxLon: -87.5}
             WHEN 'new york' THEN {minLat: 40.5, maxLat: 40.9, minLon: -74.3, maxLon: -73.7}
             ELSE {minLat: 0, maxLat: 0, minLon: 0, maxLon: 0}
           END AS area_bounds
           MATCH (a:Asset)
           WHERE a.location IS NOT NULL 
             AND area_bounds.minLat <= a.location.latitude <= area_bounds.maxLat
             AND area_bounds.minLon <= a.location.longitude <= area_bounds.maxLon
           RETURN a.name AS asset_name, 
                  a.location.latitude AS latitude,
                  a.location.longitude AS longitude,
                  a.building_type AS building_type""",
    ),
    # Count queries
    (
        re.compile(r"how many assets|asset count|total assets", re.I),
        "MATCH (a:Asset) RETURN count(a) AS total_assets",
    ),
    (
        re.compile(r"how many (?P<node_type>cities|states|regions|platforms)", re.I),
        """MATCH (c:City), (s:State), (r:Region), (p:Platform)
           RETURN count(DISTINCT c) AS cities, count(DISTINCT s) AS states, 
                  count(DISTINCT r) AS regions, count(DISTINCT p) AS platforms""",
    ),
    # Vector similarity search patterns
    (
        re.compile(r"similar to|like|comparable to|properties matching|assets like", re.I),
        "VECTOR_SEARCH",  # Special marker for vector search
    ),
    (
        re.compile(r"(?:find|show|search|looking for).*(?:with|having|featuring).*(?:luxury|premium|high-quality|modern|sustainable|ESG|green|tech|innovation)", re.I),
        "VECTOR_SEARCH",
    ),
    (
        re.compile(r"(?:sustainable|ESG|environmental|green|renewable|clean energy|carbon|climate)", re.I),
        "VECTOR_SEARCH",
    ),
    (
        re.compile(r"(?:luxury|premium|high-end|institutional|quality|amenities|modern)", re.I),
        "VECTOR_SEARCH",
    ),
    
    # FRED-enhanced business intelligence queries (Fixed for actual data structure)
    (
        re.compile(r"(?:current|latest)\s+(?:interest\s+)?rates?", re.I),
        """MATCH (mt:MetricType {category: "Interest Rate"})-[:TAIL]->(latest:MetricValue)
           RETURN mt.name AS rate_type, latest.value AS current_rate, latest.date AS as_of_date
           ORDER BY mt.name""",
    ),
    (
        re.compile(r"unemployment\s+(?:in|by)\s+(?:states?|where.*assets?)", re.I),
        """MATCH (a:Asset)-[:LOCATED_IN]->(:City)-[:PART_OF]->(s:State)
           MATCH (s)-[:HAS_METRIC]->(mt:MetricType)
           WHERE mt.category = "Labor" AND mt.name CONTAINS "Unemployment"
           MATCH (mt)-[:TAIL]->(latest:MetricValue)
           RETURN s.name AS state, 
                  latest.value AS current_unemployment_rate,
                  count(DISTINCT a) AS assets_in_state,
                  latest.date AS latest_data
           ORDER BY current_unemployment_rate ASC""",
    ),
    (
        re.compile(r"economic\s+trends?\s+(?:for|in)\s+(?P<state>.+)", re.I),
        """MATCH (s:State {name: $normalized_state})-[:HAS_METRIC]->(mt:MetricType)-[:HAS_VALUE]->(mv:MetricValue)
           WHERE mv.date >= date() - duration({months: 6})
           RETURN mt.name AS metric_name, 
                  mt.category AS category,
                  avg(mv.value) AS avg_value,
                  max(mv.date) AS latest_date,
                  count(mv) AS data_points
           ORDER BY mt.category, mt.name""",
    ),
    (
        re.compile(r"(?:interest\s+rate|rate)\s+(?:trends?|changes?|analysis)", re.I),
        """MATCH (mt:MetricType {category: "Interest Rate"})-[:HEAD]->(first:MetricValue)
           MATCH (mt)-[:TAIL]->(last:MetricValue)
           RETURN mt.name AS rate_type, 
                  first.value AS start_value,
                  last.value AS end_value,
                  last.value - first.value AS change,
                  first.date AS start_date,
                  last.date AS end_date
           ORDER BY ABS(change) DESC""",
    ),
    (
        re.compile(r"assets?\s+(?:by|grouped?\s+by)\s+economic\s+(?:environment|context)", re.I),
        """MATCH (a:Asset)-[:LOCATED_IN]->(:City)-[:PART_OF]->(s:State)-[:HAS_METRIC]->(mt:MetricType)
           WHERE mt.category = "Labor"
           MATCH (mt)-[:HAS_VALUE]->(mv:MetricValue)
           WHERE mv.date >= date() - duration({months: 1})
           WITH a, s, avg(mv.value) AS recent_unemployment
           MATCH (a)-[:BELONGS_TO]->(p:Platform)
           RETURN s.name AS state,
                  p.name AS platform,
                  recent_unemployment,
                  count(a) AS asset_count
           ORDER BY recent_unemployment ASC, asset_count DESC""",
    ),
    (
        re.compile(r"(?:national\s+)?housing\s+(?:market|metrics?|indicators?)", re.I),
        """MATCH (c:Country {name: "United States"})-[:HAS_METRIC]->(mt:MetricType)
           WHERE mt.category = "Housing"
           MATCH (mt)-[:HAS_VALUE]->(mv:MetricValue)
           WHERE mv.date >= date() - duration({months: 6})
           WITH mt.name AS metric_name,
                avg(mv.value) AS avg_value,
                max(mv.date) AS latest_date
           MATCH (a:Asset)-[:BELONGS_TO]->(p:Platform {name: "Real Estate"})
           RETURN metric_name, avg_value, latest_date, 
                  count(a) AS real_estate_assets
           ORDER BY metric_name""",
    ),
    (
                 re.compile(r"(?:portfolio\s+)?risk\s*(?:analysis|volatility|economic)", re.I),
         """MATCH (s:State)-[:HAS_METRIC]->(mt:MetricType)-[:HAS_VALUE]->(mv:MetricValue)
            WHERE mv.date >= date() - duration({months: 12})
            WITH s.name AS state, 
                 mt.category AS category,
                 max(mv.value) - min(mv.value) AS volatility
            MATCH (a:Asset)-[:LOCATED_IN]->(:City)-[:PART_OF]->(s2:State {name: state})
            MATCH (a)-[:BELONGS_TO]->(p:Platform)
            RETURN state, p.name AS platform, category,
                   avg(volatility) AS avg_economic_volatility,
                   count(a) AS assets_at_risk
            ORDER BY avg_economic_volatility DESC""",
    ),
    
    # City queries (most general, comes last)
    (
        re.compile(r"assets in (?P<city>.+)", re.I),
        """MATCH (a:Asset)-[:LOCATED_IN]->(c:City {name: $city})
           RETURN a.name AS asset_name, a.building_type AS building_type, 
                  a.investment_type AS investment_type""",
    ),
]

# Add hybrid query patterns and implementation
HYBRID_QUERY_PATTERNS = [
    # Geographic + Semantic patterns (flexible state matching)
    (
        re.compile(r"(?:properties|assets)\s+in\s+(?P<state>[^,\s]+(?:\s+[^,\s]+)?)\s+that\s+are\s+(?P<semantic>ESG|sustainable|green|renewable|luxury|premium|modern|tech|innovation)", re.I),
        "HYBRID_GEOGRAPHIC_SEMANTIC"
    ),
    (
        re.compile(r"(?P<semantic>ESG|sustainable|green|renewable|luxury|premium|modern|tech|innovation)\s+(?:properties|assets)\s+in\s+(?P<state>[^,\s]+(?:\s+[^,\s]+)?)", re.I),
        "HYBRID_SEMANTIC_GEOGRAPHIC"
    ),
    (
        re.compile(r"show\s+me\s+(?P<semantic>ESG|sustainable|green|renewable|luxury|premium|modern|tech|innovation)\s+(?:properties|assets)\s+in\s+(?P<state>[^,\s]+(?:\s+[^,\s]+)?)", re.I),
        "HYBRID_SEMANTIC_GEOGRAPHIC"
    ),
]

async def perform_vector_search(question: str, limit: int = 5) -> Dict[str, Any]:
    """Perform vector similarity search for semantic queries."""
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return {
            "answer": "Vector search requires OpenAI API key to be configured.",
            "cypher": None,
            "data": [],
            "question": question,
            "pattern_matched": False,
            "vector_search": False,
        }
    
    try:
        # Initialize OpenAI client
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
        
        # Execute vector search
        driver = get_driver()
        settings = Settings()
        async with driver.session(database=settings.neo4j_db) as session:
            result = await session.run(vector_cypher, {
                "query_embedding": query_embedding,
                "limit": limit
            })
            data = await result.data()
        
        # Generate summary
        if data:
            top_matches = [f"{item['asset_name']} (similarity: {item['similarity_score']:.3f})" 
                          for item in data[:3]]
            summary = f"Found {len(data)} semantically similar assets: {', '.join(top_matches)}"
        else:
            summary = "No semantically similar assets found."
        
        return {
            "answer": summary,
            "cypher": vector_cypher,
            "data": data,
            "question": question,
            "pattern_matched": True,
            "vector_search": True,
            "search_type": "semantic_similarity"
        }
        
    except Exception as e:
        return {
            "answer": f"Vector search error: {str(e)}",
            "cypher": None,
            "data": [],
            "question": question,
            "pattern_matched": False,
            "vector_search": False,
        }

async def perform_hybrid_search(question: str, state: str, semantic_term: str, limit: int = 5) -> Dict[str, Any]:
    """Perform hybrid search: geographic filter + semantic ranking."""
    
    # Normalize the state name
    normalized_state = normalize_state_name(state)
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return {
            "answer": "Hybrid search requires OpenAI API key to be configured.",
            "cypher": None,
            "data": [],
            "question": question,
            "pattern_matched": False,
            "hybrid_search": False,
        }
    
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=openai_key)
        
        # Generate embedding for the semantic term
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=semantic_term.replace("\n", " "),
            encoding_format="float"
        )
        query_embedding = response.data[0].embedding
        
        # Hybrid search: First filter by state, then rank by semantic similarity
        hybrid_cypher = """
        // Step 1: Get all assets in the specified state with embeddings
        MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State {name: $state})
        WHERE a.description_embedding IS NOT NULL
        
        // Step 2: Calculate cosine similarity manually
        WITH a, c, s,
             reduce(dot = 0.0, i IN range(0, size(a.description_embedding)-1) | 
                dot + a.description_embedding[i] * $query_embedding[i]) AS dot_product,
             sqrt(reduce(norm_a = 0.0, x IN a.description_embedding | norm_a + x * x)) AS norm_a,
             sqrt(reduce(norm_q = 0.0, x IN $query_embedding | norm_q + x * x)) AS norm_q
        
        WITH a, c, s, dot_product / (norm_a * norm_q) AS similarity_score
        
        // Step 3: Return results ranked by semantic relevance
        RETURN a.name AS asset_name,
               c.name AS city,
               s.name AS state,
               a.platform AS platform,
               a.building_type AS building_type,

               similarity_score,
               a.property_description AS description
        ORDER BY similarity_score DESC
        LIMIT $limit
        """
        
        # Execute hybrid search
        driver = get_driver()
        settings = Settings()
        async with driver.session(database=settings.neo4j_db) as session:
            result = await session.run(hybrid_cypher, {
                "state": normalized_state,
                "query_embedding": query_embedding,
                "limit": limit
            })
            data = await result.data()
        
        # Generate summary
        if data:
            asset_summaries = []
            for item in data:
                score = item['similarity_score']
                asset_summaries.append(f"{item['asset_name']} (similarity: {score:.3f})")
            
            summary = f"Found {len(data)} properties in {normalized_state} ranked by {semantic_term} relevance: " + ", ".join(asset_summaries)
        else:
            summary = f"No properties found in {normalized_state} with vector embeddings for semantic ranking."
        
        return {
            "answer": summary,
            "cypher": hybrid_cypher,
            "data": data,
            "question": question,
            "pattern_matched": True,
            "hybrid_search": True,
            "search_type": "Hybrid (Geographic Filter + Semantic Ranking)",
            "filter_criteria": f"State: {normalized_state} (normalized from '{state}')",
            "semantic_criteria": f"Similarity to: {semantic_term}"
        }
        
    except Exception as e:
        return {
            "answer": f"Error performing hybrid search: {str(e)}",
            "cypher": None,
            "data": [],
            "question": question,
            "pattern_matched": False,
            "hybrid_search": False,
            "error": str(e)
        }


async def answer_geospatial(question: str) -> Dict[str, Any]:
    """Return answer dictionary using geospatial patterns and vector search."""

    # First check for hybrid query patterns
    for pattern, search_type in HYBRID_QUERY_PATTERNS:
        match = pattern.search(question)
        if match:
            params = match.groupdict()
            state = params.get('state')
            semantic = params.get('semantic')
            
            if state and semantic:
                return await perform_hybrid_search(question, state, semantic)
    
    # Use pattern matching for all queries
    for pattern, cypher in GEOSPATIAL_RULES:
        match = pattern.search(question)
        if match:
            params = match.groupdict()
            
            # Normalize state parameter if present
            if 'state' in params and params['state']:
                params['normalized_state'] = normalize_state_name(params['state'])
            
            # Check if this is a vector search pattern
            if cypher == "VECTOR_SEARCH":
                return await perform_vector_search(question)
            
            # Regular graph query
            driver = get_driver()
            settings = Settings()
            async with driver.session(database=settings.neo4j_db) as session:
                result = await session.run(cypher, params)
                data = await result.data()

            summary = generate_geospatial_summary(question, data, cypher)

            return {
                "answer": summary,
                "cypher": cypher,
                "data": data,
                "question": question,
                "pattern_matched": True,
                "geospatial_enabled": True,
            }

    # Fallback: suggest what kinds of questions can be answered
    suggestions = [
        "Assets in California (or CA)",
        "Real estate assets", 
        "Properties in Texas that are ESG friendly",
        "Sustainable assets in California",
        "Luxury properties in New York",
        "Assets within 50km of Los Angeles",
        "How many assets",
    ]

    return {
        "answer": f"I couldn't understand that question. Try asking about: {', '.join(suggestions[:6])}",
        "cypher": None,
        "data": [],
        "question": question,
        "pattern_matched": False,
        "geospatial_enabled": False,
        "suggestions": suggestions,
    }


def generate_geospatial_summary(question: str, data: List[Dict], cypher: str) -> str:
    """Generate a natural language summary of geospatial query results."""
    if not data:
        return "No results found for your query."

    result_count = len(data)

    # IMPORTANT: Check specific patterns before generic ones
    
    # Portfolio distribution (specific - check this BEFORE generic asset_count)
    if "platform" in str(data[0]) and "region" in str(data[0]) and "asset_count" in str(data[0]):
        platform_summary = {}
        for item in data:
            platform = item.get("platform", "Unknown")
            if platform not in platform_summary:
                platform_summary[platform] = 0
            platform_summary[platform] += item.get("asset_count", 1)

        distribution = ", ".join(
            [f"{p}: {c} assets" for p, c in platform_summary.items()]
        )
        return f"Portfolio distribution: {distribution}"

    # Distance analysis
    if "distance_km" in str(data[0]):
        if "reference_asset" in str(data[0]):
            # Distance from reference query
            ref = data[0].get("reference_asset", "reference point")
            examples = ", ".join(
                [
                    f"{item['asset_name']} ({item['distance_km']}km away)"
                    for item in data[:3]
                ]
            )
            return f"Found {result_count} assets near {ref}: {examples}"
        else:
            # Clustering query
            pairs = [
                (item["asset1"], item["asset2"], item["distance_km"])
                for item in data[:3]
            ]
            examples = ", ".join(
                [f"{a1} and {a2} ({d}km apart)" for a1, a2, d in pairs]
            )
            return f"Found {result_count} asset pairs within proximity. Examples: {examples}"

    # Simple count queries (generic - check this AFTER specific patterns)
    if "total_assets" in str(data[0]):
        return f"Found {data[0].get('total_assets', result_count)} assets total."

    # Default summary for asset lists
    asset_names = [item.get("asset_name", "Unknown") for item in data[:5]]
    if result_count <= 5:
        return f"Found {result_count} assets: {', '.join(asset_names)}"
    else:
        return f"Found {result_count} assets including: {', '.join(asset_names)} and {result_count - 5} more"
