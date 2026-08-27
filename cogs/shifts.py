import discord
from discord import app_commands
from discord.ext import commands
import sys
import os
from datetime import datetime
import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firebase_config import get_db

class ShiftCheckinModal(discord.ui.Modal):
    character_name = discord.ui.TextInput(
        label='ชื่อตัวละคร',
        placeholder='กรอกชื่อตัวละครของคุณ...',
        required=True,
        max_length=100
    )

    def __init__(self, location: str, db, tz):
        super().__init__(title='ลงชื่อเข้าเวร')
        self.location = location
        self.db = db
        self.tz = tz

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        char_name = self.character_name.value
        now = datetime.now(self.tz)
        
        if not self.db:
            await interaction.followup.send("❌ Database connection error.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        discord_name = str(interaction.user)
        shifts_ref = self.db.collection('shifts')
        
        active_shift = shifts_ref.where('user_id', '==', user_id).where('status', '==', 'active').get()
        if active_shift:
            await interaction.followup.send("⚠️ คุณกำลังเข้าเวรอยู่แล้วครับ ต้องออกเวรก่อนถึงจะเข้าใหม่ได้", ephemeral=True)
            return

        shifts_ref.add({
            'user_id': user_id,
            'discord_name': discord_name,
            'character_name': char_name,
            'location': self.location,
            'check_in': now,
            'status': 'active'
        })

        log_channel = await self.get_target_channel(interaction.guild, "ลงชื่อเข้าเวร", "⊹˚꒰📝꒱︰ลงชื่อเข้าเวร")
        
        embed = discord.Embed(
            title="🟢 ลงชื่อเข้าเวร",
            color=discord.Color.green(),
            timestamp=now
        )
        embed.add_field(name="ชื่อตัวละคร", value=char_name, inline=True)
        embed.add_field(name="ผู้ใช้งาน Discord", value=interaction.user.mention, inline=True)
        embed.add_field(name="จุดเข้าเวร", value=self.location, inline=False)
        embed.add_field(name="เวลาเข้าเวร", value=now.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        try:
            await log_channel.send(embed=embed)
        except Exception:
            pass
            
        await interaction.followup.send(f"✅ บันทึกเข้าเวรที่ {self.location} สำเร็จ ข้อมูลถูกส่งไปที่ {log_channel.mention} แล้วครับ", ephemeral=True)

    async def get_target_channel(self, guild, partial_name, fallback_name):
        for channel in guild.channels:
            if partial_name in channel.name:
                return channel
        return discord.utils.get(guild.channels, name=fallback_name) or guild.system_channel


class ShiftCheckoutModal(discord.ui.Modal):
    character_name = discord.ui.TextInput(
        label='ชื่อตัวละคร (เพื่อยืนยัน)',
        placeholder='กรอกชื่อตัวละครของคุณ...',
        required=True,
        max_length=100
    )

    def __init__(self, bot, db, tz):
        super().__init__(title='ลงชื่อออกเวร')
        self.bot = bot
        self.db = db
        self.tz = tz

    async def get_target_channel(self, guild, partial_name, fallback_name):
        for channel in guild.channels:
            if partial_name in channel.name:
                return channel
        return discord.utils.get(guild.channels, name=fallback_name) or guild.system_channel

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        char_name = self.character_name.value
        now = datetime.now(self.tz)
        user_id = str(interaction.user.id)
        
        if not self.db:
            await interaction.followup.send("❌ Database connection error.", ephemeral=True)
            return
            
        shifts_ref = self.db.collection('shifts')
        active_shifts = shifts_ref.where('user_id', '==', user_id).where('status', '==', 'active').get()
        
        if not active_shifts:
            await interaction.followup.send("⚠️ คุณยังไม่ได้เข้าเวร หรือบันทึกเวลาออกเวรไปแล้วครับ", ephemeral=True)
            return
            
        duration_str = "ไม่ทราบระยะเวลา"
        location = "ไม่ระบุ"
        
        for shift_doc in active_shifts:
            data = shift_doc.to_dict()
            check_in_time = data.get('check_in')
            location = data.get('location', 'ไม่ระบุ')
            
            if check_in_time:
                check_in_dt = check_in_time.astimezone(self.tz)
                diff = now - check_in_dt
                hours, remainder = divmod(diff.total_seconds(), 3600)
                minutes, _ = divmod(remainder, 60)
                duration_str = f"{int(hours)} ชั่วโมง {int(minutes)} นาที"
            
            shift_doc.reference.update({
                'check_out': now,
                'status': 'completed',
                'duration_seconds': diff.total_seconds() if check_in_time else 0
            })
            
        log_channel = await self.get_target_channel(interaction.guild, "ลงชื่อออกเวร", "⊹˚꒰📝꒱︰ลงชื่อออกเวร")
        
        embed = discord.Embed(
            title="🔴 ลงชื่อออกเวร",
            color=discord.Color.red(),
            timestamp=now
        )
        embed.add_field(name="ชื่อตัวละคร", value=char_name, inline=True)
        embed.add_field(name="ผู้ใช้งาน Discord", value=interaction.user.mention, inline=True)
        embed.add_field(name="จุดเข้าเวรล่าสุด", value=location, inline=False)
        embed.add_field(name="เวลาออกเวร", value=now.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
        embed.add_field(name="รวมระยะเวลาเข้าเวร", value=duration_str, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        try:
            await log_channel.send(embed=embed)
        except Exception:
            pass
            
        await interaction.followup.send(f"✅ บันทึกออกเวรสำเร็จ ข้อมูลถูกส่งไปที่ {log_channel.mention} แล้วครับ", ephemeral=True)
        self.bot.dispatch('shift_update')


class ShiftCheckinView(discord.ui.View):
    def __init__(self, db, tz):
        super().__init__(timeout=None)
        self.db = db
        self.tz = tz

    @discord.ui.button(label="เข้าเวร (โรงพยาบาล)", style=discord.ButtonStyle.success, emoji="🏥", custom_id="checkin_hospital")
    async def btn_hospital(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ShiftCheckinModal("โรงพยาบาล", self.db, self.tz))

    @discord.ui.button(label="เข้าเวร (ค่ายทหาร)", style=discord.ButtonStyle.success, emoji="🪖", custom_id="checkin_military")
    async def btn_military(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ShiftCheckinModal("ค่ายทหาร", self.db, self.tz))

    @discord.ui.button(label="เข้าเวร (สถานีตำรวจ)", style=discord.ButtonStyle.success, emoji="🚓", custom_id="checkin_police")
    async def btn_police(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ShiftCheckinModal("สถานีตำรวจ", self.db, self.tz))


class ShiftCheckoutView(discord.ui.View):
    def __init__(self, bot, db, tz):
        super().__init__(timeout=None)
        self.bot = bot
        self.db = db
        self.tz = tz

    @discord.ui.button(label="ออกเวร", style=discord.ButtonStyle.danger, emoji="🔴", custom_id="checkout_btn")
    async def btn_checkout(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ShiftCheckoutModal(self.bot, self.db, self.tz))


class Shifts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = get_db()
        except Exception:
            self.db = None
            
        self.tz = pytz.timezone('Asia/Bangkok')

    async def cog_load(self):
        self.bot.add_view(ShiftCheckinView(self.db, self.tz))
        self.bot.add_view(ShiftCheckoutView(self.bot, self.db, self.tz))

    @app_commands.command(name="setup_checkin", description="สร้างแผงปุ่มสำหรับกดเข้าเวร (ตั้งในห้อง ลงชื่อเข้าเวร)")
    @app_commands.default_permissions(manage_roles=True)
    async def setup_checkin(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="🏥 แผงควบคุมการเข้าเวร",
            description="กรุณากดปุ่มด้านล่างตามสถานที่ที่คุณต้องการเข้าเวร เพื่อบันทึกเวลาทำงานครับ",
            color=discord.Color.green()
        )
        await interaction.channel.send(embed=embed, view=ShiftCheckinView(self.db, self.tz))
        await interaction.followup.send("✅ สร้างแผงปุ่มเข้าเวรเรียบร้อยแล้ว", ephemeral=True)

    @app_commands.command(name="setup_checkout", description="สร้างแผงปุ่มสำหรับกดออกเวร (ตั้งในห้อง ลงชื่อออกเวร)")
    @app_commands.default_permissions(manage_roles=True)
    async def setup_checkout(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="🔴 แผงควบคุมการออกเวร",
            description="กรุณากดปุ่มด้านล่างเพื่อออกเวรและสรุปเวลาการทำงานครับ",
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed, view=ShiftCheckoutView(self.bot, self.db, self.tz))
        await interaction.followup.send("✅ สร้างแผงปุ่มออกเวรเรียบร้อยแล้ว", ephemeral=True)

    @app_commands.command(name="oncall", description="ตรวจสอบว่าใครกำลังเข้าเวรอยู่บ้าง (คำนวณเวลาแบบเรียลไทม์)")
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
        now = datetime.now(self.tz)
        
        for shift in active_shifts:
            data = shift.to_dict()
            char_name = data.get('character_name', 'ไม่ระบุชื่อ')
            discord_name = data.get('discord_name', 'Unknown')
            location = data.get('location', 'โรงพยาบาล')
            check_in_time = data.get('check_in')
            
            duration_str = "ไม่ทราบ"
            if check_in_time:
                check_in_dt = check_in_time.astimezone(self.tz)
                check_in_str = check_in_dt.strftime("%H:%M")
                
                diff = now - check_in_dt
                hours, remainder = divmod(diff.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{int(hours)} ชม. {int(minutes)} น. {int(seconds)} วิ."
            else:
                check_in_str = "Unknown"
                
            embed.add_field(
                name=f"🩺 {char_name}",
                value=f"👤 Discord: {discord_name}\n📍 จุดเข้าเวร: {location}\n🕒 เข้าเวรตั้งแต่: {check_in_str}\n⏱️ ผ่านไปแล้ว: {duration_str}",
                inline=False
            )
            
        await interaction.followup.send(embed=embed)

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
        
        self.db.collection('settings').document('leaderboard').set({
            'channel_id': interaction.channel.id,
            'message_id': message.id
        })
        
        await interaction.followup.send("✅ สร้างกระดาน Live Leaderboard สำเร็จแล้วครับ!", ephemeral=True)

    @commands.Cog.listener('on_shift_update')
    async def update_live_leaderboard(self):
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
            pass

async def setup(bot):
    await bot.add_cog(Shifts(bot))
