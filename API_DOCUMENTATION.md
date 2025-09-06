# Sleeper MCP Server API Documentation

This document provides comprehensive API documentation for all tools available in the Sleeper MCP Server's HTTP API.

## Base URL

```
http://localhost:8000
```

## Common Response Format

All tool endpoints return responses in this format:

```json
{
  "tool_name": "string",
  "arguments": {...},
  "success": boolean,
  "result": {...} | null,
  "error": "string" | null,
  "timestamp": "ISO8601 string"
}
```

- **success**: `true` if the operation succeeded, `false` if it failed
- **result**: Contains the tool's output data when successful, `null` when failed
- **error**: Contains error message when failed, `null` when successful

## API Endpoints

### Health Check
- **GET** `/health` - Server health status
- **GET** `/info` - Server information
- **GET** `/tools` - List all available tools with their schemas

### Tool Execution
- **POST** `/tools/{tool_name}` - Execute a specific tool
- **POST** `/tools/batch` - Execute multiple tools in batch

## Tool Reference

### League Tools

#### get_user_leagues
Get all leagues for a username in a specific season.

**Endpoint:** `POST /tools/get_user_leagues`

**Input Schema:**
```json
{
  "arguments": {
    "username": "string (required)",
    "season": "string (optional, default: '2024')"
  }
}
```

**Output Schema:**
```json
{
  "username": "string",
  "season": "string", 
  "leagues": [
    {
      "id": "string",
      "name": "string",
      "status": "string",
      "teams": "integer",
      "sport": "string",
      "season": "string",
      "scoring_type": "string",
      "roster_positions": ["string"]
    }
  ],
  "total_leagues": "integer"
}
```

#### get_league_info
Get detailed information about a specific league.

**Endpoint:** `POST /tools/get_league_info`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "name": "string",
  "season": "string",
  "status": "string",
  "sport": "string",
  "teams": "integer",
  "scoring_type": "string",
  "roster_positions": ["string"],
  "scoring_settings": "object",
  "trade_deadline": "integer|null",
  "playoff_start_week": "integer|null",
  "playoff_teams": "integer|null"
}
```

#### get_league_rosters
Get all team rosters in a league.

**Endpoint:** `POST /tools/get_league_rosters`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "rosters": [
    {
      "roster_id": "integer",
      "owner_id": "string",
      "owner_name": "string",
      "players": ["string"],
      "starters": ["string"],
      "reserve": ["string"],
      "taxi": ["string"],
      "metadata": "object",
      "settings": "object"
    }
  ],
  "total_rosters": "integer"
}
```

#### get_league_rosters_with_draft_info
Get all team rosters in a league with draft position metadata for each player.

**Endpoint:** `POST /tools/get_league_rosters_with_draft_info`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "draft_id": "string|null",
  "draft_status": "string|null",
  "rosters": [
    {
      "roster_id": "integer",
      "owner_id": "string",
      "owner_name": "string",
      "players": ["string"],
      "starters": ["string"],
      "reserve": ["string"],
      "taxi": ["string"],
      "metadata": "object",
      "settings": "object"
    }
  ],
  "total_rosters": "integer"
}
```

#### get_league_users
Get all users/participants in a league.

**Endpoint:** `POST /tools/get_league_users`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "users": [
    {
      "user_id": "string",
      "username": "string",
      "display_name": "string|null",
      "avatar": "string|null",
      "is_owner": "boolean"
    }
  ],
  "total_users": "integer"
}
```

#### get_roster_user_mapping
Get a clear mapping of roster IDs to user names for a league.

**Endpoint:** `POST /tools/get_roster_user_mapping`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "mappings": [
    {
      "roster_id": "integer",
      "user_id": "string",
      "user_name": "string",
      "avatar": "string|null"
    }
  ],
  "total_mappings": "integer"
}
```

#### get_league_draft
Get draft results and pick information for a league.

**Endpoint:** `POST /tools/get_league_draft`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "draft_id": "string|null",
  "draft_status": "string|null",
  "draft_type": "string|null",
  "draft_order": ["integer"],
  "picks": [
    {
      "pick_no": "integer",
      "round": "integer",
      "roster_id": "integer",
      "player_id": "string",
      "player_name": "string|null",
      "position": "string|null",
      "team": "string|null",
      "is_keeper": "boolean",
      "keeper_for_team": "string|null",
      "draft_slot": "integer|null"
    }
  ],
  "total_picks": "integer"
}
```

### Player Tools

#### search_players
Search for players by name with optional position filtering.

**Endpoint:** `POST /tools/search_players`

**Input Schema:**
```json
{
  "arguments": {
    "query": "string (required)",
    "position": "string (optional, enum: ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'])"
  }
}
```

**Output Schema:**
```json
{
  "query": "string",
  "position": "string|null",
  "players": [
    {
      "id": "string",
      "name": "string",
      "position": "string|null",
      "team": "string|null",
      "status": "string|null",
      "search_rank": "integer|null",
      "fantasy_positions": ["string"]
    }
  ],
  "total_players": "integer"
}
```

#### get_trending_players
Get trending players (most added/dropped).

