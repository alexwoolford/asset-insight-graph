# Data Sources

## CIM Asset Dataset

The `etl/cim_assets.jsonl` file contains a list of properties scraped from the
[CIM Group](https://www.cimgroup.com/our-platforms/assets) website. Each line is a
JSON object describing a single asset with its name, city, state and image
metadata.

### How it was generated

The dataset was produced by running `etl/cim_assets_scrape.py`. The script fetches
the web page, parses the embedded JSON blobs and extracts the asset details. It then
writes them to `etl/cim_assets.jsonl` in [JSON Lines](https://jsonlines.org/)
format.

### Regenerating the file

1. Activate the Python environment used for this project.
2. Run the scraper:
   ```bash
   python etl/cim_assets_scrape.py
   ```
3. The script saves a fresh `cim_assets.jsonl` under the `etl/` directory.

After regeneration you can load the assets into Neo4j with `make load`.
