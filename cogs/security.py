import discord
from discord.ext import commands
import re

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Basic regex to catch potential Hospital Numbers (HN) or Thai National ID patterns.
        # This is very basic and should be adapted to the organization's specific data formats.
        self.hn_pattern = re.compile(r'\bHN\d{5,}\b', re.IGNORECASE)
        self.id_card_pattern = re.compile(r'\b\d{1}-\d{4}-\d{5}-\d{2}-\d{1}\b')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot's own messages
        if message.author.bot:
            return

        # Check for potential PHI patterns
        content = message.content
        if self.hn_pattern.search(content) or self.id_card_pattern.search(content):
            # Warn the user and potentially delete the message
            try:
                await message.delete()
                warning_msg = (
                    f"⚠️ {message.author.mention} **WARNING:** Your message was deleted because it appeared to contain "
                    f"sensitive patient information (like an HN or ID number). "
                    f"Please remember that Discord is NOT secure for patient data (PHI/PDPA). "
                    f"Use the official hospital systems for this information."
                )
                await message.channel.send(warning_msg, delete_after=15)
                
                # Optionally, log this to an admin channel
                # admin_channel = discord.utils.get(message.guild.text_channels, name='security-logs')
                # if admin_channel:
                #     await admin_channel.send(f"⚠️ User {message.author} attempted to post potential PHI in {message.channel.mention}.")
                    
            except discord.Forbidden:
                # The bot doesn't have permissions to delete messages
                pass

async def setup(bot):
    await bot.add_cog(Security(bot))
