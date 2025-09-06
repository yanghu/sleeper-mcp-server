#!/usr/bin/env python3
"""
Schema discovery script for Sleeper MCP server tools.
This script queries actual tools to understand their real output schemas.
"""

import json
import requests
import sys
from typing import Dict, Any, List

# Server configuration
SERVER_URL = "http://localhost:8000"

def query_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Query a tool and return its response."""
    try:
        response = requests.post(
            f"{SERVER_URL}/tools/{tool_name}",
            json={"arguments": arguments},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Exception: {str(e)}"}

def analyze_schema(data: Any, path: str = "") -> Dict[str, str]:
    """Recursively analyze data structure to understand schema."""
    schema = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(value, (dict, list)) and value:
                # Recursively analyze nested structures
                nested_schema = analyze_schema(value, current_path)
                schema.update(nested_schema)
            else:
                # Record the type of this field
                value_type = type(value).__name__
                if value is None:
                    value_type = "null"
                schema[current_path] = value_type
                
    elif isinstance(data, list) and data:
        # Analyze first item in list to understand structure
        if data:
            list_schema = analyze_schema(data[0], f"{path}[0]")
            schema.update(list_schema)
            schema[f"{path}.__length__"] = str(len(data))
    
    return schema

def discover_tool_schemas():
    """Discover actual schemas by querying tools with different test cases."""
    print("🔍 Discovering actual tool output schemas...")
    print(f"Server URL: {SERVER_URL}")
    
    # Test cases - using a mix of likely working and failing cases
    test_cases = [
        # Tools that might work with real data
        ("get_user_leagues", {"username": "sleeper"}),  # Official Sleeper account
        ("search_players", {"query": "Josh Allen"}),     # Common player
        ("get_trending_players", {"sport": "nfl", "add_drop": "add"}),  # Should work
        
        # Tools that will likely fail but show error structure
        ("get_league_info", {"league_id": "123456789"}),
        ("get_league_rosters", {"league_id": "123456789"}),
        ("get_league_users", {"league_id": "123456789"}),
        ("get_player_stats", {"player_id": "4984", "season": "2023"}),  # Josh Allen QB
        ("get_matchups", {"league_id": "123456789", "week": 1}),
        
        # More complex tools
        ("analyze_trade_targets", {"league_id": "123456789", "roster_id": 1}),
        ("evaluate_roster_needs", {"league_id": "123456789", "roster_id": 1}),
    ]
    
    schemas = {}
    
    for tool_name, arguments in test_cases:
        print(f"\n📊 Analyzing {tool_name}...")
        
        response = query_tool(tool_name, arguments)
        
        if "error" in response and response["error"] and "HTTP" in str(response["error"]):
            print(f"   ❌ HTTP Error: {response['error']}")
            continue
            
        # Analyze the response structure
        schema = analyze_schema(response)
        schemas[tool_name] = {
            "arguments": arguments,
            "response": response,
            "schema": schema,
            "success": response.get("success", False)
        }
        
        # Print key findings
        if response.get("success"):
            print(f"   ✅ Success - Result type: {type(response.get('result', {})).__name__}")
            if "result" in response:
                result = response["result"]
                if isinstance(result, dict):
                    print(f"      Keys: {list(result.keys())}")
                elif isinstance(result, list):
                    print(f"      List length: {len(result)}")
                    if result:
                        print(f"      First item keys: {list(result[0].keys()) if isinstance(result[0], dict) else 'Not a dict'}")
        else:
            error_msg = response.get("error", "Unknown error")
            print(f"   ❌ Failed: {error_msg}")
    
    # Save detailed schemas
    with open("discovered_schemas.json", "w") as f:
        json.dump(schemas, f, indent=2, default=str)
    
    print(f"\n📄 Detailed schemas saved to: discovered_schemas.json")
    
    # Generate summary
    print(f"\n📋 SCHEMA DISCOVERY SUMMARY")
    print(f"=" * 50)
    
    successful_tools = [name for name, data in schemas.items() if data.get("success")]
    failed_tools = [name for name, data in schemas.items() if not data.get("success")]
    
    print(f"✅ Successful tools ({len(successful_tools)}):")
    for tool_name in successful_tools:
        result = schemas[tool_name]["response"].get("result", {})
        if isinstance(result, dict):
            main_keys = [k for k in result.keys() if not k.startswith('_')]
            print(f"   - {tool_name}: {main_keys}")
        else:
            print(f"   - {tool_name}: {type(result).__name__}")
    
    print(f"\n❌ Failed tools ({len(failed_tools)}):")
    for tool_name in failed_tools:
        error = schemas[tool_name]["response"].get("error", "Unknown")
        print(f"   - {tool_name}: {error}")
    
    return schemas

def generate_validation_expectations(schemas: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Generate validation expectations based on discovered schemas."""
    expectations = {}
    
    for tool_name, data in schemas.items():
        if not data.get("success"):
            continue
            
        result = data["response"].get("result", {})
        expectation = {"type": type(result).__name__}
        
        if isinstance(result, dict):
            expectation["required_fields"] = list(result.keys())
            expectation["field_types"] = {k: type(v).__name__ for k, v in result.items()}
        elif isinstance(result, list) and result:
            expectation["list_item_type"] = type(result[0]).__name__
            if isinstance(result[0], dict):
                expectation["item_required_fields"] = list(result[0].keys())
        
        expectations[tool_name] = expectation
    
    return expectations

if __name__ == "__main__":
    schemas = discover_tool_schemas()
    expectations = generate_validation_expectations(schemas)
    
    # Save expectations for use in validation script
    with open("validation_expectations.json", "w") as f:
        json.dump(expectations, f, indent=2, default=str)
    
    print(f"\n📋 Validation expectations saved to: validation_expectations.json")
    print(f"\nUse these expectations to create accurate validation tests!")
