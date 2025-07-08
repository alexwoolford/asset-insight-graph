// Constraints
CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT tenant_id IF NOT EXISTS FOR (t:Tenant) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT partner_id IF NOT EXISTS FOR (p:Partner) REQUIRE p.id IS UNIQUE;

// Indexes
CREATE INDEX asset_name IF NOT EXISTS FOR (a:Asset) ON (a.name);
CREATE INDEX asset_city IF NOT EXISTS FOR (a:Asset) ON (a.city);

// Optional GDS projection
// CALL gds.graph.project('partnerGraph', 'Partner', 'CO_INVESTED');
