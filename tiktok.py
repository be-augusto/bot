import os
from dotenv import load_dotenv
import discord
import asyncio
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME")

last_video_url = None

def initialize_browser():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return browser

from selenium.common.exceptions import TimeoutException, NoSuchElementException

def get_latest_tiktok_url(browser):
    latest_non_pinned_video = None
    try:
        browser.get(f"https://www.tiktok.com/@{TIKTOK_USERNAME}")

        # Wait for the video elements to be present on the page
        WebDriverWait(browser, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[href*="/video/"]')))
        
        # Get video elements
        video_elements = browser.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        
        # Use a set to track URLs to avoid processing duplicates
        seen_urls = set()
        
        for video in video_elements:
            # Scroll into view to ensure the element is fully rendered
            browser.execute_script("arguments[0].scrollIntoView(true);", video)
            
            # Ensure the video element is visible
            WebDriverWait(browser, 5).until(EC.visibility_of(video))
            
            video_url = video.get_attribute('href')
            
            # Skip if URL has been seen before
            if video_url in seen_urls:
                continue
            
            seen_urls.add(video_url)
            
            # Check for pinned badge
            try:
                pinned_badge_elements = video.find_elements(By.CSS_SELECTOR, 'div[data-e2e="video-card-badge"]')
                is_pinned = bool(pinned_badge_elements)
                
                if is_pinned:
                    continue  # Skip this video if it's pinned
                
                # If no pinned badge was found, consider this video
                latest_non_pinned_video = video_url
                break  # Stop after finding the first non-pinned video
            
            except NoSuchElementException:
                # Handle cases where the pinned badge is not found
                # If no pinned badge is found, consider this video
                latest_non_pinned_video = video_url
                break
    
    except TimeoutException:
        print("TimeoutException: Failed to load video elements within the timeout period.")
        # Optionally: You can return a placeholder or log an error if needed

    return latest_non_pinned_video




async def monitor_tiktok(channel):
    global last_video_url
    browser = initialize_browser()
    
    while True:
        latest_video_url = get_latest_tiktok_url(browser)
        
        if latest_video_url and latest_video_url != last_video_url:
            last_video_url = latest_video_url
            await channel.send(f'@everyone Novo TikTok Postado pela {TIKTOK_USERNAME}! Bora Ver Galera: {latest_video_url}')
        
        await asyncio.sleep(30)  # Check every hour

class MyClient(discord.Client):
    
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        channel = self.get_channel(CHANNEL_ID)
        
        if channel:
            await monitor_tiktok(channel)

client = MyClient(intents=discord.Intents.default())
client.run(TOKEN)
