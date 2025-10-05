from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from dotenv import load_dotenv
import os


load_dotenv()
mcp_gateway_url = os.getenv("MCP_GATEWAY_URL")

# Point this to your MCP Gateway host and port (typically exposed by docker-compose)
connection_params = SseConnectionParams(url=mcp_gateway_url)

# Create the MCP toolset for your agent to use MCP tools exposed by your MCP server
medical_toolset = MCPToolset(connection_params=connection_params)




