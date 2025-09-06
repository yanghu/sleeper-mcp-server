#!/usr/bin/env python3
"""
Analyze regression test results to identify tools returning empty data.
"""

import json
import sys
import os
from typing import Dict, Any, List

def analyze_empty_results(results_file: str) -> Dict[str, Any]:
    """Analyze test results to find tools returning empty data."""
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    empty_tools = []
    tools_with_data = []
    
    # Define what constitutes "empty" for each tool type
    empty_indicators = {
        'get_user_leagues': ['leagues', []],
        'get_league_info': ['league_id', None],
        'get_league_rosters': ['rosters', []],
        'get_league_rosters_with_draft_info': ['rosters', []],
        'get_league_users': ['users', []],
        'get_roster_user_mapping': ['mappings', []],
        'get_league_draft': ['picks', []],
        'search_players': ['players', []],
        'get_trending_players': ['players', []],
        'get_player_stats': ['stats', {}],
        'get_matchups': ['matchups', []],
        'get_matchup_scores': ['matchups', []],
        'analyze_trade_targets': ['target_teams', []],
        'evaluate_roster_needs': ['strengths', []]
    }
    
    for result in results:
        tool_name = result.get('tool')
        success = result.get('success', False)
        response_data = result.get('response_data', {})
        result_data = response_data.get('result', {})
        
        if not success:
            continue
            
        # Check if this tool is returning empty data
        is_empty = False
        if tool_name in empty_indicators and result_data:
            field, empty_value = empty_indicators[tool_name]
            if field in result_data:
                if result_data[field] == empty_value:
                    is_empty = True
                elif isinstance(empty_value, list) and len(result_data[field]) == 0:
                    is_empty = True
                elif isinstance(empty_value, dict) and len(result_data[field]) == 0:
                    is_empty = True
        
        if is_empty:
            empty_tools.append({
                'tool': tool_name,
                'reason': f"Empty {empty_indicators[tool_name][0]}",
                'data': result_data
            })
        else:
            tools_with_data.append({
                'tool': tool_name,
                'data': result_data
            })
    
    return {
        'empty_tools': empty_tools,
        'tools_with_data': tools_with_data,
        'total_tools': len(results),
        'empty_count': len(empty_tools),
        'data_count': len(tools_with_data)
    }

