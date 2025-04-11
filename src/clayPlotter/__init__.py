# src/clayPlotter/__init__.py
"""
ClayPlotter Package

A library for creating choropleth maps, with an accompanying MCP server.
"""

# Import version information
from .__version__ import __version__

# Import core components from the L1 submodule
from .l1_choropleth import ChoroplethPlotter, DataLoader, GeoDataManager

# Define what is available for public import
__all__ = [
    "__version__",
    "ChoroplethPlotter",
    "DataLoader",
    "GeoDataManager",
]

# Note: The MCP server components are typically not imported here,
# as the server is run as a separate application (e.g., via `python -m clayPlotter.mcp.main`).