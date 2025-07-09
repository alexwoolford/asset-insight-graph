"""Generate diagrams for the multi-tool workflow."""
from api.multi_agent import get_multi_agent_workflow

workflow = get_multi_agent_workflow()
# LangGraph provides draw_mermaid_png() and draw_mermaid() helpers
workflow.get_graph().draw_mermaid_png("docs/multi_tool_workflow.png")
print("Diagram saved to docs/multi_tool_workflow.png")
