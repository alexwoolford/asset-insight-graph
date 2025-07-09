import re, json, requests
from bs4 import BeautifulSoup

def scrape_cim_assets():
    """
    CIM scraper with detailed debugging
    """
    URL = "https://www.cimgroup.com/our-platforms/assets"
    HEADS = {"User-Agent": "Mozilla/5.0 (compatible; AssetScraper/1.0)"}

    html = requests.get(URL, headers=HEADS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    print(f"Page loaded: {len(html):,} characters")

    # --- STEP 1: find every JSON blob that begins with {"items": ---
    json_re = re.compile(r'^\s*\{\s*"items"\s*:', re.DOTALL)
    json_tags = soup.find_all(string=json_re)

    print(f"Found {len(json_tags)} JSON blobs with 'items' property")

    assets = []
    for i, tag in enumerate(json_tags):
        print(f"\n--- Processing JSON blob {i+1} ---")
        
        try:
            blob = json.loads(tag)
            print(f"✓ Successfully parsed JSON")
        except json.JSONDecodeError as e:
            print(f"✗ JSON decode error: {e}")
            print(f"Raw JSON (first 200 chars): {tag[:200]}")
            continue

        # Show what's in this JSON object
        print(f"JSON keys: {list(blob.keys())}")
        
        group = blob.get("group")
        items = blob.get("items", [])
        print(f"Group: {group}")
        print(f"Items count: {len(items)}")
        
        # Show details of first few items
        for j, item in enumerate(items[:3]):
            print(f"  Item {j+1}: {list(item.keys())}")
            if 'origFileName' in item:
                print(f"    Filename: {item['origFileName']}")
            if '_id' in item:
                print(f"    ID: {item['_id']}")

        # STEP 2: walk forward in the DOM to get the human‑readable name + location
        try:
            name_node = tag.find_next(string=lambda s: s and s.strip())
            location_node = name_node.find_next(string=lambda s: s and s.strip()) if name_node else None

            name = name_node.strip() if name_node else None
            location = location_node.strip() if location_node else None
            
            print(f"Found name: '{name}'")
            print(f"Found location: '{location}'")
            
            city, state = (location.split(",", 1) + [None])[:2] if location else (None, None)
            city = city.strip() if city else None
            state = state.strip() if state else None
            
            print(f"Parsed city: '{city}', state: '{state}'")
            
        except Exception as e:
            print(f"Error extracting context: {e}")
            name = location = city = state = None

        # STEP 3: emit one row per image in the "items" list
        for item in items:
            asset = {
                "name": name,
                "platform": group,  # Real Estate / Infrastructure / Credit
                "city": city,
                "state": state,
                "img_url": item.get("url"),
                "img_filename": item.get("origFileName"),
                "item_id": item.get("_id"),
                "full_location": location
            }
            
            # Try to extract additional info from filename
            filename_info = extract_info_from_filename(item.get("origFileName", ""))
            asset.update(filename_info)
            
            assets.append(asset)

        print(f"Added {len(items)} assets from this JSON blob")

    print(f"\n{'='*60}")
    print(f"TOTAL ASSETS: {len(assets)}")
    print(f"{'='*60}")
    
    # Summary by platform
    by_platform = {}
    for asset in assets:
        platform = asset.get('platform', 'Unknown')
        if platform not in by_platform:
            by_platform[platform] = []
        by_platform[platform].append(asset)
    
    for platform, platform_assets in by_platform.items():
        print(f"\n{platform}: {len(platform_assets)} assets")
        unique_names = set()
        for asset in platform_assets:
            # Try to get the best name available
            best_name = (asset.get('name') or 
                        asset.get('name_from_filename') or 
                        asset.get('img_filename', '').split('.')[0])
            if best_name:
                unique_names.add(best_name)
        
        print(f"  Unique names found: {len(unique_names)}")
        for name in sorted(unique_names)[:5]:  # Show first 5
            print(f"    • {name}")
        if len(unique_names) > 5:
            print(f"    ... and {len(unique_names) - 5} more")

    return assets

def extract_info_from_filename(filename):
    """
    Extract property info from filename like 'Real-Estate-Chicago-Illinois-Tribune-Tower.jpg'
    """
    if not filename:
        return {}
    
    info = {}
    
    # Remove file extension
    base_name = filename.replace('.jpg', '').replace('.png', '').replace('.webp', '')
    
    # Split by hyphens
    if '-' in base_name:
        parts = base_name.split('-')
        
        if len(parts) >= 4:
            try:
                # Parse pattern: Platform-Type-City-State-Property-Name
                platform_part = parts[0]
                type_part = parts[1] if len(parts) > 1 else ""
                
                # Combine platform parts
                if type_part.lower() in ['estate', 'lightbox']:
                    info['platform_from_filename'] = f"{platform_part} {type_part}".title()
                    start_idx = 2
                else:
                    info['platform_from_filename'] = platform_part.title()
                    start_idx = 1
                
                # Extract location and name
                if len(parts) > start_idx + 1:
                    info['city_from_filename'] = parts[start_idx].replace('_', ' ').title()
                    info['state_from_filename'] = parts[start_idx + 1].replace('_', ' ').title()
                    
                    # Everything after state is the property name
                    if len(parts) > start_idx + 2:
                        name_parts = parts[start_idx + 2:]
                        property_name = ' '.join(name_parts).replace('_', ' ').title()
                        info['name_from_filename'] = property_name
                        
            except Exception as e:
                print(f"Error parsing filename '{filename}': {e}")
    
    return info

def save_results(assets):
    """
    Save results as JSONL (JSON Lines) format
    """
    # Create clean dataset
    clean_assets = []
    
    for asset in assets:
        # Use the best available information
        clean_asset = {
            'name': (asset.get('name') or 
                    asset.get('name_from_filename') or 
                    asset.get('img_filename', '').split('.')[0] or 
                    'Unknown'),
            'city': asset.get('city') or asset.get('city_from_filename') or '',
            'state': asset.get('state') or asset.get('state_from_filename') or '',
            'platform': (asset.get('platform') or 
                        asset.get('platform_from_filename') or 
                        'Unknown'),
            'location': asset.get('full_location') or 
                       f"{asset.get('city_from_filename', '')}, {asset.get('state_from_filename', '')}".strip(', '),
            'img_url': asset.get('img_url', ''),
            'img_filename': asset.get('img_filename', ''),
            'item_id': asset.get('item_id', '')
        }
        clean_assets.append(clean_asset)
    
    # Save as JSONL (JSON Lines)
    with open('cim_assets.jsonl', 'w') as f:
        for asset in clean_assets:
            f.write(json.dumps(asset) + '\n')
    
    print(f"\nSaved {len(clean_assets)} assets to cim_assets.jsonl")
    
    return clean_assets

if __name__ == "__main__":
    print("CIM Group Asset Scraper")
    print("="*40)
    
    assets = scrape_cim_assets()
    clean_assets = save_results(assets)
    
    print(f"\n🎉 Success! Found {len(assets)} total asset records.")
    
    # Show some examples
    if clean_assets:
        print(f"\nSample assets:")
        for i, asset in enumerate(clean_assets[:5]):
            location_str = asset['location'] if asset['location'] else "Location TBD"
            print(f"  {i+1}. {asset['name']} ({asset['platform']}) - {location_str}")
        
        if len(clean_assets) > 5:            print(f"  ... and {len(clean_assets) - 5} more assets") 
