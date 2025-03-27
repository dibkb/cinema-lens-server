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
        self.url = url if url.endswith('.json') else url + ".json"
        self.headers = {
            'User-Agent': 'CinemaLens/1.0 (Contact: your@email.com)',
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
        
        logger.info(f"Attempting to fetch comments from: {self.url}")
        response = requests.get(self.url, headers=self.headers)
        
        logger.info(f"Response status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Response data structure: {data[1]['data'].keys() if len(data) > 1 else 'No data'}")
            
            comment_data = data[1]['data']['children']
            logger.info(f"Number of comments found: {len(comment_data)}")
            
            for comment in comment_data:
                comment_body = comment['data'].get('body')
                if comment_body:
                    self.comments.append(comment_body.strip())
                    logger.info(f"Added comment, current count: {len(self.comments)}")
                    if len(self.comments) == 6:
                        break
        else:
            logger.error(f"Failed to fetch data: {response.status_code}")
            logger.error(f"Response content: {response.text}")
        
        return self.comments


    


