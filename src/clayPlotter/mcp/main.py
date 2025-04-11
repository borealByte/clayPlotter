# src/clayPlotter/mcp/main.py
import logging
import sys
from pathlib import Path

# Ensure the package root is in the Python path for relative imports
# This might be necessary if running the script directly during development
project_root = Path(__file__).resolve().parents[3] # Adjust depth if structure changes
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the FastAPI app for tests
from .api import app

# Define dummy classes for when MCP server is not available
class DummyServerInfo:
    def __init__(self, name, version, description, author, contact):
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.contact = contact

class DummyToolDefinition:
    def __init__(self, name, description, input_model, output_model, handler):
        self.name = name
        self.description = description
        self.input_model = input_model
        self.output_model = output_model
        self.handler = handler

class DummyFastMCP:
    def __init__(self, name=None):
        self.name = name or "dummy-mcp"
        self.tools = []
    
    def tool(self, name=None, description=None):
        def decorator(func):
            self.tools.append({
                "name": name or func.__name__,
                "description": description or func.__doc__ or "",
                "handler": func
            })
            return func
        return decorator
    
    def run(self):
        print("Dummy MCP server running")

# Set default classes
MCPServer = DummyFastMCP
ServerInfo = DummyServerInfo
ToolDefinition = DummyToolDefinition

# Import MCP server components and local modules if available
try:
    import mcp
    print("Successfully imported mcp")
    try:
        import mcp.server
        print("Successfully imported mcp.server")
        try:
            from mcp.server import Server as MCPServer
            print("Successfully imported Server from mcp.server")
            try:
                from mcp.server.fastmcp import FastMCP
                from mcp.server.fastmcp.tools.base import Tool
                print("Successfully imported FastMCP and Tool")
            except ImportError as e:
                print(f"Error importing from mcp.server.models: {e}")
                if __name__ == "__main__":  # Only exit if running as script
                    sys.exit(1)
        except ImportError as e:
            print(f"Error importing Server from mcp.server: {e}")
            if __name__ == "__main__":  # Only exit if running as script
                sys.exit(1)
    except ImportError as e:
        print(f"Error importing mcp.server: {e}")
        if __name__ == "__main__":  # Only exit if running as script
            sys.exit(1)
except ImportError as e:
    print(f"Error importing mcp: {e}")
    if __name__ == "__main__":  # Only exit if running as script
        sys.exit(1)

# Import local services and models using relative paths
from .config import settings
from .services.map_service import MapService
from .services.config_service import ConfigService
from .models.request_models import GenerateMapRequest
from .models.response_models import GenerateMapResponse, ListGeographiesResponse

# Configure logging (basic setup, might inherit from config)
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Tool Implementations ---

# Instantiate services
map_service = MapService()
config_service = ConfigService()

def generate_map_tool(request: GenerateMapRequest) -> GenerateMapResponse:
    """MCP Tool: Generates a choropleth map."""
    logger.info(f"Executing generate_map tool for geography: {request.geography_key}")
    response = map_service.generate_map_from_request(request)
    logger.info(f"generate_map tool execution finished. Success: {response.success}")
    return response

def list_geographies_tool() -> ListGeographiesResponse:
    """MCP Tool: Lists available geography configurations."""
    logger.info("Executing list_geographies tool.")
    response = config_service.list_available_geographies()
    logger.info(f"list_geographies tool execution finished. Success: {response.success}")
    return response

# --- Server Definition ---

server_info = {
    "name": "clayplotter-mcp",
    "version": settings.APP_VERSION,
    "description": "MCP Server for generating choropleth maps using the clayPlotter library.",
    "author": "Clay", # Replace with actual author/team
    "contact": "clay@example.com" # Replace with actual contact
}

# Create the MCP server instance
if MCPServer == DummyFastMCP:
    server = MCPServer(name=server_info["name"])
else:
    # For the real MCP server, we use FastMCP
    server = FastMCP(name=server_info["name"])

# Register tools using decorators
@server.tool(
    name="generate_map",
    description="Generates a choropleth map for a specified geography using provided data. Optionally saves the map to a file."
)
def generate_map_tool_wrapper(request: GenerateMapRequest) -> GenerateMapResponse:
    """Wrapper for generate_map_tool to use with FastMCP."""
    return generate_map_tool(request)

@server.tool(
    name="list_geographies",
    description="Lists the available geography keys (based on configuration files) that can be used with the generate_map tool."
)
def list_geographies_tool_wrapper() -> ListGeographiesResponse:
    """Wrapper for list_geographies_tool to use with FastMCP."""
    return list_geographies_tool()

# --- Main Execution ---
if __name__ == "__main__":
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    # The MCPServer library likely handles its own run loop based on stdio
    try:
        server.run() # Start the server listening on stdio
    except Exception as e:
        logger.critical(f"MCP Server failed to run: {e}", exc_info=True)
        sys.exit(1)
    logger.info("MCP Server stopped.")
else:
    # When imported (not run as script), log that we're in module mode
    logger.info("clayPlotter MCP module imported.")