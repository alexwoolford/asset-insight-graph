# Data Accuracy & Verification

## 📊 **Data Classification**

### ✅ **VERIFIED DATA**
These data points are verified facts scraped directly from CIM Group's official website:

- **Asset names**: Tribune Tower, Front & York, Centennial Yards, etc.
- **Locations**: Cities and states where assets are located
- **Platform classifications**: Real Estate, Infrastructure, Credit
- **Asset URLs**: Official images from CIM Group's CDN
- **Geographic coordinates**: Sourced from OpenStreetMap Nominatim API

### 🤖 **AI-Enhanced Verified Data**
These descriptions are generated using OpenAI GPT-4 but ONLY based on actual content scraped from CIM Group's website:

- **Property descriptions**: Created from real CIM Group marketing content
- **Platform descriptions**: Based on actual CIM Group platform documentation
- **Building classifications**: Inferred only from clear name patterns

### ⚠️ **Basic AI Data (Alternative)**
We also provide a basic approach that uses generic AI-generated descriptions. The enhanced approach using web-scraped content is recommended.

## 🏗️ **Enhanced Data Generation Process**

### 1. **Web Scraping (etl/descriptions.py)**
```python
# Scrapes actual content from CIM Group website
scraped_data = scrape_cim_asset_page(asset_name, img_url)
```

**Sources:**
- https://www.cimgroup.com/our-platforms/assets
- Individual asset pages (when available)
- Platform-specific descriptions

### 2. **GPT-Based Description Generation**
```python
prompt = """Based on the following factual information about a CIM Group asset, 
write a concise, factual property description (2-3 sentences max). 

ONLY include information that is explicitly provided. 
Do NOT add speculative details about amenities, sustainability features, 
or tenant types unless they are mentioned in the source material."""
```

**Guidelines:**
- ✅ Only use explicitly provided information
- ✅ Keep descriptions brief and factual
- ❌ No speculation about amenities or features
- ❌ No generic marketing language

### 3. **Fallback to Minimal Descriptions**
If web scraping fails or no OpenAI key is available:
```python
def _generate_minimal_description(asset):
    return f"{asset['name']} is a {asset['platform'].lower()} asset located in {asset['city']}, {asset['state']}. As part of CIM Group's {asset['platform'].lower()} platform, this represents..."
```

## 🔧 **Using Enhanced Data**

### **Generate Enhanced Descriptions**
```bash
# Generate enhanced descriptions from CIM Group website
make descriptions

# Or run directly:
cd etl && python descriptions.py
```

### **Load Enhanced Data with Vector Search**
```bash
# Complete setup with enhanced data (RECOMMENDED)
make complete-setup

# Or enhanced vector setup only:
make enhanced-setup
```

### **Compare Approaches**
```bash
# Enhanced approach (RECOMMENDED)
make enhanced-setup

# Basic approach (uses generic AI descriptions)
make vectors
```

## 📋 **Data Verification**

### **Data Verification Steps**

1. **Asset Verification**: All 12 assets confirmed on CIM Group website
2. **Location Verification**: Geocoding via OpenStreetMap
3. **Platform Verification**: Classifications match CIM Group structure
4. **Description Verification**: Based only on scraped CIM content

### **Example Enhanced Description**
```
Tribune Tower is a real estate asset located in Chicago, Illinois, owned and operated by CIM Group. It is part of CIM's portfolio, which includes various properties across the Americas and Europe.
```

**Analysis:**
- ✅ Uses actual asset name from CIM website
- ✅ Accurate location information
- ✅ Based on actual CIM Group website content
- ✅ No speculative features or amenities

### **Example Synthetic Description (Deprecated)**
```
Tribune Tower is a commercial development located in Chicago, Illinois. This direct real estate investment represents CIM Group's commitment to high-quality urban development and strategic asset positioning in key metropolitan markets. The property features modern office spaces designed for today's dynamic workforce, with flexible floor plates, advanced building systems, and premium amenities...
```

**Analysis:**
- ❌ Speculative details about "modern office spaces"
- ❌ Generic marketing language
- ❌ Assumptions about "flexible floor plates" and "premium amenities"
- ❌ No source for specific features claimed

## 🚀 **Complete Reproducible Setup**

To create the entire system from scratch with verified data:

```bash
# 1. Clone repository
git clone [repository-url]
cd asset-insight-graph

# 2. Setup environment
make setup

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your Neo4j and OpenAI credentials

# 4. Complete enhanced setup
make complete-setup

# 5. Launch application
make start-all
```

**Result**: A fully functional Asset Insight Graph with:
- ✅ 12 verified CIM Group assets
- ✅ Enhanced descriptions based on real CIM content
- ✅ Vector search with OpenAI embeddings
- ✅ Geographic and geospatial capabilities
- ✅ Professional Streamlit UI
- ✅ 100% reproducible from repository

## 📁 **Generated Files**

### **Enhanced Data Files**
- `etl/cim_assets.jsonl` - Original scraped data from CIM website
- `etl/cim_assets_enhanced.jsonl` - Enhanced with AI-generated descriptions
- Vector embeddings stored in Neo4j database

### **Data Source Tracking**
Each asset includes:
```json
{
  "name": "Tribune Tower",
  "property_description": "...",
  "description_source": "enhanced_web_scraped",
  "building_type": "Commercial"
}
```

## 🎯 **Quality Assurance**

### **Automated Verification**
```bash
# Test factual vector search
make test-vectors

# Verify knowledge graph
make verify
```

### **Manual Verification Checklist**
- [ ] All asset names match CIM Group website
- [ ] All locations are accurate
- [ ] Descriptions contain no speculative content
- [ ] Platform classifications are correct
- [ ] Vector search returns relevant results
- [ ] System is 100% reproducible

## 💡 **Best Practices**

1. **Always use enhanced approach** for production deployments
2. **Verify asset information** against CIM Group website regularly
3. **Update descriptions** when CIM Group updates their content
4. **Document data sources** for all enhancements
5. **Test vector search** to ensure relevance

This approach ensures that your Asset Insight Graph demonstration is built on solid, verifiable data while still showcasing advanced AI and graph capabilities. 