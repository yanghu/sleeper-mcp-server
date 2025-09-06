#!/usr/bin/env python3
"""
Schema-based validation for Sleeper MCP server tools.
This script queries /tools endpoint to get official schemas, then validates actual responses against them.
"""

import json
import requests
import sys
from typing import Dict, Any, List
import jsonschema
from jsonschema import validate, ValidationError

# Server configuration
SERVER_URL = "http://localhost:8000"

def get_official_tool_schemas() -> Dict[str, Dict[str, Any]]:
    """Get official tool schemas from the /tools endpoint."""
    try:
        response = requests.get(f"{SERVER_URL}/tools", timeout=10)
        if response.status_code != 200:
            raise Exception(f"Failed to get tools: HTTP {response.status_code}")
        
        tools_data = response.json()
        tools = tools_data.get("tools", [])
        
        schemas = {}
        for tool in tools:
            tool_name = tool.get("name")
            if tool_name:
                schemas[tool_name] = {
                    "name": tool_name,
                    "description": tool.get("description", ""),
                    "inputSchema": tool.get("inputSchema", {}),
                    "outputSchema": tool.get("outputSchema", {})
                }
        
        return schemas
    except Exception as e:
        print(f"❌ Failed to get tool schemas: {e}")
        sys.exit(1)

def validate_response_against_schema(response_data: Dict[str, Any], expected_schema: Dict[str, Any], tool_name: str) -> List[str]:
    """Validate a tool response against its declared output schema."""
    issues = []
    
    # Check basic response structure
    if not isinstance(response_data, dict):
        issues.append(f"{tool_name}: Response is not a JSON object")
        return issues
    
    # Check for required HTTP response fields
    required_fields = ["success", "tool_name", "arguments", "timestamp"]
    for field in required_fields:
        if field not in response_data:
            issues.append(f"{tool_name}: Missing required HTTP field '{field}'")
    
    # If not successful, check error structure
    if not response_data.get("success"):
        if "error" not in response_data or not response_data["error"]:
            issues.append(f"{tool_name}: Failed response missing error message")
        return issues
    
    # For successful responses, validate against output schema
    if "result" not in response_data:
        issues.append(f"{tool_name}: Successful response missing 'result' field")
        return issues
    
    result = response_data["result"]
    
    # Skip schema validation if no output schema is defined
    if not expected_schema or expected_schema == {}:
        issues.append(f"{tool_name}: No output schema defined - cannot validate structure")
        return issues
    
    # Validate result against JSON schema
    try:
        jsonschema.validate(result, expected_schema)
    except ValidationError as e:
        issues.append(f"{tool_name}: Schema validation failed - {e.message}")
        # Add more specific path information if available
        if e.absolute_path:
            path = " -> ".join(str(p) for p in e.absolute_path)
            issues.append(f"{tool_name}: Validation error at path: {path}")
    except Exception as e:
        issues.append(f"{tool_name}: Schema validation error - {str(e)}")
    
    return issues

