import os
import discord
import feedparser
import asyncio
from discord.ext import tasks
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv() # Load environment variables from .env file
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

# List of RSS feeds to check
RSS_FEEDS = [
    'https://feeds.feedburner.com/TheHackersNews',
    'https://www.bleepingcomputer.com/feed/',
    'https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml',
    # Add your custom Google Alerts RSS feed URL here
]

# Keyword to search for (case-insensitive)
KEYWORD = 'bluetooth'

# --- Bot Setup ---

# We need to track which articles we've already posted
# In a real production bot, you'd use a database (like SQLite) for this
posted_articles = set()

# Set up the bot's intents (permissions)
intents = discord.Intents.default()
intents.message_content = True # Needed for commands, good practice to have
client = discord.Client(intents=intents)

# --- Core Logic ---

@tasks.loop(minutes=10) # Run this task every 10 minutes
async def check_for_news():
    print("Checking for new Bluetooth security news...")
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
                    # Check if we've already posted this article link
                    if entry.link not in posted_articles:
                        print(f"Found new article: {entry.title}")
                        
                        # Format the message using a Discord Embed for a nicer look
                        embed = discord.Embed(
                            title=f"**{entry.title}**",
                            url=entry.link,
                            description=entry.summary[:400] + "..." if len(entry.summary) > 400 else entry.summary,
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text=f"Source: {feed.feed.title}")
                        
                        await channel.send(embed=embed)
                        
                        # Add the link to our set of posted articles
                        posted_articles.add(entry.link)
                        
                        # Wait a little bit to avoid spamming the Discord API
                        await asyncio.sleep(1) 
        except Exception as e:
            print(f"Error fetching or parsing feed {feed_url}: {e}")

# --- Bot Events ---

@client.event
async def on_ready():
    """This function runs when the bot successfully connects to Discord."""
    print(f'{client.user} has connected to Discord!')
    # Start the background task
    check_for_news.start()

# --- Run the Bot ---
client.run(TOKEN)