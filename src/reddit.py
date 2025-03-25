from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
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
        self.url = url
        self.html = None
        self.title = None
        self.driver = None
        self.comments = []

    def initialize(self):
        try:
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--window-size=1280,800')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(6)

            logger.info(f"Navigating to {self.url}")
            self.driver.get(self.url)

            # Wait for title element
            logger.info("Waiting for title element")
            wait = WebDriverWait(self.driver, 6)
            title_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[slot="title"]'))
            )

            self.title = title_element.text
            self.html = self.driver.page_source

        except Exception as e:
            logger.error(f"Error during initialization: {str(e)}")
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
            raise
        finally:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()

    def get_html(self):
        return self.html
    
    def get_comments(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        comments = soup.find_all('div', attrs={'slot': 'comment'})
        for comment in comments:
            if(comment.find('p')):
                self.comments.append(comment.find('p').text.strip())
        return self.comments
    
    def get_title(self):
        return self.title.strip() if self.title else None
    


