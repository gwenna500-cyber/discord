import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Setup intents (we need message content and members intent)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialize bot
class MedicalBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!', 
            intents=intents,
            help_command=commands.DefaultHelpCommand(no_category='Commands')
        )

    async def setup_hook(self):
        # Load cogs dynamically
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        
        # Sync slash commands
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

bot = MedicalBot()

from keep_alive import keep_alive

if __name__ == '__main__':
    if not TOKEN:
        print("Error: DISCORD_TOKEN is missing. Please set it in your .env file.")
    else:
        keep_alive()
        bot.run(TOKEN)
