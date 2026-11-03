import os
import requests
import ndjson

class LichessClient:
    """
    Client for interacting with the Lichess API.
    
    This class handles fetching user games and parsing the NDJSON response.
    """
    
    def __init__(self):
        """Initialize the LichessClient."""
        self.base_url = "https://lichess.org/api"
        # Optional personal API token (lichess.org/account/oauth/token, no scopes needed)
        self.token = os.getenv("LICHESS_TOKEN")
        self.last_error = None

    def _headers(self):
        """Build request headers, adding the auth token when one is set."""
        headers = {'Accept': 'application/x-ndjson'}
        if self.token:
            headers['Authorization'] = f"Bearer {self.token}"
        return headers

    def get_user_games(self, username, max_games=100):
        """
        Fetch recent games for a specific user.
        
        Args:
            username (str): The Lichess username to fetch games for.
            max_games (int): The maximum number of games to retrieve (default: 100).
            
        Returns:
            list: A list of game dictionaries. Returns an empty list if the request fails.
        """
        # Endpoint for fetching games by user
        url = f"{self.base_url}/games/user/{username}"
        
        # Parameters for the API request
        params = {
            'max': max_games,      # Limit number of games
            'perfType': 'blitz,rapid,bullet,classical', # Filter by game types
            'opening': 'true',     # Include opening information
            'rated': 'true',       # Only include rated games
            'clocks': 'true',      # Enable clock data for time management
            'evals': 'true'        # Enable analysis data for accuracy metrics
        }
        
        try:
            # Make the GET request to Lichess API
            response = requests.get(url, params=params, headers=self._headers())
            response.raise_for_status() # Raise an error for bad status codes (4xx, 5xx)
            
            # Parse the NDJSON (Newline Delimited JSON) response
            # Lichess returns multiple JSON objects separated by newlines
            games = response.json(cls=ndjson.Decoder)
            return games
            
        except requests.exceptions.RequestException as e:
            status = getattr(e.response, 'status_code', None)
            body = e.response.text[:200] if e.response is not None else ''
            self.last_error = f"{status or type(e).__name__}: {body or e} (token {'sent' if self.token else 'not set'})"
            print(f"Error fetching games: {self.last_error}")
            return []

    def get_games_by_ids(self, game_ids):
        """
        Fetch specific games by ID (Batch).
        
        Args:
            game_ids (list): List of game IDs.
            
        Returns:
            list: List of game dictionaries.
        """
        if not game_ids:
            return []
            
        url = f"{self.base_url}/games/export/_ids"
        
        params = {
            'clocks': 'true',
            'evals': 'true',
            'opening': 'true'
        }
        
        # Limit to 300 IDs per request (Lichess limit)
        # We will just do one batch for now or loop if needed.
        # But for simplicity, let's assume the caller handles batching or we do it here.
        # Let's do simple request here.
        
        try:
            # Join IDs with comma
            ids_str = ",".join(game_ids)
            response = requests.post(url, params=params, headers=self._headers(), data=ids_str)
            response.raise_for_status()
            games = response.json(cls=ndjson.Decoder)
            return games
        except Exception as e:
            print(f"Error fetching games by ID: {e}")
            return []

if __name__ == "__main__":
    # Test the client
    client = LichessClient()
    games = client.get_user_games("DrNykterstein", max_games=5)
    print(f"Fetched {len(games)} games.")
    if games:
        print(games[0].keys())
