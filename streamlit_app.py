"""
Asset Insight Graph - Streamlit Application

A user-friendly interface for querying real estate assets using natural language.
Advanced real estate and infrastructure asset intelligence platform.
"""

import json
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Asset Insight Graph",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
html, body, [class*='css'] { font-family: 'Inter', sans-serif; }
.sidebar .stButton>button { border-radius: 16px; background-color: #f5f5f5; color: #00285b; border: 1px solid #dde1e6; padding: 0.25rem 0.75rem; margin: 0.25rem 0.25rem 0.25rem 0; }
.main-header{font-size:1.2rem;font-weight:600;color:#00285b;text-align:left;margin-bottom:0.5rem;}
.response-highlight{background:#f5f7fa;padding:1rem;border-radius:4px;margin-bottom:0.5rem;}
.sidebar .stButton>button:hover { background-color: #00285b; color: #ffffff; }
</style>
""",
    unsafe_allow_html=True,
)


class AssetInsightGraphUI:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.example_questions = [
            "Portfolio distribution by region",
            "Properties in Texas that are ESG friendly",
            "Assets within 100km of Los Angeles",
            "How many infrastructure assets",
            "Sustainable renewable energy projects",
            "Mixed use properties in California",
            "Real estate assets",
            "Properties similar to The Independent",
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
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"API Error: {str(e)}"}

    def render_header(self):
        """Render the main header."""
        st.markdown(
            '<div class="main-header">🏢 Asset Insight Graph</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            "**Ask questions about your assets in natural language and get intelligent insights backed by Neo4j knowledge graphs.**"
        )

    def render_sidebar(self):
        """Render the sidebar with example questions and info."""
        with st.sidebar:
            st.markdown("### Example Questions")
            st.markdown("Click any example to try it:")
            
            for i, question in enumerate(self.example_questions):
                if st.button(f"💭 {question}", key=f"ex_{i}", use_container_width=True):
                    st.session_state.pending_question = question

            st.divider()
            if st.button("Clear Conversation"):
                st.session_state.chat_history = []
                st.rerun()

            with st.expander("Developer Info"):
                st.markdown("#### System Status")
                api_status = self.check_api_health()
                if api_status:
                    st.success("API Online")
                else:
                    st.error("API Offline")
                    st.markdown("Start the API with: `python -m api.main`")

                st.markdown("#### Architecture")
                st.markdown(
                    """
                - Guardrails → Planner → Tool Selection → Predefined Cypher
                - Text2Cypher → Summarizer
                """
                )

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
            results_count = (
                len(results_data)
                if results_data and isinstance(results_data, list)
                else 0
            )

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
                    mime="text/csv",
                    key=f"download_csv_{int(time.time() * 1000000)}",  # Unique key
                )

    def render_cypher_details(self, response_data: Dict[str, Any]):
        """Render Cypher query details in an expandable section."""
        with st.expander("🔍 Technical Details", expanded=False):
            if "cypher" in response_data:
                st.markdown("**Generated Cypher Query:**")
                # Format Cypher query for better readability
                cypher = response_data["cypher"]
                if cypher:
                    # Clean up whitespace and add proper formatting
                    formatted_cypher = self.format_cypher_query(cypher)
                    st.code(formatted_cypher, language="sql")
                else:
                    st.code("No Cypher query generated", language="text")
            
            # Show search type information
            if response_data.get("vector_search"):
                st.markdown("**Search Type:** 🧠 Vector Similarity Search")
                st.markdown("**Model:** OpenAI text-embedding-3-small (1536 dimensions)")
                st.markdown("**Similarity Function:** Cosine similarity")
            elif response_data.get("pattern_matched"):
                st.markdown("**Search Type:** 📊 Pattern-Based Graph Query")
                st.markdown("**Engine:** Neo4j Cypher with geospatial indexing")
            
            # Show query processing time if available
            if "search_type" in response_data:
                st.markdown(f"**Search Strategy:** {response_data['search_type'].replace('_', ' ').title()}")
    
    def format_cypher_query(self, cypher: str) -> str:
        """Format Cypher query for better readability."""
        if not cypher or cypher.strip() == "":
            return "No query generated"
        
        # Basic Cypher formatting
        formatted = cypher.strip()
        
        # Add line breaks after major clauses
        major_clauses = ['MATCH', 'WHERE', 'WITH', 'RETURN', 'ORDER BY', 'LIMIT', 'CALL']
        for clause in major_clauses:
            formatted = formatted.replace(f' {clause} ', f'\n{clause} ')
            formatted = formatted.replace(f'\n{clause}', f'\n{clause}')
        
        # Indent continuation lines
        lines = formatted.split('\n')
        formatted_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                # First line or lines starting with major clauses don't get indented
                if i == 0 or any(line.startswith(clause) for clause in major_clauses):
                    formatted_lines.append(line)
                else:
                    # Indent continuation lines
                    formatted_lines.append(f"  {line}")
        
        return '\n'.join(formatted_lines)

    def render_data_visualization(self, response_data: Dict[str, Any]):
        """Create visualizations from the query results."""
        # Handle both 'data' and 'results' field names
        results_data = response_data.get("data") or response_data.get("results")
        if (
            not results_data
            or not isinstance(results_data, list)
            or len(results_data) == 0
        ):
            return  # Skip visualization if no data

        try:
            df = pd.DataFrame(results_data)

            # Only render charts for queries that specifically need visualization
            # Portfolio distribution with both platform and region
            if (
                "platform" in df.columns
                and "region" in df.columns
                and "asset_count" in df.columns
            ):
                st.markdown("### 📊 Portfolio Distribution")

                # Group by platform to get totals
                platform_totals = (
                    df.groupby("platform")["asset_count"].sum().reset_index()
                )

                if len(platform_totals) > 0:
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = px.bar(
                            platform_totals,
                            x="platform",
                            y="asset_count",
                            title="By Platform",
                            color="asset_count",
                            color_continuous_scale="Blues",
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        # Group by region to get totals
                        region_totals = (
                            df.groupby("region")["asset_count"].sum().reset_index()
                        )
                        if len(region_totals) > 0:
                            fig2 = px.pie(
                                region_totals,
                                names="region",
                                values="asset_count",
                                title="By Region",
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
                    hover_data=(
                        ["distance_miles"] if "distance_miles" in df.columns else None
                    ),
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
            st.markdown("</div>", unsafe_allow_html=True)

        # 2. QUERY RESULTS (visible by default)
        self.render_query_results(response_data)

        # 3. COMPACT METRICS (one clean row)
        self.render_compact_metrics(response_data)

        # 4. DATA VISUALIZATION (if available)
        self.render_data_visualization(response_data)

        # 5. TECHNICAL DETAILS (collapsed by default)
        self.render_cypher_details(response_data)

    def run(self):
        """Main application runner using chat UI."""
        self.render_header()
        self.render_sidebar()

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "pending_question" not in st.session_state:
            st.session_state.pending_question = None

        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    self.render_response(msg["content"])

        prompt = st.chat_input("Ask about your portfolio…")
        if prompt or st.session_state.pending_question:
            question = prompt or st.session_state.pending_question
            st.session_state.pending_question = None

            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.spinner("Thinking..."):
                response_data = self.query_api(question)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": response_data}
            )
            st.rerun()


# Main application
def main():
    app = AssetInsightGraphUI()
    app.run()


if __name__ == "__main__":    main()
