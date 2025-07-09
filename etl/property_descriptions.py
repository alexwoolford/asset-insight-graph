"""
Enhanced Property Description Generator for CIM Assets

This module creates rich, descriptive text for each property that captures:
- Investment strategy and market positioning
- Architectural and design features
- Neighborhood characteristics and amenities
- Target tenant profiles and use cases
- Sustainability and ESG features
"""

import json
from typing import Dict, Any, List


def generate_property_description(asset: Dict[str, Any]) -> str:
    """Generate a comprehensive property description for vector embedding."""
    
    name = asset.get("name", "Unknown Property")
    city = asset.get("city", "")
    state = asset.get("state", "")
    platform = asset.get("platform", "")
    building_type = asset.get("building_type", "Mixed Use")
    
    # Base description with location context
    description_parts = []
    
    # Property introduction
    description_parts.append(f"{name} is a {building_type.lower()} development located in {city}, {state}.")
    
    # Platform-specific investment strategy
    if platform == "Real Estate":
        description_parts.append(
            "This direct real estate investment represents CIM Group's commitment to high-quality "
            "urban development and strategic asset positioning in key metropolitan markets."
        )
        
        # Building type specific features
        if "Commercial" in building_type:
            description_parts.append(
                "The property features modern office spaces designed for today's dynamic workforce, "
                "with flexible floor plates, advanced building systems, and premium amenities that "
                "attract top-tier corporate tenants and knowledge workers."
            )
        elif "Mixed Use" in building_type:
            description_parts.append(
                "This mixed-use development combines residential, retail, and office components, "
                "creating a vibrant live-work-play environment that serves diverse community needs "
                "and maximizes land utilization in urban settings."
            )
        elif "Residential" in building_type:
            description_parts.append(
                "The residential development offers modern living spaces with contemporary amenities, "
                "designed to meet the housing needs of urban professionals and families seeking "
                "quality accommodation in desirable locations."
            )
            
    elif platform == "Infrastructure":
        description_parts.append(
            "This infrastructure investment aligns with CIM Group's focus on essential services "
            "and sustainable development, providing stable returns while supporting community "
            "infrastructure needs and environmental stewardship."
        )
        
        # Infrastructure-specific features
        if "Solar" in name:
            description_parts.append(
                "This renewable energy facility generates clean solar power, contributing to "
                "decarbonization goals while providing long-term contracted revenue streams. "
                "The project supports grid stability and helps meet renewable energy mandates."
            )
        elif "Water" in name:
            description_parts.append(
                "This water infrastructure asset provides essential water storage and management "
                "services, supporting regional water security and sustainable resource management "
                "in areas facing water scarcity challenges."
            )
        elif "Carbon" in name:
            description_parts.append(
                "This carbon capture and storage facility represents cutting-edge environmental "
                "technology, helping industrial partners reduce their carbon footprint while "
                "generating carbon credit revenues and supporting climate goals."
            )
        else:
            description_parts.append(
                "This infrastructure asset provides essential services to the community while "
                "generating stable, long-term cash flows through regulated or contracted revenue streams."
            )
            
    elif platform == "Credit":
        description_parts.append(
            "This real estate credit investment provides financing solutions for quality developments, "
            "offering attractive risk-adjusted returns while supporting the creation of valuable "
            "real estate assets in strategic markets."
        )
        
        description_parts.append(
            "The credit investment is secured by high-quality real estate collateral and structured "
            "to provide stable income streams while maintaining capital preservation focus. "
            "The underlying asset benefits from strong market fundamentals and experienced sponsorship."
        )
    
    # Location-specific market context
    market_context = get_market_context(city, state)
    if market_context:
        description_parts.append(market_context)
    
    # ESG and sustainability features
    sustainability_features = get_sustainability_features(asset)
    if sustainability_features:
        description_parts.append(sustainability_features)
    
    # Target tenant and use case profile
    tenant_profile = get_tenant_profile(building_type, platform)
    if tenant_profile:
        description_parts.append(tenant_profile)
    
    return " ".join(description_parts)


