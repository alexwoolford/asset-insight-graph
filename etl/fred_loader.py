"""
FRED Data Loader with Timeseries Chain Structure
Loads Federal Reserve Economic Data with proper timeseries chains:
- MetricType: Describes the metric
- MetricValue: Individual data points
- HEAD/TAIL: Links to first/last data points
- NEXT: Chain connecting consecutive data points chronologically
"""

import asyncio
import aiohttp
import logging
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import time

# Add the project root to the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file  
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually load .env file
    import os
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

from api.config import Settings, get_driver

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FREDClient:
    """FRED API client with rate limiting and error handling."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session = None
        self.request_count = 0
        self.start_time = time.time()
        self.rate_limit = 120  # 120 requests per minute
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def _rate_limit_check(self):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if elapsed < 60:  # Within the first minute
            if self.request_count >= self.rate_limit:
                sleep_time = 60 - elapsed
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                self.start_time = time.time()
                self.request_count = 0
        else:
            # Reset counter after a minute
            self.start_time = current_time
            self.request_count = 0
            
    async def get_series_data(self, series_id: str, start_date: str, end_date: str) -> Optional[Dict]:
        """Fetch data for a specific FRED series."""
        await self._rate_limit_check()
        
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'start_date': start_date,
            'end_date': end_date
        }
        
        url = f"{self.base_url}/series/observations"
        
        try:
            async with self.session.get(url, params=params) as response:
                self.request_count += 1
                
                if response.status == 400:
                    logger.warning(f"Series {series_id} not found or invalid")
                    return None
                elif response.status != 200:
                    logger.error(f"Error fetching {series_id}: {response.status}")
                    return None
                    
                data = await response.json()
                return data
                
        except Exception as e:
            logger.error(f"Exception fetching {series_id}: {e}")
            return None


class FREDLoader:
    """Loads FRED data into Neo4j with timeseries chain structure."""
    
    def __init__(self):
        self.fred_api_key = os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            raise ValueError("FRED_API_KEY environment variable is required")
        
        self.driver = get_driver()
        self.settings = Settings()
        
        # Define metrics to load
        self.metrics_config = {
            # National metrics (attached to Country)
            "national": {
                "Federal Funds Rate": {"series_id": "FEDFUNDS", "units": "Percent", "category": "Interest Rate"},
                "10-Year Treasury Rate": {"series_id": "GS10", "units": "Percent", "category": "Interest Rate"},
                "30-Year Mortgage Rate": {"series_id": "MORTGAGE30US", "units": "Percent", "category": "Interest Rate"},
                "Aaa Corporate Bond Rate": {"series_id": "AAA", "units": "Percent", "category": "Interest Rate"},
                "Housing Starts": {"series_id": "HOUST", "units": "Thousands", "category": "Housing"},
                "Building Permits": {"series_id": "PERMIT", "units": "Thousands", "category": "Housing"},
                "GDP": {"series_id": "GDP", "units": "Billions", "category": "Economic"},
                "Consumer Price Index": {"series_id": "CPIAUCSL", "units": "Index", "category": "Economic"},
            },
            # State-level metrics
            "states": {
                "California": {
                    "Unemployment Rate": {"series_id": "CAURN", "units": "Percent", "category": "Labor"},
                    "Total Population": {"series_id": "CAPOP", "units": "Thousands", "category": "Demographics"},
                    "All-Transactions House Price Index": {"series_id": "CASP", "units": "Index", "category": "Housing"},
                },
                "Texas": {
                    "Unemployment Rate": {"series_id": "TXURN", "units": "Percent", "category": "Labor"},
                    "Total Population": {"series_id": "TXPOP", "units": "Thousands", "category": "Demographics"},
                    "All-Transactions House Price Index": {"series_id": "TXSP", "units": "Index", "category": "Housing"},
                },
                "New York": {
                    "Unemployment Rate": {"series_id": "NYURN", "units": "Percent", "category": "Labor"},
                    "Total Population": {"series_id": "NYPOP", "units": "Thousands", "category": "Demographics"},
                    "All-Transactions House Price Index": {"series_id": "NYSP", "units": "Index", "category": "Housing"},
                },
                "Illinois": {
                    "Unemployment Rate": {"series_id": "ILURN", "units": "Percent", "category": "Labor"},
                    "Total Population": {"series_id": "ILPOP", "units": "Thousands", "category": "Demographics"},
                    "All-Transactions House Price Index": {"series_id": "ILSP", "units": "Index", "category": "Housing"},
                },
                "Georgia": {
                    "Unemployment Rate": {"series_id": "GAURN", "units": "Percent", "category": "Labor"},
                    "Total Population": {"series_id": "GAPOP", "units": "Thousands", "category": "Demographics"},
                }
            }
        }
        
    async def create_schema(self):
        """Create schema for the timeseries chain structure."""
        print("🏗️ Creating schema for timeseries chain structure...")
        
        async with self.driver.session(database=self.settings.neo4j_db) as session:
            schema_queries = [
                # Country constraint
                "CREATE CONSTRAINT country_name IF NOT EXISTS FOR (c:Country) REQUIRE c.name IS UNIQUE",
                
                # MetricType constraints and indexes
                "CREATE CONSTRAINT metric_type_id IF NOT EXISTS FOR (mt:MetricType) REQUIRE mt.id IS UNIQUE",
                "CREATE INDEX metric_type_name IF NOT EXISTS FOR (mt:MetricType) ON (mt.name)",
                "CREATE INDEX metric_type_category IF NOT EXISTS FOR (mt:MetricType) ON (mt.category)",
                "CREATE INDEX metric_type_level IF NOT EXISTS FOR (mt:MetricType) ON (mt.level)",
                
                # MetricValue constraints and indexes
                "CREATE CONSTRAINT metric_value_id IF NOT EXISTS FOR (mv:MetricValue) REQUIRE mv.id IS UNIQUE",
                "CREATE INDEX metric_value_date IF NOT EXISTS FOR (mv:MetricValue) ON (mv.date)",
                "CREATE INDEX metric_value_metric_type IF NOT EXISTS FOR (mv:MetricValue) ON (mv.metric_type_id)",
                "CREATE INDEX metric_value_series IF NOT EXISTS FOR (mv:MetricValue) ON (mv.series_id)",
            ]
            
            for query in schema_queries:
                try:
                    await session.run(query)
                    print(f"   ✅ {query.split(' ')[1]} {query.split(' ')[2]}")
                except Exception as e:
                    print(f"   ⚠️  Schema: {e}")
                    
    async def create_geographic_hierarchy(self):
        """Create Country and State nodes with hierarchy."""
        print("🌍 Creating geographic hierarchy...")
        
        async with self.driver.session(database=self.settings.neo4j_db) as session:
            # Create United States
            await session.run("""
                MERGE (c:Country {name: "United States"})
                SET c.iso_code = "US",
                    c.created_at = datetime()
            """)
            
            # Create states and link to country
            states = ["California", "Texas", "New York", "Illinois", "Georgia"]
            for state in states:
                await session.run("""
                    MERGE (s:State {name: $state})
                    SET s.created_at = datetime()
                    WITH s
                    MATCH (c:Country {name: "United States"})
                    MERGE (s)-[:PART_OF]->(c)
                """, state=state)
            
            print(f"   ✅ Created United States with {len(states)} states")
            
    async def load_metric_timeseries(self, metric_type_id: str, series_id: str, series_data: List[Dict]):
        """Load a timeseries with proper chain structure."""
        if not series_data:
            return 0
            
        # Sort data by date to ensure proper chronological order
        sorted_data = sorted(series_data, key=lambda x: x['date'])
        
        async with self.driver.session(database=self.settings.neo4j_db) as session:
            # Create all MetricValue nodes
            metric_values = []
            for i, observation in enumerate(sorted_data):
                if observation['value'] == '.':  # Skip missing values
                    continue
                    
                metric_value_id = f"{metric_type_id}_{observation['date']}"
                metric_values.append({
                    'id': metric_value_id,
                    'date': observation['date'],
                    'value': float(observation['value']),
                    'series_id': series_id,
                    'metric_type_id': metric_type_id
                })
            
            if not metric_values:
                return 0
            
            # Batch create MetricValue nodes
            await session.run("""
                UNWIND $values as value
                MERGE (mv:MetricValue {id: value.id})
                SET mv.date = date(value.date),
                    mv.value = toFloat(value.value),
                    mv.series_id = value.series_id,
                    mv.metric_type_id = value.metric_type_id,
                    mv.updated_at = datetime()
            """, values=metric_values)
            
            # Create the chain: connect consecutive MetricValues with NEXT
            for i in range(len(metric_values) - 1):
                current_id = metric_values[i]['id']
                next_id = metric_values[i + 1]['id']
                
                await session.run("""
                    MATCH (current:MetricValue {id: $current_id})
                    MATCH (next:MetricValue {id: $next_id})
                    MERGE (current)-[:NEXT]->(next)
                """, current_id=current_id, next_id=next_id)
            
            # Link MetricType to HEAD and TAIL
            head_id = metric_values[0]['id']
            tail_id = metric_values[-1]['id']
            
            await session.run("""
                MATCH (mt:MetricType {id: $metric_type_id})
                MATCH (head:MetricValue {id: $head_id})
                MATCH (tail:MetricValue {id: $tail_id})
                MERGE (mt)-[:HEAD]->(head)
                MERGE (mt)-[:TAIL]->(tail)
            """, metric_type_id=metric_type_id, head_id=head_id, tail_id=tail_id)
            
            # Note: MetricType only connects to HEAD and TAIL, not individual values
            # This maintains clean timeseries chain structure without dense connections
            
            return len(metric_values)
            
    async def load_fred_data(self):
        """Load FRED data with timeseries chain structure."""
        print("📊 Loading FRED data with timeseries chains...")
        
        # Calculate date range (last 24 months)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # ~24 months
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        print(f"   📅 Date range: {start_date_str} to {end_date_str}")
        
        total_metric_types = 0
        total_data_points = 0
        
        async with FREDClient(self.fred_api_key) as client:
            # Load national metrics
            print("   🇺🇸 Loading national metrics...")
            for metric_name, config in self.metrics_config["national"].items():
                series_id = config["series_id"]
                
                # Create MetricType
                metric_type_id = f"US_{series_id}"
                async with self.driver.session(database=self.settings.neo4j_db) as session:
                    await session.run("""
                        MERGE (mt:MetricType {id: $id})
                        SET mt.name = $name,
                            mt.category = $category,
                            mt.level = "National",
                            mt.units = $units,
                            mt.series_id = $series_id,
                            mt.created_at = datetime()
                        WITH mt
                        MATCH (c:Country {name: "United States"})
                        MERGE (c)-[:HAS_METRIC]->(mt)
                    """, id=metric_type_id, name=metric_name, category=config["category"], 
                         units=config["units"], series_id=series_id)
                
                # Load timeseries data
                data = await client.get_series_data(series_id, start_date_str, end_date_str)
                if data and 'observations' in data:
                    count = await self.load_metric_timeseries(metric_type_id, series_id, data['observations'])
                    total_data_points += count
                    total_metric_types += 1
                    print(f"     ✅ {metric_name}: {count} data points")
                else:
                    print(f"     ❌ {metric_name}: No data")
            
            # Load state-level metrics
            print("   🏛️ Loading state-level metrics...")
            for state_name, metrics in self.metrics_config["states"].items():
                print(f"     📍 {state_name}:")
                for metric_name, config in metrics.items():
                    series_id = config["series_id"]
                    
                    # Create MetricType
                    metric_type_id = f"{state_name}_{series_id}"
                    async with self.driver.session(database=self.settings.neo4j_db) as session:
                        await session.run("""
                            MERGE (mt:MetricType {id: $id})
                            SET mt.name = $full_name,
                                mt.category = $category,
                                mt.level = "State",
                                mt.units = $units,
                                mt.series_id = $series_id,
                                mt.state = $state,
                                mt.created_at = datetime()
                            WITH mt
                            MATCH (s:State {name: $state})
                            MERGE (s)-[:HAS_METRIC]->(mt)
                        """, id=metric_type_id, full_name=f"{state_name} {metric_name}", 
                             category=config["category"], units=config["units"], 
                             series_id=series_id, state=state_name)
                    
                    # Load timeseries data
                    data = await client.get_series_data(series_id, start_date_str, end_date_str)
                    if data and 'observations' in data:
                        count = await self.load_metric_timeseries(metric_type_id, series_id, data['observations'])
                        total_data_points += count
                        total_metric_types += 1
                        print(f"       ✅ {metric_name}: {count} data points")
                    else:
                        print(f"       ❌ {metric_name}: No data")
        
        print(f"\n📈 FRED data loading complete!")
        print(f"   📊 {total_metric_types} metric types loaded")
        print(f"   📈 {total_data_points} data points loaded")
        print(f"   🔗 Timeseries chains created with HEAD/TAIL/NEXT structure")
        
    async def verify_chain_structure(self):
        """Verify the timeseries chain structure."""
        print("\n🔍 Verifying timeseries chain structure...")
        
        async with self.driver.session(database=self.settings.neo4j_db) as session:
            # Count nodes
            result = await session.run("MATCH (mt:MetricType) RETURN count(mt) as count")
            data = await result.data()
            metric_types = data[0]['count']
            
            result = await session.run("MATCH (mv:MetricValue) RETURN count(mv) as count")
            data = await result.data()
            metric_values = data[0]['count']
            
            # Check HEAD/TAIL relationships
            result = await session.run("MATCH (mt:MetricType)-[:HEAD]->() RETURN count(mt) as count")
            data = await result.data()
            head_links = data[0]['count']
            
            result = await session.run("MATCH (mt:MetricType)-[:TAIL]->() RETURN count(mt) as count")
            data = await result.data()
            tail_links = data[0]['count']
            
            # Check NEXT chain relationships
            result = await session.run("MATCH ()-[:NEXT]->() RETURN count(*) as count")
            data = await result.data()
            next_links = data[0]['count']
            
            print(f"   📊 {metric_types} MetricType nodes")
            print(f"   📈 {metric_values} MetricValue nodes")
            print(f"   🔗 {head_links} HEAD relationships")
            print(f"   🔗 {tail_links} TAIL relationships")
            print(f"   🔗 {next_links} NEXT relationships")
            
            # Sample a chain
            result = await session.run("""
                MATCH (mt:MetricType)-[:HEAD]->(head:MetricValue)
                MATCH (mt)-[:TAIL]->(tail:MetricValue)
                RETURN mt.name as metric_name, head.date as first_date, tail.date as last_date
                LIMIT 5
            """)
            data = await result.data()
            
            print("\n   🔍 Sample timeseries chains:")
            for record in data:
                print(f"     {record['metric_name']}: {record['first_date']} → {record['last_date']}")
                
    async def run(self):
        """Run the complete FRED data loading process."""
        try:
            await self.create_schema()
            await self.create_geographic_hierarchy()
            await self.load_fred_data()
            await self.verify_chain_structure()
            
        except Exception as e:
            logger.error(f"Error in FRED data loading: {e}")
            raise
        finally:
            await self.driver.close()


async def main():
    """Main function for FRED data loading."""
    print("🏦 FRED Data Loader - Timeseries Chain Structure")
    print("=" * 50)
    
    loader = FREDLoader()
    await loader.run()
    
    print("\n🎉 FRED data loading complete!")
    print("✅ Timeseries chain structure implemented")
    print("✅ HEAD/TAIL links for fast access")
    print("✅ NEXT relationships for traversal")
    print("🚀 Ready for business intelligence queries!")


if __name__ == "__main__":
    asyncio.run(main()) 