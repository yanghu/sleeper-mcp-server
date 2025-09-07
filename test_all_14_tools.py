#!/usr/bin/env python3
"""
Comprehensive test script for all 14 tools in the Sleeper MCP server.
Tests each tool with appropriate parameters and validates responses.
"""

import requests
import json
import time
from typing import Dict, Any, List

class SleeperToolTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_data = {}
        
    def test_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single tool and return the response."""
        url = f"{self.base_url}/tools/{tool_name}"
        payload = {"arguments": arguments}
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def test_all_tools(self):
        """Test all 14 tools with appropriate parameters."""
        print("🧪 Testing all 14 Sleeper MCP Server tools...")
        print("=" * 60)
        
        # Test results storage
        results = {}
        
        # 1. get_user_leagues
        print("\n1️⃣ Testing get_user_leagues...")
        result = self.test_tool("get_user_leagues", {"username": "huyang", "season": "2025"})
        results["get_user_leagues"] = result
        if result.get("success"):
            leagues = result.get("result", {}).get("leagues", [])
            if leagues:
                self.test_data["league_id"] = leagues[0].get("id")
                print(f"   ✅ Success - Found {len(leagues)} leagues")
            else:
                # Use a known working league ID for testing
                self.test_data["league_id"] = "1266251242766598144"
                print("   ⚠️  Success but no leagues found - using test league ID")
        else:
            # Use a known working league ID for testing
            self.test_data["league_id"] = "1266251242766598144"
            print(f"   ❌ Failed - {result.get('error', 'Unknown error')} - using test league ID")
        
        # 2. get_league_info
        if self.test_data.get("league_id"):
            print("\n2️⃣ Testing get_league_info...")
            result = self.test_tool("get_league_info", {"league_id": self.test_data["league_id"]})
            results["get_league_info"] = result
            if result.get("success"):
                print("   ✅ Success - League info retrieved")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 3. get_league_rosters
        if self.test_data.get("league_id"):
            print("\n3️⃣ Testing get_league_rosters...")
            result = self.test_tool("get_league_rosters", {"league_id": self.test_data["league_id"]})
            results["get_league_rosters"] = result
            if result.get("success"):
                rosters = result.get("result", {}).get("rosters", [])
                print(f"   ✅ Success - Found {len(rosters)} rosters")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 4. get_league_rosters_with_draft_info
        if self.test_data.get("league_id"):
            print("\n4️⃣ Testing get_league_rosters_with_draft_info...")
            result = self.test_tool("get_league_rosters_with_draft_info", {"league_id": self.test_data["league_id"]})
            results["get_league_rosters_with_draft_info"] = result
            if result.get("success"):
                print("   ✅ Success - Rosters with draft info retrieved")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 5. get_matchups
        if self.test_data.get("league_id"):
            print("\n5️⃣ Testing get_matchups...")
            result = self.test_tool("get_matchups", {"league_id": self.test_data["league_id"], "week": 1})
            results["get_matchups"] = result
            if result.get("success"):
                matchups = result.get("result", {}).get("matchups", [])
                print(f"   ✅ Success - Found {len(matchups)} matchups")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 6. search_players
        print("\n6️⃣ Testing search_players...")
        result = self.test_tool("search_players", {"query": "Josh Allen"})
        results["search_players"] = result
        if result.get("success"):
            players = result.get("result", {}).get("players", [])
            if players:
                # Find the QB Josh Allen (not the guard)
                qb_allen = next((p for p in players if p.get("position") == "QB"), players[0])
                self.test_data["player_id"] = qb_allen.get("id")
                print(f"   ✅ Success - Found {len(players)} players, using QB Josh Allen (ID: {self.test_data['player_id']})")
            else:
                print("   ⚠️  Success but no players found")
        else:
            print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 7. get_player_stats
        if self.test_data.get("player_id"):
            print("\n7️⃣ Testing get_player_stats...")
            result = self.test_tool("get_player_stats", {"player_id": self.test_data["player_id"], "season": "2025"})
            results["get_player_stats"] = result
            if result.get("success"):
                print("   ✅ Success - Player stats retrieved")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 8. get_trending_players
        print("\n8️⃣ Testing get_trending_players...")
        result = self.test_tool("get_trending_players", {"add_drop": "add", "lookback_hours": 24, "limit": 10})
        results["get_trending_players"] = result
        if result.get("success"):
            trending = result.get("result", {}).get("trending_players", [])
            print(f"   ✅ Success - Found {len(trending)} trending players")
        else:
            print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 9. get_league_users
        if self.test_data.get("league_id"):
            print("\n9️⃣ Testing get_league_users...")
            result = self.test_tool("get_league_users", {"league_id": self.test_data["league_id"]})
            results["get_league_users"] = result
            if result.get("success"):
                users = result.get("result", {}).get("users", [])
                print(f"   ✅ Success - Found {len(users)} users")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 10. get_roster_user_mapping
        if self.test_data.get("league_id"):
            print("\n🔟 Testing get_roster_user_mapping...")
            result = self.test_tool("get_roster_user_mapping", {"league_id": self.test_data["league_id"]})
            results["get_roster_user_mapping"] = result
            if result.get("success"):
                mappings = result.get("result", {}).get("mappings", [])
                print(f"   ✅ Success - Found {len(mappings)} roster-user mappings")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 11. get_league_draft
        if self.test_data.get("league_id"):
            print("\n1️⃣1️⃣ Testing get_league_draft...")
            result = self.test_tool("get_league_draft", {"league_id": self.test_data["league_id"]})
            results["get_league_draft"] = result
            if result.get("success"):
                picks = result.get("result", {}).get("picks", [])
                print(f"   ✅ Success - Found {len(picks)} draft picks")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 12. get_matchup_scores
        if self.test_data.get("league_id"):
            print("\n1️⃣2️⃣ Testing get_matchup_scores...")
            result = self.test_tool("get_matchup_scores", {"league_id": self.test_data["league_id"], "week": 1})
            results["get_matchup_scores"] = result
            if result.get("success"):
                matchups = result.get("result", {}).get("matchups", [])
                print(f"   ✅ Success - Found {len(matchups)} matchup scores")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 13. analyze_trade_targets
        if self.test_data.get("league_id"):
            print("\n1️⃣3️⃣ Testing analyze_trade_targets...")
            result = self.test_tool("analyze_trade_targets", {"league_id": self.test_data["league_id"], "roster_id": 1})
            results["analyze_trade_targets"] = result
            if result.get("success"):
                print("   ✅ Success - Trade targets analyzed")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # 14. evaluate_roster_needs
        if self.test_data.get("league_id"):
            print("\n1️⃣4️⃣ Testing evaluate_roster_needs...")
            result = self.test_tool("evaluate_roster_needs", {"league_id": self.test_data["league_id"], "roster_id": 1})
            results["evaluate_roster_needs"] = result
            if result.get("success"):
                print("   ✅ Success - Roster needs evaluated")
            else:
                print(f"   ❌ Failed - {result.get('error', 'Unknown error')}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        successful_tools = []
        failed_tools = []
        
        for tool_name, result in results.items():
            if result.get("success"):
                successful_tools.append(tool_name)
            else:
                failed_tools.append(tool_name)
        
        print(f"✅ Successful tools: {len(successful_tools)}/14")
        for tool in successful_tools:
            print(f"   - {tool}")
        
        if failed_tools:
            print(f"\n❌ Failed tools: {len(failed_tools)}/14")
            for tool in failed_tools:
                print(f"   - {tool}")
        
        # Save detailed results
        with open("test_results_detailed.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: test_results_detailed.json")
        
        return results

if __name__ == "__main__":
    tester = SleeperToolTester()
    results = tester.test_all_tools()