def get_market_context(city: str, state: str) -> str:
    """Generate market context based on city and state."""
    
    # Major metropolitan markets
    market_descriptions = {
        ("Chicago", "Illinois"): (
            "Located in Chicago's dynamic urban core, the property benefits from the city's "
            "position as a major Midwest hub for finance, technology, and commerce. The market "
            "offers strong transportation connectivity, diverse economic base, and ongoing urban renewal."
        ),
        ("New York", "New York"): (
            "Positioned in New York City's unparalleled real estate market, the property leverages "
            "the city's status as a global financial center and cultural capital. The market provides "
            "exceptional tenant depth, premium pricing power, and long-term value appreciation potential."
        ),
        ("Atlanta", "Georgia"): (
            "Located in Atlanta's thriving metropolitan area, the property benefits from the city's "
            "role as the Southeast's business and transportation hub. The market features strong "
            "population growth, corporate relocations, and a diverse, educated workforce."
        ),
        ("Austin", "Texas"): (
            "Situated in Austin's rapidly growing tech corridor, the property capitalizes on the city's "
            "emergence as a major technology and innovation center. The market benefits from strong "
            "job growth, young demographics, and significant corporate investment from tech giants."
        ),
        ("Los Angeles", "California"): (
            "Located in the Los Angeles metropolitan area, the property benefits from one of the "
            "nation's largest and most diverse economies. The market offers access to entertainment, "
            "technology, international trade, and manufacturing sectors."
        ),
        ("Houston", "Texas"): (
            "Positioned in Houston's energy capital market, the property benefits from the city's "
            "leadership in energy, healthcare, and aerospace industries. The market provides economic "
            "diversification opportunities and strong international business connections."
        ),
        ("Phoenix", "Arizona"): (
            "Located in Phoenix's rapidly expanding metropolitan area, the property benefits from "
            "strong population growth, business-friendly environment, and emerging technology sector. "
            "The market offers attractive demographics and continued economic diversification."
        ),
    }
    
    return market_descriptions.get((city, state), "")


def get_sustainability_features(asset: Dict[str, Any]) -> str:
    """Generate sustainability and ESG features description."""
    
    platform = asset.get("platform", "")
    building_type = asset.get("building_type", "")
    name = asset.get("name", "")
    
    if platform == "Infrastructure":
        if "Solar" in name or "Renewables" in name:
            return (
                "The project incorporates advanced environmental technologies and sustainable practices, "
                "contributing to carbon reduction goals and supporting the transition to clean energy. "
                "ESG benefits include renewable energy generation, job creation, and community environmental impact."
            )
        elif "Water" in name:
            return (
                "The facility employs sustainable water management practices and technologies, "
                "supporting regional water security and environmental stewardship. ESG benefits "
                "include resource conservation, climate resilience, and community benefit."
            )
        elif "Carbon" in name:
            return (
                "This facility represents cutting-edge carbon capture technology, directly supporting "
                "climate change mitigation efforts and helping industrial partners achieve their "
                "decarbonization goals while generating environmental credits."
            )
    
    # General sustainability features for all properties
    return (
        "The development incorporates sustainable design principles and energy-efficient systems, "
        "supporting ESG objectives through reduced environmental impact, enhanced occupant wellness, "
        "and long-term operational efficiency that benefits both tenants and investors."
    )


def get_tenant_profile(building_type: str, platform: str) -> str:
    """Generate target tenant and use case profile."""
    
    if platform == "Real Estate":
        if "Commercial" in building_type:
            return (
                "Target tenants include Fortune 500 companies, growing technology firms, professional "
                "services organizations, and knowledge-based businesses seeking premium office space "
                "with modern amenities and strategic location advantages."
            )
        elif "Mixed Use" in building_type:
            return (
                "The development serves diverse tenants including retail establishments, restaurants, "
                "residential occupants, and office users, creating a vibrant community ecosystem "
                "that attracts both businesses and residents seeking integrated urban lifestyle."
            )
        elif "Residential" in building_type:
            return (
                "Target residents include urban professionals, young families, and empty nesters "
                "seeking modern living spaces with premium amenities, convenient location, and "
                "access to employment centers, entertainment, and transportation."
            )
    
    elif platform == "Infrastructure":
        return (
            "The infrastructure asset serves essential community and regional needs, providing "
            "critical services to municipalities, utilities, and industrial users while supporting "
            "economic development and quality of life in the service area."
        )
    
    elif platform == "Credit":
        return (
            "The credit investment supports quality real estate development by experienced sponsors, "
            "ultimately serving end tenants and users who benefit from well-located, professionally "
            "managed properties that meet modern market demands."
        )
    
    return ""