**Endpoint:** `POST /tools/get_trending_players`

**Input Schema:**
```json
{
  "arguments": {
    "sport": "string (optional, default: 'nfl')",
    "add_drop": "string (optional, enum: ['add', 'drop'], default: 'add')"
  }
}
```

**Output Schema:**
```json
{
  "sport": "string",
  "add_drop": "string",
  "players": [
    {
      "id": "string",
      "name": "string",
      "position": "string|null",
      "team": "string|null",
      "status": "string|null",
      "trend_direction": "string|null",
      "trend_reason": "string|null"
    }
  ],
  "total_players": "integer"
}
```

#### get_player_stats
Get player statistics for a specific season.

**Endpoint:** `POST /tools/get_player_stats`

**Input Schema:**
```json
{
  "arguments": {
    "player_id": "string (required)",
    "season": "string (optional, default: '2024')"
  }
}
```

**Output Schema:**
```json
{
  "player_id": "string",
  "player_name": "string|null",
  "position": "string|null",
  "team": "string|null",
  "season": "string",
  "stats": {
    "stat_name": "number|null"
  },
  "total_stats": "integer"
}
```

### Matchup Tools

#### get_matchups
Get matchups for a specific week in a league.

**Endpoint:** `POST /tools/get_matchups`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)",
    "week": "integer (required, min: 1, max: 22)"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "week": "integer",
  "matchups": [
    {
      "matchup_id": "integer|null",
      "roster_id": "integer",
      "points": "number|null",
      "players": ["string"],
      "starters": ["string"],
      "reserve": ["string"],
      "taxi": ["string"]
    }
  ],
  "total_matchups": "integer"
}
```

#### get_matchup_scores
Get real-time scoring information for matchups in a specific week.

**Endpoint:** `POST /tools/get_matchup_scores`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)",
    "week": "integer (required, min: 1, max: 22)"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "week": "integer",
  "matchups": [
    {
      "matchup_id": "integer|null",
      "roster_id": "integer",
      "points": "number|null",
      "starters_points": "number",
      "bench_points": "number"
    }
  ],
  "total_matchups": "integer"
}
```

### Trade Tools

#### analyze_trade_targets
Analyze potential trade targets for a roster based on positional needs.

**Endpoint:** `POST /tools/analyze_trade_targets`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)",
    "roster_id": "integer (required)",
    "position": "string (optional, enum: ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'])"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "roster_id": "integer",
  "position": "string|null",
  "target_teams": ["object"],
  "suggested_trades": ["object"],
  "positional_needs": "object",
  "trade_value_analysis": "object"
}
```

#### evaluate_roster_needs
Evaluate roster strengths and weaknesses across all positions.

**Endpoint:** `POST /tools/evaluate_roster_needs`

**Input Schema:**
```json
{
  "arguments": {
    "league_id": "string (required)",
    "roster_id": "integer (required)"
  }
}
```

**Output Schema:**
```json
{
  "league_id": "string",
  "roster_id": "integer",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "recommendations": ["string"],
  "positional_analysis": "object",
  "overall_grade": "string"
}
```

## Example Usage

### Single Tool Call

```bash
curl -X POST http://localhost:8000/tools/get_user_leagues \
  -H "Content-Type: application/json" \
  -d '{
    "arguments": {
      "username": "sleeper",
      "season": "2024"
    }
  }'
```

### Batch Tool Call

```bash
curl -X POST http://localhost:8000/tools/batch \
  -H "Content-Type: application/json" \
  -d '{
    "tools": [
      {
        "name": "get_user_leagues",
        "arguments": {"username": "sleeper"}
      },
      {
        "name": "search_players", 
        "arguments": {"query": "Josh Allen"}
      }
    ]
  }'
```

## Error Handling

When a tool call fails, the response will have:
- `success: false`
- `result: null`
- `error: "Error description"`

Common error scenarios:
- Invalid league ID: `"League 'ID' not found"`
- Invalid player ID: `"Player not found"`
- API rate limiting: `"Rate limit exceeded"`
- Network issues: `"Failed to retrieve data"`

## Integration Examples

### Python
```python
import requests

response = requests.post(
    "http://localhost:8000/tools/get_user_leagues",
    json={"arguments": {"username": "sleeper"}}
)

data = response.json()
if data["success"]:
    leagues = data["result"]["leagues"]
    print(f"Found {len(leagues)} leagues")
else:
    print(f"Error: {data['error']}")
```

### JavaScript
```javascript
const response = await fetch('http://localhost:8000/tools/search_players', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    arguments: {query: 'Josh Allen'}
  })
});

const data = await response.json();
if (data.success) {
  console.log(`Found ${data.result.total_players} players`);
} else {
  console.error(`Error: ${data.error}`);
}
```

## Schema Validation

All responses are validated against their declared output schemas. The schemas use JSON Schema format and support:
- Type validation (`string`, `integer`, `number`, `boolean`, `array`, `object`)
- Null values (`string|null`)
- Array item validation
- Required vs optional fields

For the most up-to-date schemas, query the `/tools` endpoint which returns the complete tool definitions with input and output schemas.