def suggest_better_test_data(empty_tools: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Suggest better test data for tools that returned empty results."""
    
    suggestions = {}
    
    for tool_info in empty_tools:
        tool_name = tool_info['tool']
        
        if tool_name == 'get_user_leagues':
            suggestions[tool_name] = {
                'current': {'username': 'testuser123'},
                'suggested': [
                    {'username': 'sleeper', 'season': '2024'},  # Known active user
                    {'username': 'fantasyfootball', 'season': '2024'},  # Another known user
                    {'username': 'nfl', 'season': '2024'}  # Official NFL account
                ],
                'reason': 'Use known active Sleeper users'
            }
        
        elif tool_name in ['get_league_info', 'get_league_rosters', 'get_league_rosters_with_draft_info', 
                          'get_league_users', 'get_roster_user_mapping', 'get_league_draft']:
            suggestions[tool_name] = {
                'current': {'league_id': '1234567890'},
                'suggested': [
                    {'league_id': '123456789012345678'},  # 18-digit format
                    {'league_id': '987654321098765432'},  # Another 18-digit format
                ],
                'reason': 'Use proper 18-digit league ID format'
            }
        
        elif tool_name == 'search_players':
            suggestions[tool_name] = {
                'current': {'query': 'Josh Allen'},
                'suggested': [
                    {'query': 'Josh Allen', 'position': 'QB'},
                    {'query': 'Cooper Kupp', 'position': 'WR'},
                    {'query': 'Travis Kelce', 'position': 'TE'},
                    {'query': 'Christian McCaffrey', 'position': 'RB'}
                ],
                'reason': 'Use well-known NFL players with position filters'
            }
        
        elif tool_name == 'get_trending_players':
            suggestions[tool_name] = {
                'current': {'sport': 'nfl', 'add_drop': 'add'},
                'suggested': [
                    {'sport': 'nfl', 'add_drop': 'add'},
                    {'sport': 'nfl', 'add_drop': 'drop'},
                ],
                'reason': 'Current test data should work - may be API timing issue'
            }
        
        elif tool_name == 'get_player_stats':
            suggestions[tool_name] = {
                'current': {'player_id': '4984', 'season': '2023'},
                'suggested': [
                    {'player_id': '4984', 'season': '2024'},  # Josh Allen 2024
                    {'player_id': '4034', 'season': '2024'},  # Cooper Kupp 2024
                    {'player_id': '4035', 'season': '2024'},  # Travis Kelce 2024
                    {'player_id': '4037', 'season': '2024'}   # Christian McCaffrey 2024
                ],
                'reason': 'Use 2024 season and well-known player IDs'
            }
        
        elif tool_name in ['get_matchups', 'get_matchup_scores']:
            suggestions[tool_name] = {
                'current': {'league_id': '1234567890', 'week': 1},
                'suggested': [
                    {'league_id': '123456789012345678', 'week': 1},
                    {'league_id': '123456789012345678', 'week': 5},
                    {'league_id': '123456789012345678', 'week': 10}
                ],
                'reason': 'Use proper 18-digit league ID format'
            }
        
        elif tool_name in ['analyze_trade_targets', 'evaluate_roster_needs']:
            suggestions[tool_name] = {
                'current': {'league_id': '1234567890', 'roster_id': 1},
                'suggested': [
                    {'league_id': '123456789012345678', 'roster_id': 1},
                    {'league_id': '123456789012345678', 'roster_id': 2},
                    {'league_id': '123456789012345678', 'roster_id': 3}
                ],
                'reason': 'Use proper 18-digit league ID format'
            }
    
    return suggestions

def main():
    """Main analysis function."""
    
    # Find the most recent results file
    results_files = [f for f in os.listdir('.') if f.startswith('regression_results_') and f.endswith('.json')]
    if not results_files:
        print("❌ No regression results files found")
        sys.exit(1)
    
    latest_file = sorted(results_files)[-1]
    print(f"📊 Analyzing results from: {latest_file}")
    
    # Analyze results
    analysis = analyze_empty_results(latest_file)
    
    print(f"\n📈 ANALYSIS SUMMARY")
    print(f"=" * 50)
    print(f"Total tools tested: {analysis['total_tools']}")
    print(f"Tools with data: {analysis['data_count']}")
    print(f"Tools with empty results: {analysis['empty_count']}")
    
    if analysis['empty_tools']:
        print(f"\n❌ TOOLS RETURNING EMPTY DATA")
        print(f"=" * 50)
        for tool_info in analysis['empty_tools']:
            print(f"• {tool_info['tool']}: {tool_info['reason']}")
    
    if analysis['tools_with_data']:
        print(f"\n✅ TOOLS WITH DATA")
        print(f"=" * 50)
        for tool_info in analysis['tools_with_data']:
            print(f"• {tool_info['tool']}")
    
    # Generate suggestions
    suggestions = suggest_better_test_data(analysis['empty_tools'])
    
    if suggestions:
        print(f"\n💡 SUGGESTIONS FOR BETTER TEST DATA")
        print(f"=" * 50)
        for tool_name, suggestion in suggestions.items():
            print(f"\n{tool_name}:")
            print(f"  Current: {suggestion['current']}")
            print(f"  Suggested: {suggestion['suggested']}")
            print(f"  Reason: {suggestion['reason']}")
    
    # Save suggestions to file
    suggestions_file = "test_data_suggestions.json"
    with open(suggestions_file, 'w') as f:
        json.dump(suggestions, f, indent=2)
    
    print(f"\n📄 Suggestions saved to: {suggestions_file}")

if __name__ == "__main__":
    main()
