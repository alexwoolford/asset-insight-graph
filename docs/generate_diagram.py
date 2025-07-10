"""Generate PNG workflow diagrams for Asset Insight Graph.

Usage Example:
    from docs.generate_diagram import draw_mermaid_png
    
    # Generate workflow PNG
    draw_mermaid_png("my_workflow.png")
    
    # Or generate with default name
    draw_mermaid_png()  # Creates multi_tool_workflow.png
"""

import os
import subprocess
import tempfile
from pathlib import Path

def create_workflow_diagram():
    """Create a simplified LangGraph-style workflow state diagram."""
    
    mermaid_diagram = """stateDiagram-v2
    [*] --> __start__
    
    __start__ --> query_analysis
    
    query_analysis --> hybrid_search : Geographic + Semantic Query
    query_analysis --> vector_search : Pure Semantic Query
    query_analysis --> graph_search : Pure Geographic Query
    query_analysis --> __end__ : Invalid Query
    
    hybrid_search --> geographic_filter : Step 1 Filter by Location
    geographic_filter --> semantic_ranking : Step 2 Rank by Similarity
    semantic_ranking --> format_results
    
    vector_search --> embedding_generation
    embedding_generation --> similarity_search
    similarity_search --> format_results
    
    graph_search --> pattern_matching
    pattern_matching --> cypher_execution
    cypher_execution --> format_results
    
    format_results --> final_answer
    final_answer --> __end__
    
    __end__ --> [*]
    
    state hybrid_search {
        [*] --> texas_filter
        [*] --> california_filter
        [*] --> esg_ranking
        [*] --> luxury_ranking
        
        texas_filter --> [*]
        california_filter --> [*]
        esg_ranking --> [*]
        luxury_ranking --> [*]
    }
    
    state graph_search {
        [*] --> state_queries
        [*] --> platform_queries
        [*] --> geospatial_queries
        [*] --> portfolio_queries
        
        state_queries --> [*]
        platform_queries --> [*]
        geospatial_queries --> [*]
        portfolio_queries --> [*]
    }"""
    
    return mermaid_diagram

def check_mermaid_cli():
    """Check if Mermaid CLI is installed."""
    try:
        result = subprocess.run(['mmdc', '--version'], 
                              capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_mermaid_cli():
    """Install Mermaid CLI via npm."""
    try:
        print("📦 Installing Mermaid CLI...")
        subprocess.run(['npm', 'install', '-g', '@mermaid-js/mermaid-cli'], 
                      check=True)
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Mermaid CLI")
        return False

def generate_png_diagram(mermaid_content, output_path):
    """Generate PNG from Mermaid diagram using CLI."""
    
    # Create temporary file for Mermaid diagram
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_file:
        temp_file.write(mermaid_content)
        temp_mermaid_path = temp_file.name
    
    try:
        # Convert to PNG using Mermaid CLI (white background)
        cmd = ['mmdc', '-i', temp_mermaid_path, '-o', str(output_path), 
               '--backgroundColor', 'white']
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating PNG: {e}")
        return False
    finally:
        # Clean up temporary file
        os.unlink(temp_mermaid_path)

def draw_mermaid_png(filename="multi_tool_workflow.png"):
    """
    Generate PNG workflow diagram for Asset Insight Graph.
    
    Args:
        filename: Name of the PNG file to generate
    """
    
    # Create workflows directory
    workflows_dir = Path("workflows")
    workflows_dir.mkdir(exist_ok=True)
    
    output_path = workflows_dir / filename
    
    # Check if Mermaid CLI is available
    if not check_mermaid_cli():
        print("❌ Mermaid CLI not found")
        print("📦 To install: npm install -g @mermaid-js/mermaid-cli")
        print("🔗 Or visit: https://github.com/mermaid-js/mermaid-cli")
        return False
    
    # Generate the workflow diagram
    diagram_content = create_workflow_diagram()
    
    # Convert to PNG
    if generate_png_diagram(diagram_content, output_path):
        print(f"✅ Workflow diagram saved to {output_path}")
        return True
    else:
        print(f"❌ Failed to generate {output_path}")
        return False

def main():
    """Generate workflow PNG diagram for Asset Insight Graph."""
    
    print("🎯 Generating Asset Insight Graph Workflow Diagram...")
    
    # Generate the main workflow diagram
    success = draw_mermaid_png("multi_tool_workflow.png")
    
    if success:
        print("🎉 Done! Workflow PNG generated in workflows/ folder")
        print("📁 View the diagram: workflows/multi_tool_workflow.png")
    else:
        print("💡 Alternative: Use https://mermaid.live to convert diagrams manually")

if __name__ == "__main__":
    main()
