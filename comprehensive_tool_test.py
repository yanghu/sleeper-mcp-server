#!/usr/bin/env python3
"""
Comprehensive test of all 14 tools to identify server errors
"""
import requests
import json
import time
from typing import Dict, Any

class ComprehensiveToolTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.results = {}
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool and return result with timing info"""
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.base_url}/tools/{tool_name}",
                json={"arguments": arguments},
                timeout=30
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "duration": duration,
                    "result": result,
                    "tool_name": tool_name,
                    "arguments": arguments
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "duration": duration,
                    "error": response.text,
                    "tool_name": tool_name,
                    "arguments": arguments
                }
                
        except Exception as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "status_code": None,
                "duration": duration,
                "error": str(e),
                "tool_name": tool_name,
                "arguments": arguments
            }
    
    def test_all_tools(self):
        """Test all 14 tools systematically"""
        print("🧪 Starting Comprehensive Tool Testing")
        print("=" * 50)
        
        # Test 1: get_user_leagues
        print("\n1️⃣ Testing get_user_leagues...")
        result = self.call_tool("get_user_leagues", {
            "username": "huyang",
            "season": "2025"
        })
        self.results["get_user_leagues"] = result
        self.print_result(result)
        
        # Extract league data for subsequent tests
        league_id = None
        if result["success"] and "result" in result["result"]:
            leagues = result["result"]["result"].get("leagues", [])
            if leagues:
                league_id = leagues[0].get("id")
                print(f"   📝 Using league_id: {league_id}")
        
        # Test 2: get_league_info
        print("\n2️⃣ Testing get_league_info...")
        if league_id:
            result = self.call_tool("get_league_info", {"league_id": league_id})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["get_league_info"] = result
        self.print_result(result)
        
        # Test 3: get_league_rosters
        print("\n3️⃣ Testing get_league_rosters...")
        if league_id:
            result = self.call_tool("get_league_rosters", {"league_id": league_id})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["get_league_rosters"] = result
        self.print_result(result)
        
        # Test 4: get_league_rosters_with_draft_info
        print("\n4️⃣ Testing get_league_rosters_with_draft_info...")
        if league_id:
            result = self.call_tool("get_league_rosters_with_draft_info", {"league_id": league_id})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["get_league_rosters_with_draft_info"] = result
        self.print_result(result)
        
        # Test 5: get_league_users
        print("\n5️⃣ Testing get_league_users...")
        if league_id:
            result = self.call_tool("get_league_users", {"league_id": league_id})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["get_league_users"] = result
        self.print_result(result)
        
        # Test 6: get_roster_user_mapping
        print("\n6️⃣ Testing get_roster_user_mapping...")
        if league_id:
            result = self.call_tool("get_roster_user_mapping", {"league_id": league_id})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["get_roster_user_mapping"] = result
        self.print_result(result)
        
        # Test 7: get_league_draft
        print("\n7️⃣ Testing get_league_draft...")
        if league_id:
            result = self.call_tool("get_league_draft", {"league_id": league_id})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["get_league_draft"] = result
        self.print_result(result)
        
        # Test 8: search_players
        print("\n8️⃣ Testing search_players...")
        result = self.call_tool("search_players", {"query": "Patrick Mahomes"})
        self.results["search_players"] = result
        self.print_result(result)
        
        # Test 9: get_trending_players
        print("\n9️⃣ Testing get_trending_players...")
        result = self.call_tool("get_trending_players", {"sport": "nfl", "add_drop": "add"})
        self.results["get_trending_players"] = result
        self.print_result(result)
        
        # Test 10: get_player_stats
        print("\n🔟 Testing get_player_stats...")
        result = self.call_tool("get_player_stats", {"player_id": "4046", "season": "2024"})
        self.results["get_player_stats"] = result
        self.print_result(result)
        
        # Test 11: get_matchups
        print("\n1️⃣1️⃣ Testing get_matchups...")
        if league_id:
            result = self.call_tool("get_matchups", {"league_id": league_id, "week": 1})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["get_matchups"] = result
        self.print_result(result)
        
        # Test 12: get_matchup_scores
        print("\n1️⃣2️⃣ Testing get_matchup_scores...")
        if league_id:
            result = self.call_tool("get_matchup_scores", {"league_id": league_id, "week": 1})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["get_matchup_scores"] = result
        self.print_result(result)
        
        # Test 13: analyze_trade_targets (needs roster_id)
        print("\n1️⃣3️⃣ Testing analyze_trade_targets...")
        if league_id:
            result = self.call_tool("analyze_trade_targets", {"league_id": league_id, "roster_id": 1})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["analyze_trade_targets"] = result
        self.print_result(result)
        
        # Test 14: evaluate_roster_needs (needs roster_id)
        print("\n1️⃣4️⃣ Testing evaluate_roster_needs...")
        if league_id:
            result = self.call_tool("evaluate_roster_needs", {"league_id": league_id, "roster_id": 1})
        else:
            result = {"success": False, "error": "No league_id available", "skipped": True}
        self.results["evaluate_roster_needs"] = result
        self.print_result(result)
        
        # Summary
        self.print_summary()
    
    def print_result(self, result: Dict[str, Any]):
        """Print formatted result"""
        if result.get("skipped"):
            print("   ⏭️ SKIPPED")
            return
            
        if result["success"]:
            print(f"   ✅ SUCCESS ({result['duration']:.2f}s)")
        else:
            print(f"   ❌ FAILED ({result.get('duration', 0):.2f}s)")
            print(f"      Status: {result.get('status_code', 'N/A')}")
            print(f"      Error: {result.get('error', 'Unknown')}"[:100])
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.results)
        successful = len([r for r in self.results.values() if r["success"]])
        failed = len([r for r in self.results.values() if not r["success"] and not r.get("skipped")])
        skipped = len([r for r in self.results.values() if r.get("skipped")])
        
        print(f"Total tests: {total_tests}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️ Skipped: {skipped}")
        
        print("\n📋 FAILED TESTS:")
        for tool_name, result in self.results.items():
            if not result["success"] and not result.get("skipped"):
                print(f"  • {tool_name}: {result.get('error', 'Unknown error')}"[:80])
        
        # Save detailed results
        with open("comprehensive_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved to comprehensive_test_results.json")

if __name__ == "__main__":
    tester = ComprehensiveToolTester()
    tester.test_all_tools()
