import logging
from pydantic import BaseModel, Field
from typing import List
import praw
from .config import settings
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedditResult(BaseModel):
    movies: List[str] = Field(description="List of movies from the site")
    site_url: str = Field(description="URL of the site")

class RedditPost:
    def __init__(self, url):
        self.id = self.extract_id(url)
        self.comments = []
        self.client  = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_SECRET,
            user_agent='script:myapp:v1.0 (by /u/dibkb)'
        )

    def extract_id(self,url):
        # https://www.reddit.com/r/movies/comments/111uty4/what_movies_are_on_par_with_interstellar/
        parts = url.split("/comments/")
        if len(parts) > 1:
            id = parts[1].split("/")[0]
            return id if id else None
        return None
    def get_comments(self):
        if len(self.comments) > 0:
            return self.comments
        
        submission = self.client.submission(id=self.id)
        submission.comments.replace_more(limit=10)
        for comment in submission.comments.list():
            self.comments.append(comment.body)
            if len(self.comments) == 6:
                break

        return self.comments

    


