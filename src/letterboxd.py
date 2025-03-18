import httpx
from bs4 import BeautifulSoup
from typing import Optional, List


class Letterboxd:
    def __init__(self, url: str):
        self.url = url
        self.soup = self._get_soup()

    def _get_soup(self) -> Optional[BeautifulSoup]:
        try:
            response = httpx.get(self.url, timeout=10)
            response.raise_for_status()  
            return BeautifulSoup(response.text, 'html.parser')
        except httpx.RequestError as e:
            print(f"Network error while fetching the page: {str(e)}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"HTTP error while fetching the page: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error while fetching the page: {str(e)}")
            return None
        
    def get_movies(self) -> List[str]:
        if not self.soup:
            print("No valid HTML content available")
            return []
            
        movies = []
        for movie in self.soup.find_all('li', class_='poster-container'):
            div = movie.find('div', class_='film-poster')
            if div:
                title = div.find('img')
                if title and title.get('alt'):
                    movies.append(title.get('alt'))
        return movies
    
    
    
    
    