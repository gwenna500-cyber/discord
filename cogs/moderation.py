import discord
from discord import app_commands
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear", description="ล้างข้อความในห้องแชท (เฉพาะแอดมิน)")
    @app_commands.describe(amount="จำนวนข้อความที่ต้องการลบ (ค่าเริ่มต้นคือ 10, สูงสุด 100)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = 10):
        # Prevent deleting too many messages at once to avoid API rate limits/errors
        if amount > 100:
            amount = 100
        elif amount < 1:
            amount = 1
            
        await interaction.response.defer(ephemeral=True)
        
        try:
            # We add 1 to amount if we were deleting a command message, but slash commands don't leave messages.
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f"✅ ลบข้อความจำนวน {len(deleted)} ข้อความเรียบร้อยแล้วครับ", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ บอทไม่มีสิทธิ์ในการลบข้อความในห้องนี้ครับ", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
