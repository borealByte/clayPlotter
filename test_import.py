import sys
print("Python path:", sys.path)

try:
    import mcp
    print("mcp imported successfully")
    print("mcp.__file__:", mcp.__file__)
    print("dir(mcp):", dir(mcp))
    
    try:
        import mcp.server
        print("mcp.server imported successfully")
        print("mcp.server.__file__:", mcp.server.__file__)
        print("dir(mcp.server):", dir(mcp.server))
    except ImportError as e:
        print("Failed to import mcp.server:", e)
except ImportError as e:
    print("Failed to import mcp:", e)