import sys
import os
import pytest

def test_mcp_import():
    # Print Python path and current working directory for debugging
    print("\nPython path:", sys.path)
    print("Current working directory:", os.getcwd())

    # Test importing mcp
    import mcp
    assert mcp is not None, "mcp module should be importable"
    print("mcp.__file__:", mcp.__file__)
    
    # Test if mcp has a server attribute
    has_server_attr = hasattr(mcp, 'server')
    print("hasattr(mcp, 'server'):", has_server_attr)
    assert has_server_attr, "mcp should have a server attribute"
    
    # Test if mcp has a __path__ attribute (indicating it's a package)
    has_path_attr = hasattr(mcp, '__path__')
    print("hasattr(mcp, '__path__'):", has_path_attr)
    assert has_path_attr, "mcp should have a __path__ attribute"
    
    if has_path_attr:
        print("mcp.__path__:", mcp.__path__)
    
    # Check if the server module exists in the mcp package directory
    if hasattr(mcp, '__file__'):
        mcp_dir = os.path.dirname(mcp.__file__)
        print("Contents of mcp directory:")
        dir_contents = os.listdir(mcp_dir)
        for item in dir_contents:
            print(f"  {item}")
        
        assert 'server' in dir_contents, "server directory should exist in mcp package"
        
        if 'server' in dir_contents:
            server_dir = os.path.join(mcp_dir, 'server')
            print(f"    Contents of {server_dir}:")
            server_contents = os.listdir(server_dir)
            for subitem in server_contents:
                print(f"      {subitem}")
    
    # Test importing mcp.server
    import mcp.server
    assert mcp.server is not None, "mcp.server module should be importable"
    print("mcp.server.__file__:", mcp.server.__file__)