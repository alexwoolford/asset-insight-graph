"""
Asset Insight Graph - Streamlit Demo Application

A user-friendly interface for querying real estate assets using natural language.
Similar to ps-genai-agents but tailored for asset management.
"""

import streamlit as st
import pandas as pd
import requests
import json
import time
from typing import Dict, Any, List, Optional
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Asset Insight Graph",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean CIM Group Styling - exactly like their website
st.markdown("""
<style>
    /* Force everything to be clean and white like CIM's website */
    .main, .main > div, .block-container, 
    .stApp, .stAppViewContainer, .stAppViewBlockContainer {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Main header - simple and clean like CIM */
    .main-header {
        font-size: 2.25rem;
        font-weight: 600;
        color: #000000 !important;
        text-align: center;
        margin-bottom: 1rem;
        font-family: system-ui, -apple-system, sans-serif;
    }
    
    /* Clean white layout */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        background-color: #ffffff !important;
    }
    
    /* Response section - clean and simple */
    .response-highlight {
        background-color: #ffffff !important;
        color: #000000 !important;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #e5e5e5;
    }
    
    .response-highlight h3 {
        color: #000000 !important;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    /* Clean inputs */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #d0d0d0;
        border-radius: 2px;
        font-family: system-ui, -apple-system, sans-serif;
    }
    
    /* Simple buttons */
    .stButton > button {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #d0d0d0;
        border-radius: 2px;
        font-family: system-ui, -apple-system, sans-serif;
        font-weight: 400;
    }
    
    .stButton > button[kind="primary"] {
        background-color: #0066cc !important;
        color: #ffffff !important;
        border: 1px solid #0066cc;
    }
    
    /* Fix sidebar completely */
    .sidebar, .sidebar .sidebar-content, .sidebar .stMarkdown, 
    .sidebar h1, .sidebar h2, .sidebar h3, .sidebar h4, .sidebar h5, .sidebar h6,
    .sidebar p, .sidebar div, .sidebar span, .sidebar button {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Force sidebar buttons to be readable */
    .sidebar .stButton > button {
        background-color: #f5f5f5 !important;
        color: #000000 !important;
        border: 1px solid #d0d0d0 !important;
    }
    
    /* Force all text to be black everywhere */
    *, .stMarkdown, .stText, .stCaption, .stCode {
        color: #000000 !important;
    }
    
    /* Fix data table completely - force white background and black text */
    .stDataFrame, .stDataFrame > div, .stDataFrame table, 
    .stDataFrame thead, .stDataFrame tbody, .stDataFrame th, .stDataFrame td,
    .stDataFrame .dataframe, .stDataFrame .dataframe th, .stDataFrame .dataframe td {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-color: #e5e5e5 !important;
    }
    
    /* Override any dark theme on tables */
    [data-testid="stDataFrame"] {
        background-color: #ffffff !important;
    }
    
    [data-testid="stDataFrame"] table {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    [data-testid="stDataFrame"] th {
        background-color: #f8f9fa !important;
        color: #000000 !important;
        border-bottom: 1px solid #e5e5e5 !important;
    }
    
    [data-testid="stDataFrame"] td {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-bottom: 1px solid #f0f0f0 !important;
    }
    
    /* Success indicator */
    .stSuccess {
        background-color: #e8f5e8 !important;
        color: #000000 !important;
        border-left: 3px solid #4caf50;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Typography */
    h1, h2, h3, h4, h5, h6, p, div, span {
        color: #000000 !important;
        font-family: system-ui, -apple-system, sans-serif !important;
    }
</style>
""", unsafe_allow_html=True)

