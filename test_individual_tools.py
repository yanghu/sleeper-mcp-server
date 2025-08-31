#!/usr/bin/env python3
"""
Individual tool testing script for Sleeper MCP server.

This script allows you to test specific tools with predefined test cases.
"""

import requests
import json
import sys
from typing import Dict, Any


class IndividualToolTester:
    """Tester for individual tools with specific test cases."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
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
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
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
    
    def test_get_user_leagues(self):
        """Test get_user_leagues with huyang/2025."""
        print("🏈 Testing get_user_leagues...")
        
        result = self.call_tool("get_user_leagues", {
            "username": "huyang",
            "season": "2025"
        })
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                parsed_data = self.extract_league_data_from_text(text_content)
                leagues = parsed_data.get('leagues', [])
                print(f"   Found {len(leagues)} leagues")
                for league in leagues[:3]:  # Show first 3
                    print(f"   • {league.get('name', 'Unknown')} (ID: {league.get('league_id', 'Unknown')})")
                return parsed_data
            else:
                # This might be direct data
                leagues = result.get('leagues', [])
                print(f"   Found {len(leagues)} leagues")
                for league in leagues[:3]:  # Show first 3
                    print(f"   • {league.get('name', 'Unknown')} (ID: {league.get('league_id', 'Unknown')})")
                return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None
    
    def test_get_league_info(self, league_id: str):
        """Test get_league_info with a specific league ID."""
        print(f"🏆 Testing get_league_info with league {league_id}...")
        
        result = self.call_tool("get_league_info", {
            "league_id": league_id
        })
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")  # Show first 100 chars
            else:
                # This might be direct data
                print(f"   League: {result.get('name', 'Unknown')}")
                print(f"   Season: {result.get('season', 'Unknown')}")
                print(f"   Teams: {result.get('total_rosters', 'Unknown')}")
            
            return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None
    
    def test_get_league_rosters(self, league_id: str):
        """Test get_league_rosters with a specific league ID."""
        print(f"👥 Testing get_league_rosters with league {league_id}...")
        
        result = self.call_tool("get_league_rosters", {
            "league_id": league_id
        })
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")  # Show first 100 chars
            else:
                # This might be direct data
                rosters = result.get('rosters', [])
                print(f"   Found {len(rosters)} rosters")
            
            return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None
    
    def test_search_players(self, query: str, position: str = None):
        """Test search_players with a specific query."""
        print(f"🔍 Testing search_players with query '{query}'...")
        
        args = {"query": query}
        if position:
            args["position"] = position
            print(f"   Position filter: {position}")
        
        result = self.call_tool("search_players", args)
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")  # Show first 100 chars
            else:
                # This might be direct data
                players = result.get('players', [])
                print(f"   Found {len(players)} players")
                for player in players[:3]:  # Show first 3
                    name = player.get('full_name', 'Unknown')
                    pos = player.get('position', 'Unknown')
                    team = player.get('team', 'Unknown')
                    print(f"   • {name} ({pos} - {team})")
            
            return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None
    
    def test_get_trending_players(self, sport: str = "nfl", add_drop: str = "add"):
        """Test get_trending_players."""
        print(f"📈 Testing get_trending_players ({sport}, {add_drop})...")
        
        result = self.call_tool("get_trending_players", {
            "sport": sport,
            "add_drop": add_drop
        })
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")  # Show first 100 chars
            else:
                # This might be direct data
                players = result.get('players', [])
                print(f"   Found {len(players)} trending players")
                for player in players[:3]:  # Show first 3
                    name = player.get('full_name', 'Unknown')
                    pos = player.get('position', 'Unknown')
                    count = player.get('count', 0)
                    print(f"   • {name} ({pos}) - {count} adds")
            
            return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None
    
    def test_get_player_stats(self, player_id: str, season: str = "2024"):
        """Test get_player_stats with a specific player ID."""
        print(f"📊 Testing get_player_stats for player {player_id} ({season})...")
        
        result = self.call_tool("get_player_stats", {
            "player_id": player_id,
            "season": season
        })
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")  # Show first 100 chars
            else:
                # This might be direct data
                print(f"   Player: {result.get('player_name', 'Unknown')}")
                print(f"   Position: {result.get('position', 'Unknown')}")
                print(f"   Team: {result.get('team', 'Unknown')}")
                stats = result.get('stats', {})
                if stats:
                    print(f"   Stats available: {len(stats)} categories")
            
            return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None
    
    def test_get_matchups(self, league_id: str, week: int = 1):
        """Test get_matchups with a specific league and week."""
        print(f"⚔️ Testing get_matchups for league {league_id}, week {week}...")
        
        result = self.call_tool("get_matchups", {
            "league_id": league_id,
            "week": week
        })
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")  # Show first 100 chars
            else:
                # This might be direct data
                matchups = result.get('matchups', [])
                print(f"   Found {len(matchups)} matchups")
            
            return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None
    
    def test_get_matchup_scores(self, league_id: str, week: int = 1):
        """Test get_matchup_scores with a specific league and week."""
        print(f"📊 Testing get_matchup_scores for league {league_id}, week {week}...")
        
        result = self.call_tool("get_matchup_scores", {
            "league_id": league_id,
            "week": week
        })
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")  # Show first 100 chars
            else:
                # This might be direct data
                scores = result.get('scores', [])
                print(f"   Found {len(scores)} score entries")
            
            return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None
    
    def test_evaluate_roster_needs(self, league_id: str, roster_id: int):
        """Test evaluate_roster_needs with specific league and roster."""
        print(f"📋 Testing evaluate_roster_needs for roster {roster_id} in league {league_id}...")
        
        result = self.call_tool("evaluate_roster_needs", {
            "league_id": league_id,
            "roster_id": roster_id
        })
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")  # Show first 100 chars
            else:
                # This might be direct data
                overall_rating = result.get('overall_rating', 0)
                print(f"   Overall Rating: {overall_rating * 100:.0f}%")
            
            return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None
    
    def test_analyze_trade_targets(self, league_id: str, roster_id: int, position: str = "RB"):
        """Test analyze_trade_targets with specific parameters."""
        print(f"🔄 Testing analyze_trade_targets for roster {roster_id} in league {league_id}...")
        print(f"   Target position: {position}")
        
        result = self.call_tool("analyze_trade_targets", {
            "league_id": league_id,
            "roster_id": roster_id,
            "position": position
        })
        
        if "error" not in result:
            print("✅ Success!")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                print(f"   Response: {text_content[:100]}...")  # Show first 100 chars
            else:
                # This might be direct data
                target_teams = result.get('target_teams', [])
                print(f"   Potential trade partners: {len(target_teams)} teams")
            
            return result
        else:
            print(f"❌ Failed: {result.get('error')}")
            return None


def main():
    """Main function to run individual tool tests."""
    print("🧪 Individual Tool Testing for Sleeper MCP Server")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("Usage: python test_individual_tools.py <tool_name> [additional_args...]")
        print("\nAvailable tools:")
        print("  get_user_leagues")
        print("  get_league_info <league_id>")
        print("  get_league_rosters <league_id>")
        print("  search_players <query> [position]")
        print("  get_trending_players [sport] [add_drop]")
        print("  get_player_stats <player_id> [season]")
        print("  get_matchups <league_id> [week]")
        print("  get_matchup_scores <league_id> [week]")
        print("  evaluate_roster_needs <league_id> <roster_id>")
        print("  analyze_trade_targets <league_id> <roster_id> [position]")
        print("\nExamples:")
        print("  python test_individual_tools.py get_user_leagues")
        print("  python test_individual_tools.py search_players 'Patrick Mahomes' QB")
        print("  python test_individual_tools.py get_league_info 123456")
        return
    
    tester = IndividualToolTester()
    tool_name = sys.argv[1].lower()
    
    try:
        if tool_name == "get_user_leagues":
            result = tester.test_get_user_leagues()
            if result:
                # Save result for other tests
                with open('user_leagues_result.json', 'w') as f:
                    json.dump(result, f, indent=2)
                print("💾 Result saved to user_leagues_result.json")
        
        elif tool_name == "get_league_info":
            if len(sys.argv) < 3:
                print("❌ Missing league_id argument")
                return
            league_id = sys.argv[2]
            tester.test_get_league_info(league_id)
        
        elif tool_name == "get_league_rosters":
            if len(sys.argv) < 3:
                print("❌ Missing league_id argument")
                return
            league_id = sys.argv[2]
            tester.test_get_league_rosters(league_id)
        
        elif tool_name == "search_players":
            if len(sys.argv) < 3:
                print("❌ Missing query argument")
                return
            query = sys.argv[2]
            position = sys.argv[3] if len(sys.argv) > 3 else None
            tester.test_search_players(query, position)
        
        elif tool_name == "get_trending_players":
            sport = sys.argv[2] if len(sys.argv) > 2 else "nfl"
            add_drop = sys.argv[3] if len(sys.argv) > 3 else "add"
            tester.test_get_trending_players(sport, add_drop)
        
        elif tool_name == "get_player_stats":
            if len(sys.argv) < 3:
                print("❌ Missing player_id argument")
                return
            player_id = sys.argv[2]
            season = sys.argv[3] if len(sys.argv) > 3 else "2024"
            tester.test_get_player_stats(player_id, season)
        
        elif tool_name == "get_matchups":
            if len(sys.argv) < 3:
                print("❌ Missing league_id argument")
                return
            league_id = sys.argv[2]
            week = int(sys.argv[3]) if len(sys.argv) > 3 else 1
            tester.test_get_matchups(league_id, week)
        
        elif tool_name == "get_matchup_scores":
            if len(sys.argv) < 3:
                print("❌ Missing league_id argument")
                return
            league_id = sys.argv[2]
            week = int(sys.argv[3]) if len(sys.argv) > 3 else 1
            tester.test_get_matchup_scores(league_id, week)
        
        elif tool_name == "evaluate_roster_needs":
            if len(sys.argv) < 4:
                print("❌ Missing league_id and roster_id arguments")
                return
            league_id = sys.argv[2]
            roster_id = int(sys.argv[3])
            tester.test_evaluate_roster_needs(league_id, roster_id)
        
        elif tool_name == "analyze_trade_targets":
            if len(sys.argv) < 4:
                print("❌ Missing league_id and roster_id arguments")
                return
            league_id = sys.argv[2]
            roster_id = int(sys.argv[3])
            position = sys.argv[4] if len(sys.argv) > 4 else "RB"
            tester.test_analyze_trade_targets(league_id, roster_id, position)
        
        else:
            print(f"❌ Unknown tool: {tool_name}")
            print("Run without arguments to see available tools")
    
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