def test_tool_against_schema(tool_name: str, tool_schema: Dict[str, Any], test_arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single tool against its declared schema."""
    print(f"\n🧪 Testing {tool_name} against declared schema...")
    
    # Show the expected output schema
    output_schema = tool_schema.get("outputSchema", {})
    if output_schema:
        print(f"   📋 Expected schema: {json.dumps(output_schema, indent=2)[:200]}...")
    else:
        print(f"   ⚠️  No output schema defined")
    
    try:
        # Make tool call
        response = requests.post(
            f"{SERVER_URL}/tools/{tool_name}",
            json={"arguments": test_arguments},
            timeout=10
        )
        
        if response.status_code != 200:
            return {
                "tool": tool_name,
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "issues": [f"HTTP request failed with status {response.status_code}"]
            }
        
        # Parse response
        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            return {
                "tool": tool_name,
                "success": False,
                "error": f"Invalid JSON response: {e}",
                "issues": ["Response is not valid JSON"]
            }
        
        # Validate against schema
        issues = validate_response_against_schema(response_data, output_schema, tool_name)
        
        success = len(issues) == 0
        
        result = {
            "tool": tool_name,
            "success": success,
            "response_data": response_data,
            "expected_schema": output_schema,
            "issues": issues
        }
        
        if success:
            print(f"✅ {tool_name}: PASSED - Response matches declared schema")
        else:
            print(f"❌ {tool_name}: FAILED - Schema validation issues:")
            for issue in issues:
                print(f"   - {issue}")
        
        return result
        
    except Exception as e:
        print(f"❌ {tool_name}: EXCEPTION - {e}")
        return {
            "tool": tool_name,
            "success": False,
            "error": str(e),
            "issues": [f"Exception during testing: {e}"]
        }

def main():
    """Run schema-based validation tests."""
    print("🚀 Starting schema-based validation...")
    print(f"Server URL: {SERVER_URL}")
    
    # Get official tool schemas
    print("\n📋 Getting official tool schemas from /tools endpoint...")
    official_schemas = get_official_tool_schemas()
    
    print(f"Found {len(official_schemas)} tools with schemas:")
    for tool_name, schema in official_schemas.items():
        has_output_schema = bool(schema.get("outputSchema"))
        status = "✅" if has_output_schema else "⚠️ "
        print(f"   {status} {tool_name}: {'Has output schema' if has_output_schema else 'No output schema'}")
    
    # Test cases - using simple test data that should work or fail gracefully
    test_cases = [
        ("get_user_leagues", {"username": "testuser123"}),
        ("get_league_info", {"league_id": "1234567890"}),
        ("get_league_rosters", {"league_id": "1234567890"}),
        ("get_league_rosters_with_draft_info", {"league_id": "1234567890"}),
        ("get_league_users", {"league_id": "1234567890"}),
        ("get_roster_user_mapping", {"league_id": "1234567890"}),
        ("get_league_draft", {"league_id": "1234567890"}),
        ("search_players", {"query": "Josh Allen"}),
        ("get_trending_players", {"sport": "nfl", "add_drop": "add"}),
        ("get_player_stats", {"player_id": "4984", "season": "2023"}),
        ("get_matchups", {"league_id": "1234567890", "week": 1}),
        ("get_matchup_scores", {"league_id": "1234567890", "week": 1}),
        ("analyze_trade_targets", {"league_id": "1234567890", "roster_id": 1}),
        ("evaluate_roster_needs", {"league_id": "1234567890", "roster_id": 1})
    ]
    
    results = []
    passed = 0
    failed = 0
    no_schema = 0
    
    # Test each tool against its declared schema
    for tool_name, test_arguments in test_cases:
        if tool_name not in official_schemas:
            print(f"\n⚠️  {tool_name}: Tool not found in official schema list")
            continue
        
        tool_schema = official_schemas[tool_name]
        result = test_tool_against_schema(tool_name, tool_schema, test_arguments)
        results.append(result)
        
        if not tool_schema.get("outputSchema"):
            no_schema += 1
        elif result["success"]:
            passed += 1
        else:
            failed += 1
    
    # Print summary
    print(f"\n📊 SCHEMA VALIDATION SUMMARY")
    print(f"=" * 50)
    print(f"Total tools tested: {len(test_cases)}")
    print(f"✅ Passed (matches schema): {passed}")
    print(f"❌ Failed (schema mismatch): {failed}")
    print(f"⚠️  No output schema defined: {no_schema}")
    
    if passed + failed > 0:
        success_rate = (passed / (passed + failed)) * 100
        print(f"Success rate (excluding no-schema): {success_rate:.1f}%")
    
    # Print detailed failures
    schema_failures = [r for r in results if not r["success"] and r["tool"] in official_schemas and official_schemas[r["tool"]].get("outputSchema")]
    if schema_failures:
        print(f"\n🔍 SCHEMA VALIDATION FAILURES")
        print(f"=" * 50)
        for result in schema_failures:
            print(f"\n❌ {result['tool']}:")
            for issue in result["issues"]:
                print(f"   - {issue}")
    
    # Print tools without output schemas
    no_schema_tools = [r["tool"] for r in results if r["tool"] in official_schemas and not official_schemas[r["tool"]].get("outputSchema")]
    if no_schema_tools:
        print(f"\n⚠️  TOOLS WITHOUT OUTPUT SCHEMAS")
        print(f"=" * 50)
        for tool_name in no_schema_tools:
            print(f"   - {tool_name}: No outputSchema defined in tool specification")
    
    # Save detailed results
    with open("schema_validation_results.json", "w") as f:
        json.dump({
            "official_schemas": official_schemas,
            "test_results": results,
            "summary": {
                "total": len(test_cases),
                "passed": passed,
                "failed": failed,
                "no_schema": no_schema
            }
        }, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: schema_validation_results.json")
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()

