import os
from dotenv import load_dotenv
import discord
import asyncio
from selenium import webdriver
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
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
TARGET_PROFILE = 'stelaryss'

last_reel_url = None
browser = None
current_url = None

def initialize_browser():
    global browser
    options = Options()
    options.add_argument("--incognito")
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # Log in to Instagram
    browser.get("https://www.instagram.com/accounts/login/")
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.NAME, 'username')))
    
    username_field = browser.find_element(By.NAME, 'username')
    password_field = browser.find_element(By.NAME, 'password')
    login_button = browser.find_element(By.XPATH, '//button[@type="submit"]')
    
    username_field.send_keys(INSTAGRAM_USERNAME)
    password_field.send_keys(INSTAGRAM_PASSWORD)
    login_button.click()
    
    # Wait for login to complete
    WebDriverWait(browser, 15).until(EC.url_changes("https://www.instagram.com/accounts/login/"))

def get_latest_reel_url():
    global browser
    global current_url
    
    # Navigate to the URL if needed
    if current_url:
        browser.get(current_url)
    else:
        current_url = f"https://www.instagram.com/{TARGET_PROFILE}/reels/"
        browser.get(current_url)
    
    # Wait for the profile page to load
    WebDriverWait(browser, 15).until(EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/reel/")]')))
    
    # Scroll down to load more content if needed
    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    try:
        reel_elements = browser.find_elements(By.XPATH, '//a[contains(@href, "/reel/")]')
        latest_reel_url = reel_elements[0].get_attribute('href') if reel_elements else None
    except Exception as e:
        print(f"Error finding reels: {e}")
        latest_reel_url = None
    
    return latest_reel_url

async def monitor_instagram(channel):
    global last_reel_url
    global current_url
    
    while True:
        latest_reel_url = get_latest_reel_url()
        
        if latest_reel_url and latest_reel_url != last_reel_url:
            last_reel_url = latest_reel_url
            print(f'New Reel posted: {latest_reel_url}')
            
            # Send a message in Discord mentioning everyone
            await channel.send(f'@everyone Novo Reels Postado pela {TARGET_PROFILE}! Bora ver galera: {latest_reel_url}')

                
        # Wait before checking again
        await asyncio.sleep(30)  # Wait for 1 hour before reloading

class MyClient(discord.Client):
    
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, *args, **kwargs)
    
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        
        guild = self.get_guild(GUILD_ID)
        if guild is None:
            print(f'Guild with the ID {GUILD_ID} not found.')
            return
        
        channel = self.get_channel(CHANNEL_ID)
        if channel is None:
            print(f'Channel with the ID {CHANNEL_ID} not found.')
            return
        
        # Initialize the browser and log in
        initialize_browser()
        
        # Start monitoring the Instagram profile
        await monitor_instagram(channel)

client = MyClient()
client.run(TOKEN)