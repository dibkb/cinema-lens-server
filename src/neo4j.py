from typing import Dict, Any

def process_result(result:Dict[str,Any]):
    target = result.get("target", {})
    connections = result.get("connections", [])
     
    # Use list comprehensions for better performance
    actors = [conn["connected"]["name"] for conn in connections 
              if conn.get("direction") == "OUTGOING" and conn.get("relationship") == "ACTED_IN"]
    
    directors = [conn["connected"]["name"] for conn in connections 
                if conn.get("direction") == "OUTGOING" and conn.get("relationship") == "DIRECTED_BY"]
    
    genres = [conn["connected"]["name"] for conn in connections 
             if conn.get("direction") == "OUTGOING" and conn.get("relationship") == "HAS_GENRE"]
    
    # Use next() with generator expression for year lookup
    year = next((conn["connected"]["year"] for conn in connections 
                 if conn.get("direction") == "OUTGOING" and conn.get("relationship") == "RELEASED_IN"), None)
    
    return {
        **target,
        "actors": actors,
        "directors": directors,
        "genres": genres,
        "year": year
    }

