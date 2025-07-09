// Enhanced Asset Insight Graph Schema for CIM Group

// =========================
// CONSTRAINTS
// =========================

// Core entity constraints
CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT city_composite IF NOT EXISTS FOR (c:City) REQUIRE (c.name, c.state) IS UNIQUE;
CREATE CONSTRAINT state_name IF NOT EXISTS FOR (s:State) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT region_name IF NOT EXISTS FOR (r:Region) REQUIRE r.name IS UNIQUE;
CREATE CONSTRAINT platform_name IF NOT EXISTS FOR (p:Platform) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT building_type_name IF NOT EXISTS FOR (bt:BuildingType) REQUIRE bt.name IS UNIQUE;
CREATE CONSTRAINT investment_type_name IF NOT EXISTS FOR (it:InvestmentType) REQUIRE it.name IS UNIQUE;

// =========================
// INDEXES
// =========================

// Asset indexes
CREATE INDEX asset_name IF NOT EXISTS FOR (a:Asset) ON (a.name);
CREATE INDEX asset_building_type IF NOT EXISTS FOR (a:Asset) ON (a.building_type);
CREATE INDEX asset_investment_type IF NOT EXISTS FOR (a:Asset) ON (a.investment_type);

// Geospatial Point type indexes (native Neo4j spatial)
CREATE POINT INDEX asset_location_geo IF NOT EXISTS FOR (a:Asset) ON (a.location);

// Geographic indexes
CREATE INDEX city_name IF NOT EXISTS FOR (c:City) ON (c.name);
CREATE POINT INDEX city_location_geo IF NOT EXISTS FOR (c:City) ON (c.location);
CREATE INDEX state_name IF NOT EXISTS FOR (s:State) ON (s.name);
CREATE INDEX region_name IF NOT EXISTS FOR (r:Region) ON (r.name);

// Business indexes
CREATE INDEX platform_name IF NOT EXISTS FOR (p:Platform) ON (p.name);
CREATE INDEX building_type_name IF NOT EXISTS FOR (bt:BuildingType) ON (bt.name);
CREATE INDEX investment_type_name IF NOT EXISTS FOR (it:InvestmentType) ON (it.name) 