def generate_enhanced_dataset() -> List[Dict[str, Any]]:
    """Generate enhanced descriptions for all CIM assets."""
    
    # Read existing assets
    with open("cim_assets.jsonl", "r") as f:
        assets = [json.loads(line) for line in f]
    
    enhanced_assets = []
    
    for asset in assets:
        # Add building type (this logic should match your existing ETL)
        asset["building_type"] = infer_building_type(asset)
        
        # Generate comprehensive description
        asset["property_description"] = generate_property_description(asset)
        
        # Add investment themes keywords for better search
        asset["investment_themes"] = get_investment_themes(asset)
        
        enhanced_assets.append(asset)
    
    return enhanced_assets


def infer_building_type(asset: Dict[str, Any]) -> str:
    """Infer building type from asset data (matches existing ETL logic)."""
    
    name = asset.get("name", "").lower()
    platform = asset.get("platform", "")
    
    if any(word in name for word in ["tower", "building", "center", "plaza"]):
        return "Commercial"
    elif any(word in name for word in ["apartments", "residence", "homes", "view"]):
        return "Residential"
    elif any(word in name for word in ["mall", "retail", "shopping"]):
        return "Retail"
    elif any(word in name for word in ["solar", "wind", "energy", "power", "renewables"]):
        return "Energy Infrastructure"
    elif any(word in name for word in ["water", "utility"]):
        return "Water Infrastructure"
    elif any(word in name for word in ["carbon"]):
        return "Environmental Infrastructure"
    else:
        return "Mixed Use"


def get_investment_themes(asset: Dict[str, Any]) -> List[str]:
    """Generate investment theme keywords for enhanced search."""
    
    themes = []
    platform = asset.get("platform", "")
    building_type = asset.get("building_type", "")
    city = asset.get("city", "")
    state = asset.get("state", "")
    name = asset.get("name", "")
    
    # Platform themes
    if platform == "Real Estate":
        themes.extend(["direct real estate", "core", "urban development", "institutional quality"])
    elif platform == "Infrastructure":
        themes.extend(["infrastructure", "essential services", "stable income", "contracted revenue"])
    elif platform == "Credit":
        themes.extend(["real estate credit", "financing", "secured lending", "income generation"])
    
    # Building type themes
    if "Commercial" in building_type:
        themes.extend(["office", "corporate headquarters", "business district", "professional services"])
    elif "Residential" in building_type:
        themes.extend(["multifamily", "apartments", "urban living", "housing"])
    elif "Infrastructure" in building_type:
        themes.extend(["utilities", "essential infrastructure", "regulated assets", "public-private partnership"])
    elif "Mixed Use" in building_type:
        themes.extend(["mixed use", "live work play", "urban planning", "community development"])
    
    # Market themes
    if state in ["California", "New York"]:
        themes.extend(["gateway market", "high barrier to entry", "premium market"])
    elif state in ["Texas", "Georgia", "Arizona"]:
        themes.extend(["growth market", "business friendly", "population growth"])
    
    # ESG themes
    if any(word in name.lower() for word in ["solar", "renewable", "carbon", "water", "sustainable"]):
        themes.extend(["ESG", "sustainability", "environmental", "climate", "green"])
    
    # Tech and innovation themes
    if city in ["Austin", "Los Angeles"]:
        themes.extend(["technology hub", "innovation", "startups", "tech companies"])
    
    return themes


if __name__ == "__main__":
    # Generate enhanced dataset
    enhanced_assets = generate_enhanced_dataset()
    
    # Save enhanced dataset
    with open("cim_assets_enhanced.jsonl", "w") as f:
        for asset in enhanced_assets:
            f.write(json.dumps(asset) + "\n")
    
    print(f"Generated enhanced descriptions for {len(enhanced_assets)} assets")
    
    # Print sample
    print("\nSample enhanced description:")
    print("="*50)
    print(f"Asset: {enhanced_assets[0]['name']}")
    print(f"Description: {enhanced_assets[0]['property_description']}")
    print(f"Investment Themes: {', '.join(enhanced_assets[0]['investment_themes'])}") 