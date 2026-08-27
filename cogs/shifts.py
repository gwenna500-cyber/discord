import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import pytz
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firebase_config import get_db

class Shifts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = get_db()
        except Exception:
            self.db = None
            
        # Set timezone to Thailand
        self.tz = pytz.timezone('Asia/Bangkok')

    async def get_target_channel(self, guild: discord.Guild, keyword: str, exact_name: str):
        for channel in guild.text_channels:
            if keyword in channel.name:
                return channel
        return await guild.create_text_channel(exact_name)

    @app_commands.command(name="checkin", description="เข้าเวรทำงาน (ระบุชื่อตัวละคร)")
    @app_commands.describe(character_name="ชื่อตัวละครของคุณ")
    async def checkin(self, interaction: discord.Interaction, character_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        now = datetime.now(self.tz)
        
        # Log to Firebase
        if self.db:
            shifts_ref = self.db.collection('shifts')
            active_shift = shifts_ref.where('user_id', '==', user_id).where('status', '==', 'active').get()
            
            if active_shift:
                await interaction.followup.send("⚠️ คุณกำลังอยู่ในเวรอยู่แล้วครับ กรุณา /checkout ก่อนเข้าเวรใหม่", ephemeral=True)
                return
                
            shifts_ref.add({
                'user_id': user_id,
                'discord_name': interaction.user.name,
                'character_name': character_name,
                'check_in': now,
                'status': 'active'
            })
            
        # Send to specific channel
        log_channel = await self.get_target_channel(interaction.guild, "ลงชื่อเข้าเวร", "⊹˚꒰📝꒱︰ลงชื่อเข้าเวร")
        
        embed = discord.Embed(
            title="🟢 ลงชื่อเข้าเวร",
            color=discord.Color.green(),
            timestamp=now
        )
        embed.add_field(name="ชื่อตัวละคร", value=character_name, inline=True)
        embed.add_field(name="ผู้ใช้งาน Discord", value=interaction.user.mention, inline=True)
        embed.add_field(name="เวลาเข้าเวร", value=now.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await log_channel.send(embed=embed)
        await interaction.followup.send(f"✅ บันทึกเข้าเวรสำเร็จ ข้อมูลถูกส่งไปที่ {log_channel.mention} แล้วครับ", ephemeral=True)

    @app_commands.command(name="checkout", description="ออกเวรทำงาน (ระบุชื่อตัวละคร)")
    @app_commands.describe(character_name="ชื่อตัวละครของคุณ")
    async def checkout(self, interaction: discord.Interaction, character_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        now = datetime.now(self.tz)
        
        duration_str = "ไม่ทราบระยะเวลา (เนื่องจากไม่ได้บันทึกในระบบ)"
        
        # Update Firebase
        if self.db:
            shifts_ref = self.db.collection('shifts')
            active_shifts = shifts_ref.where('user_id', '==', user_id).where('status', '==', 'active').get()
            
            if not active_shifts:
                await interaction.followup.send("⚠️ ไม่พบข้อมูลการเข้าเวรของคุณครับ (คุณอาจจะยังไม่ได้ /checkin)", ephemeral=True)
                return
                
            shift_doc = active_shifts[0]
            check_in_time = shift_doc.to_dict().get('check_in')
            
            if check_in_time:
                # Calculate duration
                diff = now - check_in_time.astimezone(self.tz)
                hours, remainder = divmod(diff.total_seconds(), 3600)
                minutes, _ = divmod(remainder, 60)
                duration_str = f"{int(hours)} ชั่วโมง {int(minutes)} นาที"
            
            # Update document
            shift_doc.reference.update({
                'check_out': now,
                'status': 'completed',
                'duration_seconds': diff.total_seconds() if check_in_time else 0
            })
            
        # Send to specific channel
        log_channel = await self.get_target_channel(interaction.guild, "ลงชื่อออกเวร", "⊹˚꒰📝꒱︰ลงชื่อออกเวร")
        
        embed = discord.Embed(
            title="🔴 ลงชื่อออกเวร",
            color=discord.Color.red(),
            timestamp=now
        )
        embed.add_field(name="ชื่อตัวละคร", value=character_name, inline=True)
        embed.add_field(name="ผู้ใช้งาน Discord", value=interaction.user.mention, inline=True)
        embed.add_field(name="เวลาออกเวร", value=now.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
        embed.add_field(name="รวมระยะเวลาเข้าเวร", value=duration_str, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await log_channel.send(embed=embed)
        await interaction.followup.send(f"✅ บันทึกออกเวรสำเร็จ ข้อมูลถูกส่งไปที่ {log_channel.mention} แล้วครับ", ephemeral=True)

    @app_commands.command(name="oncall", description="ตรวจสอบว่าใครกำลังเข้าเวรอยู่บ้าง")
    async def oncall(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        if not self.db:
            await interaction.followup.send("❌ ระบบฐานข้อมูลขัดข้อง ไม่สามารถดึงข้อมูลได้ครับ")
            return
            
        shifts_ref = self.db.collection('shifts')
        active_shifts = shifts_ref.where('status', '==', 'active').get()
        
        if not active_shifts:
            await interaction.followup.send("ขณะนี้ไม่มีใครเข้าเวรอยู่เลยครับ 🏥")
            return
            
        embed = discord.Embed(title="🏥 รายชื่อแพทย์ที่กำลังเข้าเวร (On-Call)", color=discord.Color.blue())
        
        for shift in active_shifts:
            data = shift.to_dict()
            char_name = data.get('character_name', 'ไม่ระบุชื่อ')
            discord_name = data.get('discord_name', 'Unknown')
            check_in_time = data.get('check_in')
            
            if check_in_time:
                check_in_str = check_in_time.astimezone(self.tz).strftime("%H:%M")
            else:
                check_in_str = "Unknown"
                
            embed.add_field(
                name=f"🩺 {char_name}",
                value=f"Discord: {discord_name}\nเข้าเวรตั้งแต่: {check_in_str}",
                inline=False
            )
            
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Shifts(bot))
