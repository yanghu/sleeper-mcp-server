#!/usr/bin/env python3
"""
Fantasy Football Workflow Testing Script for Sleeper MCP Server.

This script demonstrates a realistic fantasy football scenario:
1. Find user's leagues
2. Get league information and rosters
3. Search for players to add
4. Analyze roster needs
5. Evaluate trade opportunities
"""

import requests
import json
import time
from typing import Dict, Any, List


class FantasyWorkflowTester:
    """Tester for realistic fantasy football workflows."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.workflow_data = {}
    
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
    
    def step_1_find_user_leagues(self):
        """Step 1: Find user's leagues for the 2025 season."""
        print("🏈 STEP 1: Finding User Leagues")
        print("-" * 40)
        
        result = self.call_tool("get_user_leagues", {
            "username": "huyang",
            "season": "2025"
        })
        
        if "error" not in result:
            print("✅ Successfully found user leagues")
            
            # Handle the actual response format
            if isinstance(result, list) and len(result) > 0:
                # This is the MCP format response
                text_content = result[0].get('text', '')
                parsed_data = self.extract_league_data_from_text(text_content)
                self.workflow_data['user_leagues'] = parsed_data
                
                leagues = parsed_data.get('leagues', [])
                print(f"   Found {len(leagues)} leagues")
                
                for i, league in enumerate(leagues, 1):
                    print(f"   {i}. {league.get('name', 'Unknown')}")
                    print(f"      ID: {league.get('league_id', 'Unknown')}")
                    print(f"      Status: {league.get('status', 'Unknown')}")
                    print(f"      Teams: {league.get('total_rosters', 'Unknown')}")
                    print()
            else:
                # This might be direct data
                self.workflow_data['user_leagues'] = result
                leagues = result.get('leagues', [])
                print(f"   Found {len(leagues)} leagues")
                
                for i, league in enumerate(leagues, 1):
                    print(f"   {i}. {league.get('name', 'Unknown')}")
                    print(f"      ID: {league.get('league_id', 'Unknown')}")
                    print(f"      Status: {league.get('status', 'Unknown')}")
                    print(f"      Teams: {league.get('total_rosters', 'Unknown')}")
                    print()
            
            return True
        else:
            print(f"❌ Failed to find user leagues: {result.get('error')}")
            return False
    
    def step_2_analyze_primary_league(self):
        """Step 2: Analyze the primary league (first one found)."""
        print("🏆 STEP 2: Analyzing Primary League")
        print("-" * 40)
        
        if 'user_leagues' not in self.workflow_data:
            print("❌ No user leagues data available")
            return False
        
        leagues = self.workflow_data['user_leagues'].get('leagues', [])
        if not leagues:
            print("❌ No leagues found")
            return False
        
        primary_league = leagues[0]
        league_id = primary_league.get('league_id')
        league_name = primary_league.get('name', 'Unknown')
        
        print(f"Analyzing league: {league_name} (ID: {league_id})")
        
        # Get league info
        print("\n   Getting league information...")
        league_info = self.call_tool("get_league_info", {"league_id": league_id})
        if "error" not in league_info:
            print("   ✅ League info retrieved")
            self.workflow_data['league_info'] = league_info
        else:
            print(f"   ❌ Failed to get league info: {league_info.get('error')}")
        
        # Get league rosters
        print("\n   Getting league rosters...")
        league_rosters = self.call_tool("get_league_rosters", {"league_id": league_id})
        if "error" not in league_rosters:
            print("   ✅ League rosters retrieved")
            self.workflow_data['league_rosters'] = league_rosters
        else:
            print(f"   ❌ Failed to get league rosters: {league_rosters.get('error')}")
        
        # Get league users
        print("\n   Getting league users...")
        league_users = self.call_tool("get_league_users", {"league_id": league_id})
        if "error" not in league_users:
            print("   ✅ League users retrieved")
            self.workflow_data['league_users'] = league_users
        else:
            print(f"   ❌ Failed to get league users: {league_users.get('error')}")
        
        return True
    
    def step_3_player_research(self):
        """Step 3: Research players for potential additions."""
        print("\n🔍 STEP 3: Player Research")
        print("-" * 40)
        
        # Search for trending players
        print("   Finding trending players...")
        trending_result = self.call_tool("get_trending_players", {
            "sport": "nfl",
            "add_drop": "add"
        })
        
        if "error" not in trending_result:
            print("   ✅ Trending players found")
            players = trending_result.get('players', [])
            print(f"      Found {len(players)} trending players")
            
            # Show top 5 trending players
            for i, player in enumerate(players[:5], 1):
                name = player.get('full_name', 'Unknown')
                position = player.get('position', 'Unknown')
                team = player.get('team', 'Unknown')
                count = player.get('count', 0)
                print(f"      {i}. {name} ({position} - {team}) - {count} adds")
            
            self.workflow_data['trending_players'] = trending_result
        else:
            print(f"   ❌ Failed to get trending players: {trending_result.get('error')}")
        
        # Search for specific players
        print("\n   Searching for specific players...")
        search_queries = ["Christian McCaffrey", "Tyreek Hill", "Travis Kelce"]
        
        for query in search_queries:
            print(f"      Searching for: {query}")
            search_result = self.call_tool("search_players", {"query": query})
            
            if "error" not in search_result:
                players = search_result.get('players', [])
                if players:
                    player = players[0]  # Get first result
                    player_id = player.get('player_id')
                    print(f"         Found: {player.get('full_name')} (ID: {player_id})")
                    
                    # Get player stats
                    if player_id:
                        stats_result = self.call_tool("get_player_stats", {
                            "player_id": player_id,
                            "season": "2024"
                        })
                        if "error" not in stats_result:
                            print(f"         Stats available: {len(stats_result.get('stats', {}))} categories")
                        else:
                            print(f"         No stats available")
                else:
                    print(f"         No players found")
            else:
                print(f"         Search failed: {search_result.get('error')}")
        
        return True
    
    def step_4_roster_analysis(self):
        """Step 4: Analyze roster needs and trade opportunities."""
        print("\n📋 STEP 4: Roster Analysis")
        print("-" * 40)
        
        if 'league_rosters' not in self.workflow_data:
            print("❌ No league rosters data available")
            return False
        
        rosters = self.workflow_data['league_rosters'].get('rosters', [])
        if not rosters:
            print("❌ No rosters found")
            return False
        
        # Analyze first few rosters
        for i, roster in enumerate(rosters[:3], 1):
            roster_id = roster.get('roster_id')
            owner_info = roster.get('owner_info', {})
            display_name = owner_info.get('display_name', f"User {roster_id}")
            
            print(f"\n   Analyzing roster {i}: {display_name}")
            print(f"      Roster ID: {roster_id}")
            
            league_id = self.workflow_data['user_leagues']['leagues'][0].get('league_id')
            
            # Evaluate roster needs
            print("      Evaluating roster needs...")
            eval_result = self.call_tool("evaluate_roster_needs", {
                "league_id": league_id,
                "roster_id": roster_id
            })
            
            if "error" not in eval_result:
                overall_rating = eval_result.get('overall_rating', 0)
                print(f"         Overall Rating: {overall_rating * 100:.0f}%")
                
                positional_strength = eval_result.get('positional_strength', {})
                if positional_strength:
                    print("         Positional Strength:")
                    for pos, strength in list(positional_strength.items())[:3]:  # Show top 3
                        strength_pct = strength * 100
                        emoji = "💪" if strength >= 0.8 else "👍" if strength >= 0.6 else "⚠️" if strength >= 0.4 else "🔴"
                        print(f"            {pos}: {strength_pct:.0f}% {emoji}")
            else:
                print(f"         Evaluation failed: {eval_result.get('error')}")
            
            # Analyze trade targets
            print("      Analyzing trade targets...")
            trade_result = self.call_tool("analyze_trade_targets", {
                "league_id": league_id,
                "roster_id": roster_id,
                "position": "RB"  # Focus on RB position
            })
            
            if "error" not in trade_result:
                target_teams = trade_result.get('target_teams', [])
                print(f"         Potential trade partners: {len(target_teams)} teams")
                
                if target_teams:
                    print(f"         Target roster IDs: {', '.join(map(str, target_teams[:3]))}")
            else:
                print(f"         Trade analysis failed: {trade_result.get('error')}")
        
        return True
    
    def step_5_matchup_analysis(self):
        """Step 5: Analyze current matchups and scores."""
        print("\n⚔️ STEP 5: Matchup Analysis")
        print("-" * 40)
        
        if 'user_leagues' not in self.workflow_data:
            print("❌ No user leagues data available")
            return False
        
        league_id = self.workflow_data['user_leagues']['leagues'][0].get('league_id')
        
        # Test with week 1 (adjust as needed)
        week = 1
        print(f"   Analyzing Week {week} matchups...")
        
        # Get matchups
        matchups_result = self.call_tool("get_matchups", {
            "league_id": league_id,
            "week": week
        })
        
        if "error" not in matchups_result:
            print("   ✅ Matchups retrieved")
            matchups = matchups_result.get('matchups', [])
            print(f"      Found {len(matchups)} matchups")
            self.workflow_data['matchups'] = matchups_result
        else:
            print(f"   ❌ Failed to get matchups: {matchups_result.get('error')}")
        
        # Get matchup scores
        print(f"\n   Analyzing Week {week} scores...")
        scores_result = self.call_tool("get_matchup_scores", {
            "league_id": league_id,
            "week": week
        })
        
        if "error" not in scores_result:
            print("   ✅ Scores retrieved")
            scores = scores_result.get('scores', [])
            print(f"      Found {len(scores)} score entries")
            self.workflow_data['matchup_scores'] = scores_result
        else:
            print(f"   ❌ Failed to get scores: {scores_result.get('error')}")
        
        return True
    
    def run_fantasy_workflow(self):
        """Run the complete fantasy football workflow."""
        print("🎯 FANTASY FOOTBALL WORKFLOW TEST")
        print("=" * 60)
        print("This test simulates a realistic fantasy football scenario")
        print("using multiple tools in sequence.\n")
        
        # Check server health
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code != 200:
                print("❌ Server is not healthy. Please start the server first.")
                return
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            print("Please start the server with: python start_http_server.py")
            return
        
        print("✅ Server is healthy and ready for testing\n")
        
        # Run workflow steps
        steps = [
            ("Find User Leagues", self.step_1_find_user_leagues),
            ("Analyze Primary League", self.step_2_analyze_primary_league),
            ("Player Research", self.step_3_player_research),
            ("Roster Analysis", self.step_4_roster_analysis),
            ("Matchup Analysis", self.step_5_matchup_analysis)
        ]
        
        successful_steps = 0
        total_steps = len(steps)
        
        for step_name, step_func in steps:
            try:
                if step_func():
                    successful_steps += 1
                else:
                    print(f"⚠️ Step '{step_name}' had issues but continuing...")
            except Exception as e:
                print(f"❌ Step '{step_name}' failed with error: {e}")
                print("Continuing with next step...")
            
            # Small delay between steps
            time.sleep(1)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 WORKFLOW SUMMARY")
        print("=" * 60)
        print(f"Steps completed: {successful_steps}/{total_steps}")
        
        if successful_steps == total_steps:
            print("🎉 All workflow steps completed successfully!")
        elif successful_steps > total_steps / 2:
            print("⚠️ Most workflow steps completed. Some tools may need configuration.")
        else:
            print("❌ Many workflow steps failed. Check server configuration.")
        
        # Save workflow data
        if self.workflow_data:
            with open('fantasy_workflow_results.json', 'w') as f:
                json.dump(self.workflow_data, f, indent=2)
            print(f"\n💾 Workflow data saved to fantasy_workflow_results.json")
        
        print("\n🏈 Fantasy Football Workflow Test Complete!")


if __name__ == "__main__":
    tester = FantasyWorkflowTester()
    tester.run_fantasy_workflow()
