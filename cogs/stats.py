import discord
from discord import app_commands
from discord.ext import commands
import sys
import os
from datetime import datetime
import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firebase_config import get_db

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = get_db()
        except Exception:
            self.db = None
        self.tz = pytz.timezone('Asia/Bangkok')

    def calculate_leaderboard_embed(self) -> discord.Embed:
        if not self.db:
            return discord.Embed(title="❌ Database Error", description="ไม่สามารถดึงข้อมูลได้", color=discord.Color.red())
            
        shifts_ref = self.db.collection('shifts')
        completed_shifts = shifts_ref.where('status', '==', 'completed').stream()
        
        doctor_stats = {}
        for shift in completed_shifts:
            data = shift.to_dict()
            user_id = data.get('user_id')
            discord_name = data.get('discord_name', 'Unknown')
            char_name = data.get('character_name', 'ไม่ระบุ')
            duration = data.get('duration_seconds', 0)
            
            if user_id not in doctor_stats:
                doctor_stats[user_id] = {
                    'discord_name': discord_name,
                    'char_name': char_name,
                    'total_seconds': 0,
                    'shift_count': 0
                }
                
            doctor_stats[user_id]['total_seconds'] += duration
            doctor_stats[user_id]['shift_count'] += 1
            
        # Sort by total_seconds descending
        sorted_doctors = sorted(doctor_stats.values(), key=lambda x: x['total_seconds'], reverse=True)
        
        embed = discord.Embed(
            title="🏆 ทำเนียบแพทย์ขยัน (Live Leaderboard)",
            description="สรุปเวลาการเข้าเวรทั้งหมดของโรงพยาบาล อัปเดตแบบเรียลไทม์!",
            color=discord.Color.gold(),
            timestamp=datetime.now(self.tz)
        )
        
        if not sorted_doctors:
            embed.add_field(name="ยังไม่มีข้อมูล", value="ยังไม่มีประวัติการออกเวรในระบบครับ", inline=False)
            return embed
            
        medal_emojis = ["🥇", "🥈", "🥉"]
        
        for i, doc in enumerate(sorted_doctors[:10]): # Top 10
            rank = medal_emojis[i] if i < 3 else f"**#{i+1}**"
            
            total_secs = doc['total_seconds']
            hours, remainder = divmod(total_secs, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{int(hours)} ชม. {int(minutes)} น. {int(seconds)} วิ."
            
            embed.add_field(
                name=f"{rank} {doc['char_name']}",
                value=f"👤 Discord: {doc['discord_name']}\n⏱️ เวลารวม: **{time_str}**\n🏥 เข้าเวรไปแล้ว: {doc['shift_count']} ครั้ง",
                inline=False
            )
            
        embed.set_footer(text="อัปเดตล่าสุด")
        return embed

    @app_commands.command(name="setup_leaderboard", description="สร้างกระดานสถิติ Live Leaderboard (อัปเดตอัตโนมัติ)")
    @app_commands.default_permissions(manage_roles=True)
    async def setup_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        if not self.db:
            await interaction.followup.send("❌ Database not initialized.", ephemeral=True)
            return
            
        embed = self.calculate_leaderboard_embed()
        message = await interaction.channel.send(embed=embed)
        
        # Save message ID to Firebase
        self.db.collection('settings').document('leaderboard').set({
            'channel_id': interaction.channel.id,
            'message_id': message.id
        })
        
        await interaction.followup.send("✅ สร้างกระดาน Live Leaderboard สำเร็จแล้วครับ!", ephemeral=True)

    @commands.Cog.listener('on_shift_update')
    async def update_live_leaderboard(self):
        """This listens to a custom event dispatched when someone checks out."""
        if not self.db:
            return
            
        doc_ref = self.db.collection('settings').document('leaderboard').get()
        if not doc_ref.exists:
            return
            
        data = doc_ref.to_dict()
        channel_id = data.get('channel_id')
        message_id = data.get('message_id')
        
        if not channel_id or not message_id:
            return
            
        channel = self.bot.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception:
                return
                
        try:
            message = await channel.fetch_message(message_id)
            embed = self.calculate_leaderboard_embed()
            await message.edit(embed=embed)
        except Exception as e:
            print(f"Error updating leaderboard: {e}")

async def setup(bot):
    await bot.add_cog(Stats(bot))
