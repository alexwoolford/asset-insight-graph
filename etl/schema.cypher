// CIM Asset Insight Graph Schema
// Constraints and indexes for Neo4j knowledge graph

// =========================
// CORE CONSTRAINTS
// =========================

// Primary entity constraints  
CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT city_composite IF NOT EXISTS FOR (c:City) REQUIRE (c.name, c.state) IS UNIQUE;
CREATE CONSTRAINT state_name IF NOT EXISTS FOR (s:State) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT region_name IF NOT EXISTS FOR (r:Region) REQUIRE r.name IS UNIQUE;
CREATE CONSTRAINT platform_name IF NOT EXISTS FOR (p:Platform) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT building_type_name IF NOT EXISTS FOR (bt:BuildingType) REQUIRE bt.name IS UNIQUE;
CREATE CONSTRAINT investment_type_name IF NOT EXISTS FOR (it:InvestmentType) REQUIRE it.name IS UNIQUE;

// =========================
// PERFORMANCE INDEXES
// =========================

// Asset discovery indexes (for GraphRAG)
CREATE INDEX asset_name IF NOT EXISTS FOR (a:Asset) ON (a.name);
CREATE TEXT INDEX asset_name_text IF NOT EXISTS FOR (a:Asset) ON (a.name);

// Geospatial indexes (for location-based queries)
CREATE POINT INDEX asset_location_geo IF NOT EXISTS FOR (a:Asset) ON (a.location);
CREATE POINT INDEX city_location_geo IF NOT EXISTS FOR (c:City) ON (c.location);

// Business categorization indexes
CREATE INDEX platform_name IF NOT EXISTS FOR (p:Platform) ON (p.name);
CREATE INDEX building_type_name IF NOT EXISTS FOR (bt:BuildingType) ON (bt.name);
CREATE INDEX investment_type_name IF NOT EXISTS FOR (it:InvestmentType) ON (it.name);

// Geographic discovery indexes
CREATE INDEX city_name IF NOT EXISTS FOR (c:City) ON (c.name);
CREATE INDEX state_name IF NOT EXISTS FOR (s:State) ON (s.name);
CREATE INDEX region_name IF NOT EXISTS FOR (r:Region) ON (r.name);

 