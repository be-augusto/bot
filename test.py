import os
from dotenv import load_dotenv
import discord
import asyncio
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
TARGET_PROFILE = os.getenv('INSTAGRAM_USER')

last_video_url = None
last_reel_url = None
browser = None
current_url = None

def initialize_browser():
    global browser
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
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

def get_latest_tiktok_url(browser):
    global last_video_url
    latest_non_pinned_video = None
    try:
        browser.get(f"https://www.tiktok.com/@{TIKTOK_USERNAME}")

        WebDriverWait(browser, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[href*="/video/"]')))

        video_elements = browser.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')

        seen_urls = set()

        for video in video_elements:
            browser.execute_script("arguments[0].scrollIntoView(true);", video)
            WebDriverWait(browser, 5).until(EC.visibility_of(video))
            video_url = video.get_attribute('href')

            if video_url in seen_urls:
                continue

            seen_urls.add(video_url)

            try:
                pinned_badge_elements = video.find_elements(By.CSS_SELECTOR, 'div[data-e2e="video-card-badge"]')
                is_pinned = bool(pinned_badge_elements)
                
                if is_pinned:
                    continue
                
                latest_non_pinned_video = video_url
                break

            except NoSuchElementException:
                latest_non_pinned_video = video_url
                break

    except TimeoutException:
        print("TimeoutException: Failed to load video elements within the timeout period.")

    return latest_non_pinned_video

def get_latest_reel_url():
    global browser
    global current_url
    
    if current_url:
        browser.get(current_url)
    else:
        current_url = f"https://www.instagram.com/{TARGET_PROFILE}/reels/"
        browser.get(current_url)
    
    retries = 3
    while retries > 0:
        try:
            WebDriverWait(browser, 15).until(
                EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "/reel/")]'))
            )
            
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            reel_elements = browser.find_elements(By.XPATH, '//a[contains(@href, "/reel/")]')
            latest_reel_url = reel_elements[0].get_attribute('href') if reel_elements else None
            
            if not latest_reel_url:
                print("No reels found.")
            
            return latest_reel_url
        
        except TimeoutException as e:
            print(f"TimeoutException: Attempt {4 - retries} failed. {e}")
            retries -= 1
            if retries > 0:
                print("Retrying...")
    
    print("Failed to retrieve latest reel URL after several attempts.")
    return None

async def monitor_social_media(channel):
    global last_video_url
    global last_reel_url

    while True:
        # Monitor TikTok
        latest_video_url = get_latest_tiktok_url(browser)
        if latest_video_url and latest_video_url != last_video_url:
            last_video_url = latest_video_url
            await channel.send(f'@everyone Novo TikTok Postado pela {TIKTOK_USERNAME}! Bora Ver Galera: {latest_video_url}')
        
        await asyncio.sleep(30)  # Wait 30 seconds before switching

        # Monitor Instagram
        latest_reel_url = get_latest_reel_url()
        if latest_reel_url and latest_reel_url != last_reel_url:
            last_reel_url = latest_reel_url
            await channel.send(f'@everyone Novo Reels Postado pela {TARGET_PROFILE}! Bora ver galera: {latest_reel_url}')
        
        await asyncio.sleep(30)  # Wait 30 seconds before switching

class MyClient(discord.Client):
    
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, *args, **kwargs)
    
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        channel = self.get_channel(CHANNEL_ID)
        if channel:
            initialize_browser()
            await monitor_social_media(channel)

client = MyClient()
client.run(TOKEN)
