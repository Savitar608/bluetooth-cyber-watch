import os
import discord
import feedparser
import asyncio
import sqlite3
from discord.ext import tasks
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv() # Load environment variables from .env file
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
DB_FILE = 'news.db' # Name for our SQLite database file

# List of RSS feeds to check
RSS_FEEDS = [
    'https://feeds.feedburner.com/TheHackersNews',
    'https://www.bleepingcomputer.com/feed/',
    'https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml',
    # Add your custom Google Alerts RSS feed URL here
]

# Keyword to search for (case-insensitive)
KEYWORD = 'bluetooth'

# --- Database Functions ---

def setup_database():
    """Create the database and the articles table if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Create a table to store posted article links.
    # The link is the PRIMARY KEY to prevent duplicates and speed up lookups.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            link TEXT PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()
    print("Database setup complete.")

def is_article_posted(link):
    """Check if an article link already exists in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT link FROM articles WHERE link = ?", (link,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_posted_article(link):
    """Add a new article link to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Using 'INSERT OR IGNORE' is a safe way to handle potential race conditions
    cursor.execute("INSERT OR IGNORE INTO articles (link) VALUES (?)", (link,))
    conn.commit()
    conn.close()

# --- Bot Setup ---
intents = discord.Intents.default()
# intents.message_content = True # Needed for commands, good practice to have. Is this really needed here?
client = discord.Client(intents=intents)

# --- Core Logic ---

@tasks.loop(minutes=10)
async def check_for_news():
    print(f"[{discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Checking for news...")
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Error: Channel with ID {CHANNEL_ID} not found.")
        return

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                # Check if the keyword is in the title or summary
                title_lower = entry.title.lower()
                summary_lower = entry.summary.lower()
                
                if KEYWORD in title_lower or KEYWORD in summary_lower:
                    # Check the DATABASE instead of the in-memory set
                    if not is_article_posted(entry.link):
                        print(f"Found new article: {entry.title}")
                        
                        embed = discord.Embed(
                            title=f"**{entry.title}**",
                            url=entry.link,
                            description=entry.summary[:400] + "..." if len(entry.summary) > 400 else entry.summary,
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text=f"Source: {feed.feed.title}")
                        
                        await channel.send(embed=embed)
                        
                        # Add the link to the DATABASE
                        add_posted_article(entry.link)
                        
                        await asyncio.sleep(1)
        except Exception as e:
            print(f"Error fetching or parsing feed {feed_url}: {e}")

# --- Bot Events ---

@client.event
async def on_ready():
    """Runs when the bot connects to Discord."""
    print(f'{client.user} has connected to Discord!')
    # Set up the database before starting the news check loop
    setup_database()
    check_for_news.start()

# --- Run the Bot ---
client.run(TOKEN)