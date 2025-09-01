#!/usr/bin/env python3
"""
Comprehensive test script for all Sleeper MCP server tools.

This script demonstrates a realistic workflow using actual tool responses
to generate subsequent tool calls.
"""

import requests
import json
import time
from typing import Dict, Any, List


class SleeperToolTester:
    """Comprehensive tester for all Sleeper MCP server tools."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_data = {}
        
    def health_check(self) -> bool:
        """Check if server is running."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ Server is healthy and running")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return False
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools."""
        try:
            response = self.session.get(f"{self.base_url}/tools")
            if response.status_code == 200:
                data = response.json()
                tools = data.get('tools', [])
                print(f"📋 Found {len(tools)} available tools")
                return tools
            else:
                print(f"❌ Failed to get tools: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error listing tools: {e}")
            return []
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool and return the result."""
        try:
            response = self.session.post(
                f"{self.base_url}/tools/{tool_name}",
                json={"arguments": arguments},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                # The server returns a nested structure, extract the actual result
                if 'result' in data:
                    return data['result']
                else:
                    return data
            else:
                print(f"❌ Tool call failed for {tool_name}: {response.status_code}")
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            print(f"❌ Error calling {tool_name}: {e}")
            return {"error": str(e)}
    
    def extract_league_data_from_text(self, text_content: str) -> Dict[str, Any]:
        """Extract league data from the formatted text response."""
        leagues = []
        
        # Split by league sections (numbered items)
        lines = text_content.split('\n')
        current_league = None
        
        for line in lines:
            line = line.strip()
            
            # Look for league headers (e.g., "**1. 老登们**")
            if line.startswith('**') and line.endswith('**') and '.' in line:
                if current_league:
                    leagues.append(current_league)
                
                # Extract league name
                league_name = line.replace('**', '').split('. ', 1)[-1]
                current_league = {
                    'name': league_name,
                    'league_id': '',
                    'status': '',
                    'total_rosters': 0,
                    'sport': ''
                }
            
            # Extract league details
            elif current_league and line.startswith('•'):
                if 'League ID:' in line:
                    league_id = line.split('`')[1] if '`' in line else line.split(': ')[-1]
                    current_league['league_id'] = league_id
                elif 'Status:' in line:
                    status = line.split(': ')[-1]
                    current_league['status'] = status
                elif 'Teams:' in line:
                    teams = line.split(': ')[-1]
                    try:
                        current_league['total_rosters'] = int(teams)
                    except ValueError:
                        current_league['total_rosters'] = 0
                elif 'Sport:' in line:
                    sport = line.split(': ')[-1]
                    current_league['sport'] = sport
        
        # Add the last league
        if current_league:
            leagues.append(current_league)
        
        return {
            'username': 'huyang',
            'season': '2025',
            'leagues': leagues
        }
    
    def test_user_leagues(self) -> bool:
        """Test get_user_leagues tool."""
        print("\n🏈 Testing get_user_leagues...")
        
        result = self.call_tool("get_user_leagues", {
            "username": "huyang",
            "season": "2025"
        })
        
        if "error" not in result:
            print("✅ get_user_leagues successful")
            
            # Extract structured data from the response
            if 'result' in result and isinstance(result['result'], dict):
                self.test_data['user_leagues'] = result['result']
                leagues_count = len(result['result'].get('leagues', []))
                print(f"   Found {leagues_count} leagues in response")
            else:
                print("⚠️ Unexpected response format")
                return False
            
            return True
        else:
            print(f"❌ get_user_leagues failed: {result.get('error')}")
            return False
    
    def test_league_info(self) -> bool:
        """Test get_league_info tool using data from user_leagues."""
        print("\n🏆 Testing get_league_info...")
        
        if 'user_leagues' not in self.test_data:
            print("⚠️ Skipping - no user leagues data available")
            return False
        
        leagues = self.test_data['user_leagues'].get('leagues', [])
        if not leagues:
            print("⚠️ No leagues found to test with")
            return False
        
        # Use the first league
        league_id = leagues[0].get('id')
        if not league_id:
            print("⚠️ No league ID found in first league")
            return False
        
        print(f"   Using league ID: {league_id}")
        
        result = self.call_tool("get_league_info", {
            "league_id": league_id
        })
        
        if "error" not in result:
            print("✅ get_league_info successful")
            self.test_data['league_info'] = result
            return True
        else:
            print(f"❌ get_league_info failed: {result.get('error')}")
            return False
    
    def test_league_rosters(self) -> bool:
        """Test get_league_rosters tool."""
        print("\n👥 Testing get_league_rosters...")
        
        if 'user_leagues' not in self.test_data:
            print("⚠️ Skipping - no user leagues data available")
            return False
        
        leagues = self.test_data['user_leagues'].get('leagues', [])
        if not leagues:
            print("⚠️ No leagues found to test with")
            return False
        
        league_id = leagues[0].get('id')
        print(f"   Using league ID: {league_id}")
        
        result = self.call_tool("get_league_rosters", {
            "league_id": league_id
        })
        
        if "error" not in result:
            print("✅ get_league_rosters successful")
            self.test_data['league_rosters'] = result
            return True
        else:
            print(f"❌ get_league_rosters failed: {result.get('error')}")
            return False
    
    def test_league_users(self) -> bool:
        """Test get_league_users tool."""
        print("\n👤 Testing get_league_users...")
        
        if 'user_leagues' not in self.test_data:
            print("⚠️ Skipping - no user leagues data available")
            return False
        
        leagues = self.test_data['user_leagues'].get('leagues', [])
        if not leagues:
            print("⚠️ No leagues found to test with")
            return False
        
        league_id = leagues[0].get('id')
        print(f"   Using league ID: {league_id}")
        
        result = self.call_tool("get_league_users", {
            "league_id": league_id
        })
        
        if "error" not in result:
            print("✅ get_league_users successful")
            self.test_data['league_users'] = result
            return True
        else:
            print(f"❌ get_league_users failed: {result.get('error')}")
            return False
    
    def test_search_players(self) -> bool:
        """Test search_players tool."""
        print("\n🔍 Testing search_players...")
        
        # Test with a well-known player
        result = self.call_tool("search_players", {
            "query": "Patrick Mahomes",
            "position": "QB"
        })
        
        if "error" not in result:
            print("✅ search_players successful")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")
                self.test_data['search_players'] = result
            else:
                # This might be direct data
                self.test_data['search_players'] = result
            
            return True
        else:
            print(f"❌ search_players failed: {result.get('error')}")
            return False
    
    def test_trending_players(self) -> bool:
        """Test get_trending_players tool."""
        print("\n📈 Testing get_trending_players...")
        
        result = self.call_tool("get_trending_players", {
            "sport": "nfl",
            "add_drop": "add"
        })
        
        if "error" not in result:
            print("✅ get_trending_players successful")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")
                self.test_data['trending_players'] = result
            else:
                # This might be direct data
                self.test_data['trending_players'] = result
            
            return True
        else:
            print(f"❌ get_trending_players failed: {result.get('error')}")
            return False
    
    def test_player_stats(self) -> bool:
        """Test get_player_stats tool using data from search_players."""
        print("\n📊 Testing get_player_stats...")
        
        if 'search_players' not in self.test_data:
            print("⚠️ Skipping - no player search data available")
            return False
        
        # For now, use a hardcoded player ID since we can't easily extract it from MCP text
        # In a real scenario, you'd parse the text response to extract player IDs
        player_id = "4039"  # Patrick Mahomes' ID
        print(f"   Using hardcoded player ID: {player_id}")
        
        result = self.call_tool("get_player_stats", {
            "player_id": player_id,
            "season": "2024"
        })
        
        if "error" not in result:
            print("✅ get_player_stats successful")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")
                self.test_data['player_stats'] = result
            else:
                # This might be direct data
                self.test_data['player_stats'] = result
            
            return True
        else:
            print(f"❌ get_player_stats failed: {result.get('error')}")
            return False
    
    def test_matchups(self) -> bool:
        """Test get_matchups tool."""
        print("\n⚔️ Testing get_matchups...")
        
        if 'user_leagues' not in self.test_data:
            print("⚠️ Skipping - no user leagues data available")
            return False
        
        leagues = self.test_data['user_leagues'].get('leagues', [])
        if not leagues:
            print("⚠️ No leagues found to test with")
            return False
        
        league_id = leagues[0].get('id')
        print(f"   Using league ID: {league_id}, Week 1")
        
        result = self.call_tool("get_matchups", {
            "league_id": league_id,
            "week": 1
        })
        
        if "error" not in result:
            print("✅ get_matchups successful")
            self.test_data['matchups'] = result
            return True
        else:
            print(f"❌ get_matchups failed: {result.get('error')}")
            return False
    
    def test_matchup_scores(self) -> bool:
        """Test get_matchup_scores tool."""
        print("\n📊 Testing get_matchup_scores...")
        
        if 'user_leagues' not in self.test_data:
            print("⚠️ Skipping - no user leagues data available")
            return False
        
        leagues = self.test_data['user_leagues'].get('leagues', [])
        if not leagues:
            print("⚠️ No leagues found to test with")
            return False
        
        league_id = leagues[0].get('id')
        print(f"   Using league ID: {league_id}, Week 1")
        
        result = self.call_tool("get_matchup_scores", {
            "league_id": league_id,
            "week": 1
        })
        
        if "error" not in result:
            print("✅ get_matchup_scores successful")
            self.test_data['matchup_scores'] = result
            return True
        else:
            print(f"❌ get_matchup_scores failed: {result.get('error')}")
            return False
    
    def test_roster_analysis(self) -> bool:
        """Test roster analysis tools."""
        print("\n🔄 Testing roster analysis tools...")
        
        if 'league_rosters' not in self.test_data:
            print("⚠️ Skipping - no league rosters data available")
            return False
        
        # For now, use hardcoded values since we can't easily extract them from MCP text
        # In a real scenario, you'd parse the text response to extract roster IDs
        roster_id = 1  # Assume first roster
        league_id = self.test_data['user_leagues']['leagues'][0].get('id')
        print(f"   Using roster ID: {roster_id}, league ID: {league_id}")
        
        # Test evaluate_roster_needs
        print("   Testing evaluate_roster_needs...")
        eval_result = self.call_tool("evaluate_roster_needs", {
            "league_id": league_id,
            "roster_id": roster_id
        })
        
        if "error" not in eval_result:
            print("   ✅ evaluate_roster_needs successful")
            self.test_data['roster_evaluation'] = eval_result
        else:
            print(f"   ❌ evaluate_roster_needs failed: {eval_result.get('error')}")
        
        # Test analyze_trade_targets
        print("   Testing analyze_trade_targets...")
        trade_result = self.call_tool("analyze_trade_targets", {
            "league_id": league_id,
            "roster_id": roster_id,
            "position": "RB"
        })
        
        if "error" not in trade_result:
            print("   ✅ analyze_trade_targets successful")
            self.test_data['trade_analysis'] = trade_result
            return True
        else:
            print(f"   ❌ analyze_trade_targets failed: {trade_result.get('error')}")
            return False
    
    def run_comprehensive_test(self):
        """Run all tool tests in logical order."""
        print("🚀 Starting Comprehensive Sleeper MCP Server Tool Test")
        print("=" * 60)
        
        # Check server health first
        if not self.health_check():
            print("❌ Server is not available. Please start the server first.")
            return
        
        # List available tools
        tools = self.list_tools()
        if not tools:
            print("❌ No tools available. Server may not be properly initialized.")
            return
        
        print(f"\n📋 Available tools: {len(tools)}")
        for tool in tools:
            print(f"   • {tool['name']}: {tool['description']}")
        
        # Run tests in logical order
        test_results = []
        
        # Start with user data
        test_results.append(("get_user_leagues", self.test_user_leagues()))
        
        # League information tools
        test_results.append(("get_league_info", self.test_league_info()))
        test_results.append(("get_league_rosters", self.test_league_rosters()))
        test_results.append(("get_league_users", self.test_league_users()))
        
        # Player tools
        test_results.append(("search_players", self.test_search_players()))
        test_results.append(("get_trending_players", self.test_trending_players()))
        test_results.append(("get_player_stats", self.test_player_stats()))
        
        # Matchup tools
        test_results.append(("get_matchups", self.test_matchups()))
        test_results.append(("get_matchup_scores", self.test_matchup_scores()))
        
        # Analysis tools
        test_results.append(("roster_analysis", self.test_roster_analysis()))
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        successful = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n🎯 Overall Result: {successful}/{total} tests passed")
        
        if successful == total:
            print("🎉 All tests passed! Server is working perfectly.")
        elif successful > total / 2:
            print("⚠️ Most tests passed. Some tools may need configuration.")
        else:
            print("❌ Many tests failed. Check server configuration and Sleeper API access.")
        
        # Save test data for inspection
        if self.test_data:
            with open('test_results.json', 'w') as f:
                json.dump(self.test_data, f, indent=2)
            print(f"\n💾 Test data saved to test_results.json")


if __name__ == "__main__":
    tester = SleeperToolTester()
    tester.run_comprehensive_test()
