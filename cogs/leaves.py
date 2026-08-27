import discord
from discord import app_commands
from discord.ext import commands
import sys
import os
from datetime import datetime
import pytz

# Add parent directory to path so we can import firebase_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firebase_config import get_db

class Leaves(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = get_db()
        except Exception as e:
            print(f"Error initializing Firebase in Leaves: {e}")
            self.db = None

    @app_commands.command(name="leave", description="ยื่นคำร้องขอลา")
    @app_commands.describe(
        character_name="ชื่อตัวละคร",
        duration="จำนวนวันที่ต้องการลา",
        reason="เหตุผลการลา"
    )
    @app_commands.choices(duration=[
        app_commands.Choice(name="1 วัน", value=1),
        app_commands.Choice(name="3 วัน", value=3),
        app_commands.Choice(name="7 วัน", value=7)
    ])
    async def request_leave(self, interaction: discord.Interaction, character_name: str, duration: int, reason: str):
        if not self.db:
            await interaction.response.send_message("Database not initialized.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        tz = pytz.timezone('Asia/Bangkok')
        now = datetime.now(tz)
        
        self.db.collection('leaves').add({
            'user_id': user_id,
            'character_name': character_name,
            'duration': duration,
            'reason': reason,
            'timestamp': now,
            'status': 'Pending'
        })
            
        embed = discord.Embed(title="📝 ส่งคำร้องขอลาสำเร็จ", color=discord.Color.orange())
        embed.add_field(name="ชื่อตัวละคร", value=character_name, inline=True)
        embed.add_field(name="ผู้ยื่นเรื่อง (Discord)", value=interaction.user.mention, inline=True)
        embed.add_field(name="จำนวนวันลา", value=f"{duration} วัน", inline=False)
        embed.add_field(name="เหตุผล", value=reason, inline=False)
        embed.add_field(name="สถานะ", value="⏳ รออนุมัติวันลา", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="my_leaves", description="ดูประวัติการลาของคุณ")
    async def my_leaves(self, interaction: discord.Interaction):
        if not self.db:
            await interaction.response.send_message("Database not initialized.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        
        leaves_ref = self.db.collection('leaves').where('user_id', '==', user_id).stream()
        leaves_list = list(leaves_ref)
        
        if not leaves_list:
            await interaction.response.send_message("คุณยังไม่มีประวัติการลาครับ", ephemeral=True)
            return
            
        embed = discord.Embed(title="ประวัติการลาของคุณ", color=discord.Color.blue())
        # Display up to 5 recent leaves
        for doc in leaves_list[:5]:
            data = doc.to_dict()
            char_name = data.get('character_name', 'ไม่ระบุ')
            duration = data.get('duration', '?')
            status = data.get('status', 'Pending')
            
            status_emoji = "⏳" if status == "Pending" else ("✅" if status == "Approved" else "❌")
            embed.add_field(name=f"ตัวละคร: {char_name}", value=f"ลา {duration} วัน\nสถานะ: {status_emoji} {status}", inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Leaves(bot))
