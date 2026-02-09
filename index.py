# index.py - FastAPI for Vercel deployment
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
import json
import os

# Create FastAPI app
app = FastAPI(
    title="NBA Player Skills API",
    description="Get NBA players' best skills based on statistical z-scores",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Load player data from JSON file
def load_players():
    """Load player data from JSON file"""
    try:
        # Vercel path: players.json is in parent directory of api/
        json_path = os.path.join(os.path.dirname(__file__), '..', 'players.json')
        with open(json_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: players.json not found")
        return []

# Global variable to store player data
players_data = load_players()

@app.get("/")
def read_root():
    """Root endpoint - API information"""
    return {
        "name": "NBA Player Skills API",
        "version": "1.0.0",
        "description": "Get NBA players' best skills based on z-scores",
        "total_players": len(players_data),
        "endpoints": {
            "GET /": "This help page",
            "GET /player/{name}": "Search for player by name",
            "GET /players": "List all players (with pagination)",
            "GET /player_id/{id}": "Get player by exact Player_ID",
            "GET /skills": "Get summary of best skills distribution",
            "GET /health": "Health check endpoint",
            "GET /docs": "Interactive API documentation"
        },
        "examples": {
            "search": "/player/LeBron",
            "list": "/players?limit=20&offset=0",
            "by_id": "/player_id/2544"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "players_loaded": len(players_data)
    }

@app.get("/player/{name}")
def get_player(name: str):
    """
    Search for a player by name (case-insensitive, partial match)

    Args:
        name: Player name or partial name to search for

    Returns:
        Player data including best skill, raw value, and z-score
    """
    # Search for matching players (case-insensitive)
    matches = [
        player for player in players_data
        if name.lower() in player['name'].lower()
    ]

    if len(matches) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No players found matching '{name}'"
        )

    if len(matches) == 1:
        return {
            "status": "success",
            "count": 1,
            "data": matches[0]
        }
    else:
        return {
            "status": "success",
            "count": len(matches),
            "message": f"Found {len(matches)} players matching '{name}'",
            "data": matches
        }

@app.get("/players")
def get_all_players(
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    skill: Optional[str] = None
):
    """
    Get all players with pagination and optional filtering

    Args:
        limit: Number of players to return (default: 50, max: 100)
        offset: Number of players to skip (default: 0)
        skill: Filter by best skill (e.g., 'PTS', 'AST', 'REB')

    Returns:
        List of players with their best skills
    """
    # Limit the maximum to prevent overload
    limit = min(limit, 100)

    # Filter by skill if provided
    if skill:
        filtered_players = [
            p for p in players_data
            if p.get('best_skill', '').upper() == skill.upper()
        ]
    else:
        filtered_players = players_data

    # Apply pagination
    start = offset
    end = offset + limit
    paginated = filtered_players[start:end]

    return {
        "status": "success",
        "total_players": len(filtered_players),
        "showing": len(paginated),
        "offset": offset,
        "limit": limit,
        "filter": {"skill": skill} if skill else None,
        "data": paginated
    }

@app.get("/player_id/{player_id}")
def get_player_by_id(player_id: str):
    """
    Get player by exact Player_ID

    Args:
        player_id: Exact NBA Player ID (e.g., '2544' for LeBron James)

    Returns:
        Player data including best skill
    """
    match = next(
        (player for player in players_data if player['player_id'] == player_id),
        None
    )

    if match is None:
        raise HTTPException(
            status_code=404,
            detail=f"Player ID '{player_id}' not found"
        )

    return {
        "status": "success",
        "data": match
    }

@app.get("/skills")
def get_skills_summary():
    """
    Get summary of how many players excel at each skill

    Returns:
        Dictionary with skill counts and percentages
    """
    skills_count = {}
    for player in players_data:
        skill = player.get('best_skill', 'Unknown')
        skills_count[skill] = skills_count.get(skill, 0) + 1

    # Calculate percentages
    total = len(players_data)
    skills_with_percentage = {
        skill: {
            "count": count,
            "percentage": round((count / total) * 100, 2) if total > 0 else 0
        }
        for skill, count in sorted(skills_count.items(), key=lambda x: x[1], reverse=True)
    }

    return {
        "status": "success",
        "total_players": total,
        "skills": skills_with_percentage
    }

@app.get("/top/{skill}")
def get_top_by_skill(skill: str, limit: int = 10):
    """
    Get top players for a specific skill

    Args:
        skill: Skill name (e.g., 'PTS', 'AST', 'REB')
        limit: Number of top players to return (default: 10)

    Returns:
        Top players sorted by z-score for that skill
    """
    # Filter players by skill and sort by z-score
    skill_players = [
        p for p in players_data
        if p.get('best_skill', '').upper() == skill.upper()
    ]

    if not skill_players:
        raise HTTPException(
            status_code=404,
            detail=f"No players found with '{skill}' as their best skill"
        )

    # Sort by z-score (descending)
    sorted_players = sorted(
        skill_players,
        key=lambda x: x.get('z_score', 0),
        reverse=True
    )[:limit]

    return {
        "status": "success",
        "skill": skill.upper(),
        "showing": len(sorted_players),
        "data": sorted_players
    }
