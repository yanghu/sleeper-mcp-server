#!/usr/bin/env python3
"""
Improved regression test suite with better test data that should return actual results.
This version uses known good data sources to ensure we get meaningful test results.
"""

import json
import requests
import sys
import os
from typing import Dict, Any, List
import jsonschema
from jsonschema import validate, ValidationError

# Add the project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

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
        output_schema = tool_schema.get("outputSchema", {})
        issues = validate_response_against_schema(response_data, output_schema, tool_name)
        
        success = len(issues) == 0
        
        # Check if we got meaningful data
        data_quality = check_data_quality(tool_name, response_data.get("result", {}))
        
        return {
            "tool": tool_name,
            "success": success,
            "response_data": response_data,
            "expected_schema": output_schema,
            "issues": issues,
            "data_quality": data_quality
        }
        
    except Exception as e:
        return {
            "tool": tool_name,
            "success": False,
            "error": str(e),
            "issues": [f"Exception during testing: {e}"],
            "data_quality": {"has_data": False, "reason": f"Exception: {e}"}
        }

def check_data_quality(tool_name: str, result_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check if the tool returned meaningful data."""
    if not result_data:
        return {"has_data": False, "reason": "No result data"}
    
    # Define what constitutes meaningful data for each tool
    quality_checks = {
        'get_user_leagues': lambda r: len(r.get('leagues', [])) > 0,
        'get_league_info': lambda r: r.get('league_id') is not None,
        'get_league_rosters': lambda r: len(r.get('rosters', [])) > 0,
        'get_league_rosters_with_draft_info': lambda r: len(r.get('rosters', [])) > 0,
        'get_league_users': lambda r: len(r.get('users', [])) > 0,
        'get_roster_user_mapping': lambda r: len(r.get('mappings', [])) > 0,
        'get_league_draft': lambda r: len(r.get('picks', [])) > 0,
        'search_players': lambda r: len(r.get('players', [])) > 0,
        'get_trending_players': lambda r: len(r.get('players', [])) > 0,
        'get_player_stats': lambda r: len(r.get('stats', {})) > 0,
        'get_matchups': lambda r: len(r.get('matchups', [])) > 0,
        'get_matchup_scores': lambda r: len(r.get('matchups', [])) > 0,
        'analyze_trade_targets': lambda r: len(r.get('target_teams', [])) > 0 or len(r.get('suggested_trades', [])) > 0,
        'evaluate_roster_needs': lambda r: len(r.get('strengths', [])) > 0 or len(r.get('weaknesses', [])) > 0
    }
    
    if tool_name in quality_checks:
        has_data = quality_checks[tool_name](result_data)
        return {
            "has_data": has_data,
            "reason": "Has meaningful data" if has_data else "Empty or minimal data returned"
        }
    
    return {"has_data": True, "reason": "No specific quality check defined"}

def run_improved_regression_tests(verbose: bool = False) -> bool:
    """Run improved regression tests with better test data."""
    print("🚀 Running Improved Sleeper MCP Server Regression Tests...")
    print(f"Server URL: {SERVER_URL}")
    
    # Check server health
    try:
        health_response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if health_response.status_code != 200:
            print(f"❌ Server health check failed: HTTP {health_response.status_code}")
            return False
        print("✅ Server health check passed")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    # Get official tool schemas
    if verbose:
        print("\n📋 Getting official tool schemas from /tools endpoint...")
    official_schemas = get_official_tool_schemas()
    
    if verbose:
        print(f"Found {len(official_schemas)} tools with schemas")
    
    # Improved test cases with better data that should return results
    test_cases = [
        # Use known active Sleeper users
        ("get_user_leagues", {"username": "sleeper", "season": "2024"}),
        ("get_user_leagues", {"username": "fantasyfootball", "season": "2024"}),
        
        # Use well-known NFL players
        ("search_players", {"query": "Josh Allen", "position": "QB"}),
        ("search_players", {"query": "Cooper Kupp", "position": "WR"}),
        ("search_players", {"query": "Travis Kelce", "position": "TE"}),
        ("search_players", {"query": "Christian McCaffrey", "position": "RB"}),
        
        # Get trending players (should work)
        ("get_trending_players", {"sport": "nfl", "add_drop": "add"}),
        ("get_trending_players", {"sport": "nfl", "add_drop": "drop"}),
        
        # Get player stats for known players (2024 season)
        ("get_player_stats", {"player_id": "4984", "season": "2024"}),  # Josh Allen
        ("get_player_stats", {"player_id": "4034", "season": "2024"}),  # Cooper Kupp
        ("get_player_stats", {"player_id": "4035", "season": "2024"}),  # Travis Kelce
        ("get_player_stats", {"player_id": "4037", "season": "2024"}),  # Christian McCaffrey
        
        # Note: League-based tools will likely fail with fake IDs, but we'll test them anyway
        # to ensure proper error handling
        ("get_league_info", {"league_id": "123456789012345678"}),
        ("get_league_rosters", {"league_id": "123456789012345678"}),
        ("get_league_rosters_with_draft_info", {"league_id": "123456789012345678"}),
        ("get_league_users", {"league_id": "123456789012345678"}),
        ("get_roster_user_mapping", {"league_id": "123456789012345678"}),
        ("get_league_draft", {"league_id": "123456789012345678"}),
        ("get_matchups", {"league_id": "123456789012345678", "week": 1}),
        ("get_matchup_scores", {"league_id": "123456789012345678", "week": 1}),
        ("analyze_trade_targets", {"league_id": "123456789012345678", "roster_id": 1}),
        ("evaluate_roster_needs", {"league_id": "123456789012345678", "roster_id": 1})
    ]
    
    results = []
    passed = 0
    failed = 0
    no_schema = 0
    meaningful_data = 0
    empty_data = 0
    
    # Test each tool against its declared schema
    for tool_name, test_arguments in test_cases:
        if tool_name not in official_schemas:
            if verbose:
                print(f"⚠️  {tool_name}: Tool not found in official schema list")
            continue
        
        tool_schema = official_schemas[tool_name]
        result = test_tool_against_schema(tool_name, tool_schema, test_arguments)
        results.append(result)
        
        if not tool_schema.get("outputSchema"):
            no_schema += 1
        elif result["success"]:
            passed += 1
            if result["data_quality"]["has_data"]:
                meaningful_data += 1
                if verbose:
                    print(f"✅ {tool_name}: PASSED (with data)")
            else:
                empty_data += 1
                if verbose:
                    print(f"⚠️  {tool_name}: PASSED (empty data)")
        else:
            failed += 1
            if verbose:
                print(f"❌ {tool_name}: FAILED")
                for issue in result["issues"]:
                    print(f"   - {issue}")
    
    # Print summary
    print(f"\n📊 IMPROVED REGRESSION TEST SUMMARY")
    print(f"=" * 60)
    print(f"Total tools tested: {len(test_cases)}")
    print(f"✅ Passed (schema match): {passed}")
    print(f"❌ Failed (schema mismatch): {failed}")
    print(f"⚠️  No output schema defined: {no_schema}")
    print(f"📈 Meaningful data returned: {meaningful_data}")
    print(f"📉 Empty data returned: {empty_data}")
    
    if passed + failed > 0:
        success_rate = (passed / (passed + failed)) * 100
        print(f"Schema success rate: {success_rate:.1f}%")
    
    if passed > 0:
        data_quality_rate = (meaningful_data / passed) * 100
        print(f"Data quality rate: {data_quality_rate:.1f}%")
    
    # Print detailed results
    if verbose:
        print(f"\n🔍 DETAILED RESULTS")
        print(f"=" * 60)
        for result in results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            data_status = "📈 DATA" if result["data_quality"]["has_data"] else "📉 EMPTY"
            print(f"{status} {data_status} {result['tool']}")
            if not result["success"] and result["issues"]:
                for issue in result["issues"]:
                    print(f"   - {issue}")
            elif not result["data_quality"]["has_data"]:
                print(f"   - {result['data_quality']['reason']}")
    
    # Save results for debugging
    timestamp = __import__("datetime").datetime.now().isoformat()
    results_file = f"improved_regression_results_{timestamp.split('T')[0]}.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "server_url": SERVER_URL,
            "summary": {
                "total": len(test_cases),
                "passed": passed,
                "failed": failed,
                "no_schema": no_schema,
                "meaningful_data": meaningful_data,
                "empty_data": empty_data,
                "success_rate": (passed / (passed + failed)) * 100 if passed + failed > 0 else 0,
                "data_quality_rate": (meaningful_data / passed) * 100 if passed > 0 else 0
            },
            "results": results
        }, f, indent=2, default=str)
    
    if verbose:
        print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Return success status (consider both schema validation and data quality)
    return failed == 0 and meaningful_data > 0

def main():
    """Main entry point for improved regression testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run improved Sleeper MCP Server regression tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--server", "-s", default="http://localhost:8000", help="Server URL")
    
    args = parser.parse_args()
    
    global SERVER_URL
    SERVER_URL = args.server
    
    success = run_improved_regression_tests(verbose=args.verbose)
    
    if success:
        print("\n🎉 All improved regression tests passed with meaningful data!")
        sys.exit(0)
    else:
        print("\n💥 Some improved regression tests failed or returned empty data!")
        sys.exit(1)

if __name__ == "__main__":
    main()
