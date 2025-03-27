import requests
import logging
from pydantic import BaseModel, Field
from typing import List
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedditResult(BaseModel):
    movies: List[str] = Field(description="List of movies from the site")
    site_url: str = Field(description="URL of the site")

class RedditPost:
    def __init__(self, url):
        self.url = url + ".json"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1'
        }
        self.comments = []

    def get_comments(self):
        if len(self.comments) > 0:
            return self.comments
        
        response = requests.get(self.url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            comments = data[1]['data']['children']
            
            for comment in comments:
                comment_body = comment['data'].get('body')
                if comment_body:
                    self.comments.append(comment_body.strip())
                    if len(self.comments) == 6:
                        break
            return self.comments
        else:
            logger.error(f"Failed to fetch data: {response.status_code}")
            return self.comments


    