class AssetInsightGraphUI:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.example_questions = [
            "assets in California",
            "portfolio distribution", 
            "commercial buildings",
            "assets within 20km of Los Angeles",
            "how many assets",
            "residential properties in Texas"
        ]
        
    def check_api_health(self) -> bool:
        """Check if the API is running."""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def query_api(self, question: str) -> Dict[str, Any]:
        """Send question to the Asset Insight Graph API."""
        try:
            response = requests.post(
                f"{self.api_base_url}/qa",
                json={"question": question},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"API Error: {str(e)}"}
    
    def render_header(self):
        """Render the main header."""
        st.markdown('<div class="main-header">🏢 Asset Insight Graph</div>', unsafe_allow_html=True)
        st.markdown("**Ask questions about your assets in natural language and get intelligent insights backed by Neo4j knowledge graphs.**")
    
    def render_sidebar(self):
        """Render the sidebar with example questions and info."""
        with st.sidebar:
            st.markdown("## 🎯 Example Questions")
            st.markdown("Click any example below to try it:")
            
            for question in self.example_questions:
                if st.button(f"💭 {question}", key=f"example_{question}", use_container_width=True):
                    st.session_state.selected_question = question
            
            st.divider()
            
            st.markdown("## 🔧 System Status")
            api_status = self.check_api_health()
            if api_status:
                st.success("✅ API Online")
            else:
                st.error("❌ API Offline")
                st.markdown("Start the API with: `python -m api.main`")
            
            st.divider()
            
            st.markdown("## 🏗️ Architecture")
            st.markdown("""
            **Multi-Agent Workflow:**
            - 🛡️ **Guardrails**: Input validation
            - 📋 **Planner**: Query analysis  
            - 🔧 **Tool Selection**: Pattern matching
            - 💾 **Predefined Cypher**: Fast queries
            - 🤖 **Text2Cypher**: LLM fallback
            - 📝 **Summarizer**: Natural language
            """)
            
            st.markdown("## 📊 Capabilities")
            st.markdown("""
            - **Geographic Queries**: States, regions, cities
            - **Portfolio Analysis**: Platform distribution  
            - **Building Types**: Commercial, residential
            - **Geospatial**: Distance-based searches
            - **Business Intelligence**: Asset metrics
            """)
    
    def render_compact_metrics(self, response_data: Dict[str, Any]):
        """Render compact metrics and workflow in a single row."""
        if "answer" in response_data or "cypher" in response_data:
            # Determine workflow based on response
            if response_data.get("pattern_matched", False):
                agent_type = "Fast Query"
                workflow_emoji = "⚡"
                workflow_text = "Pattern Match"
            else:
                agent_type = "AI Query"
                workflow_emoji = "🤖"  
                workflow_text = "Text2Cypher"
            
            # Results count
            results_data = response_data.get("data") or response_data.get("results")
            results_count = len(results_data) if results_data and isinstance(results_data, list) else 0
            
            # Clean metrics row with better spacing
            col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 2])
            with col1:
                st.metric("📊 Results", f"{results_count}")
            with col2:
                st.metric(f"{workflow_emoji} Agent", agent_type)
            with col3:
                st.metric("⏱️ Time", "< 1s")
            with col4:
                st.caption(f"**Workflow:** {workflow_text}")
                st.caption("🛡️ → 📋 → 🔧 → 💾 → 📝 → ✅")
    
    def render_query_results(self, response_data: Dict[str, Any]):
        """Render query results prominently (not collapsed)."""
        # Handle both 'data' and 'results' field names
        results_data = response_data.get("data") or response_data.get("results")
        if results_data and isinstance(results_data, list) and results_data:
            st.markdown("### 📊 Query Results")
            df = pd.DataFrame(results_data)
            st.dataframe(df, use_container_width=True)
            
            # Download button
            col1, col2 = st.columns([1, 4])
            with col1:
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 CSV",
                    data=csv,
                    file_name=f"asset_query_{int(time.time())}.csv",
                    mime="text/csv"
                )
    
    def render_cypher_details(self, response_data: Dict[str, Any]):
        """Render Cypher query details in an expandable section."""
        with st.expander("🔍 Technical Details", expanded=False):
            if "cypher" in response_data:
                st.markdown("**Generated Cypher Query:**")
                st.markdown(f'<div class="cypher-box">{response_data["cypher"]}</div>', unsafe_allow_html=True)
    
    def render_data_visualization(self, response_data: Dict[str, Any]):
        """Create visualizations from the query results."""
        # Handle both 'data' and 'results' field names
        results_data = response_data.get("data") or response_data.get("results")
        if not results_data or not isinstance(results_data, list) or len(results_data) == 0:
            return  # Skip visualization if no data
        
        try:
            df = pd.DataFrame(results_data)
            
            # Only render charts for queries that specifically need visualization
            # Portfolio distribution with both platform and region
            if "platform" in df.columns and "region" in df.columns and "asset_count" in df.columns:
                st.markdown("### 📊 Portfolio Distribution")
                
                # Group by platform to get totals
                platform_totals = df.groupby("platform")["asset_count"].sum().reset_index()
                
                if len(platform_totals) > 0:
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = px.bar(
                            platform_totals, 
                            x="platform", 
                            y="asset_count",
                            title="By Platform",
                            color="asset_count",
                            color_continuous_scale="Blues"
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Group by region to get totals  
                        region_totals = df.groupby("region")["asset_count"].sum().reset_index()
                        if len(region_totals) > 0:
                            fig2 = px.pie(
                                region_totals,
                                names="region",
                                values="asset_count", 
                                title="By Region"
                            )
                            fig2.update_layout(height=400)
                            st.plotly_chart(fig2, use_container_width=True)
            
            # Distance analysis only
            elif "distance_km" in df.columns and "asset_name" in df.columns:
                st.markdown("### 📊 Distance Analysis")
                fig = px.scatter(
                    df,
                    x="distance_km",
                    y="asset_name",
                    title="Assets by Distance",
                    hover_data=["distance_miles"] if "distance_miles" in df.columns else None
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
        except Exception as e:
            # If visualization fails, just skip it silently
            st.caption(f"Note: Visualization not available for this query type")
    
    def render_response(self, response_data: Dict[str, Any]):
        """Render the complete response with all components."""
        if "error" in response_data:
            st.error(f"❌ {response_data['error']}")
            return
        
        # 1. MAIN RESPONSE FIRST (most important)
        if "answer" in response_data:
            st.markdown('<div class="response-highlight">', unsafe_allow_html=True)
            st.markdown("### 💬 Response")
            st.markdown(f"**{response_data['answer']}**")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 2. QUERY RESULTS (visible by default)
        self.render_query_results(response_data)
        
        # 3. COMPACT METRICS (one clean row)
        self.render_compact_metrics(response_data)
        
        # 4. DATA VISUALIZATION (if available)  
        self.render_data_visualization(response_data)
        
        # 5. TECHNICAL DETAILS (collapsed by default)
        self.render_cypher_details(response_data)
    
    def run(self):
        """Main application runner."""
        self.render_header()
        self.render_sidebar()
        
        # Initialize session state
        if "conversation_history" not in st.session_state:
            st.session_state.conversation_history = []
        
        if "selected_question" not in st.session_state:
            st.session_state.selected_question = ""
        
        # Main query interface
        st.markdown("## 💭 Ask Your Question")
        
        # Use selected question if available
        default_value = st.session_state.selected_question if st.session_state.selected_question else ""
        
        question = st.text_input(
            "Enter your question about the asset portfolio:",
            value=default_value,
            placeholder="e.g., 'assets in California' or 'portfolio distribution'"
        )
        
        col1, col2, col3 = st.columns([2, 1, 4])
        with col1:
            submit_button = st.button("🚀 Ask", type="primary", use_container_width=True)
        with col2:
            clear_button = st.button("🗑️ Clear", use_container_width=True)
        with col3:
            st.empty()  # Spacer
        
        if clear_button:
            st.session_state.conversation_history = []
            st.rerun()
        
        # Auto-submit if question was selected from sidebar
        if st.session_state.selected_question and not submit_button:
            if not self.check_api_health():
                st.error("❌ API is not running. Please start the FastAPI server with: `python -m api.main`")
                return
            
            with st.spinner("🤔 Processing your question..."):
                response_data = self.query_api(st.session_state.selected_question)
            
            # Add to conversation history
            st.session_state.conversation_history.append({
                "question": st.session_state.selected_question,
                "response": response_data,
                "timestamp": time.time()
            })
            
            # Clear the selected question after processing
            st.session_state.selected_question = ""
        
        # Process question from manual submission
        elif submit_button and question:
            if not self.check_api_health():
                st.error("❌ API is not running. Please start the FastAPI server with: `python -m api.main`")
                return
            
            with st.spinner("🤔 Processing your question..."):
                response_data = self.query_api(question)
            
            # Add to conversation history
            st.session_state.conversation_history.append({
                "question": question,
                "response": response_data,
                "timestamp": time.time()
            })
        
        # Display latest conversation
        if st.session_state.conversation_history:            
            # Show the latest response
            latest_item = st.session_state.conversation_history[-1]
            
            # Create a clean header for the current query
            st.markdown("---")
            query_header_col1, query_header_col2 = st.columns([4, 1])
            with query_header_col1:
                st.markdown(f"### 🔍 Current Query: *{latest_item['question']}*")
            with query_header_col2:
                if len(st.session_state.conversation_history) > 1:
                    with st.popover("📚 History", use_container_width=True):
                        st.markdown(f"**{len(st.session_state.conversation_history)} total conversations**")
                        for i, item in enumerate(reversed(st.session_state.conversation_history[:-1])):
                            idx = len(st.session_state.conversation_history) - 1 - i
                            results_data = item["response"].get("data") or item["response"].get("results")
                            results_count = len(results_data) if results_data and isinstance(results_data, list) else 0
                            
                            st.markdown(f"**Q{idx}:** {item['question']}")
                            if "answer" in item["response"]:
                                st.caption(f"💬 {item['response']['answer'][:100]}...")
                            st.caption(f"📊 {results_count} results")
                            st.markdown("---")
            
            # Render the response
            self.render_response(latest_item["response"])

# Main application
def main():
    app = AssetInsightGraphUI()
    app.run()

if __name__ == "__main__":
    main() 