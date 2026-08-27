import discord
from discord import app_commands
from discord.ext import commands
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firebase_config import get_db

class TicketUserView(discord.ui.View):
    def __init__(self, user_to_verify: discord.Member, db):
        super().__init__(timeout=None)
        self.user_to_verify = user_to_verify
        self.db = db

    async def get_or_create_intro_channel(self, guild: discord.Guild):
        channel_name = "⊹˚꒰🧑🏻⚕️꒱แนะนำตัวหมอ"
        # Since the user's screenshot has spaces, we can search by contains or create without spaces if not found
        for channel in guild.text_channels:
            if "แนะนำตัวหมอ" in channel.name:
                return channel
        
        # If absolutely not found, create a new one
        return await guild.create_text_channel(channel_name)

    @discord.ui.button(label="ยืนยันการส่งข้อมูล", style=discord.ButtonStyle.success, custom_id="verify_submit")
    async def submit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user_to_verify:
            await interaction.response.send_message("❌ ปุ่มนี้สำหรับผู้ลงทะเบียนเท่านั้นครับ", ephemeral=True)
            return

        await interaction.response.defer()

        messages = [msg async for msg in interaction.channel.history(limit=50, oldest_first=True)]
        user_messages = []
        attachments = []
        for msg in messages:
            if msg.author == self.user_to_verify:
                if msg.content:
                    user_messages.append(msg.content)
                for att in msg.attachments:
                    try:
                        file = await att.to_file()
                        attachments.append(file)
                    except Exception:
                        pass
                    
        if not user_messages and not attachments:
            await interaction.followup.send("❌ คุณยังไม่ได้พิมพ์ข้อความหรือแนบรูปเลยครับ กรุณาส่งข้อมูลก่อนกดยืนยัน", ephemeral=True)
            return

        guild = interaction.guild
        
        role = discord.utils.get(guild.roles, name="Verified Staff")
        if not role:
            try:
                role = await guild.create_role(name="Verified Staff", color=discord.Color.blue())
            except Exception:
                pass

        if role:
            try:
                await self.user_to_verify.add_roles(role)
            except Exception:
                pass

        intro_channel = await self.get_or_create_intro_channel(guild)
        embed = discord.Embed(
            title="🎉 ต้อนรับบุคลากรใหม่!",
            description=f"ขอต้อนรับ {self.user_to_verify.mention} เข้าสู่ระบบอย่างเป็นทางการครับ",
            color=discord.Color.teal()
        )
        
        if user_messages:
            intro_text = "\n".join(user_messages)
            if len(intro_text) > 1000:
                intro_text = intro_text[:1000] + "..."
            embed.add_field(name="ข้อมูลแนะนำตัว", value=intro_text, inline=False)
            
        try:
            await intro_channel.send(embed=embed, files=attachments)
        except Exception:
            pass

        if self.db:
            self.db.collection('verified_staff').document(str(self.user_to_verify.id)).set({
                'user_id': str(self.user_to_verify.id),
                'verified_by': 'self_submitted',
                'timestamp': discord.utils.utcnow()
            })

        try:
            await self.user_to_verify.send("✅ **การยืนยันตัวตนของคุณสำเร็จแล้ว!** ข้อมูลและรูปของคุณถูกส่งไปยังห้องแนะนำตัวหมอเรียบร้อยแล้วครับ")
        except:
            pass

        try:
            await interaction.channel.delete(reason="User Submitted Verification")
        except Exception:
            pass


class VerifyStartView(discord.ui.View):
    def __init__(self, bot, db):
        super().__init__(timeout=None)
        self.bot = bot
        self.db = db

    @discord.ui.button(label="คลิกเพื่อยืนยันตัวตน", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="start_verify_ticket")
    async def start_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        await interaction.response.defer(ephemeral=True)
        
        role = discord.utils.get(guild.roles, name="Verified Staff")
        if role and role in user.roles:
            await interaction.followup.send("✅ คุณยืนยันตัวตนเรียบร้อยแล้วครับ ไม่ต้องทำซ้ำ", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name="Verification Tickets")
        if not category:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            category = await guild.create_category("Verification Tickets", overwrites=overwrites)

        existing_channel = discord.utils.get(category.text_channels, name=f"verify-{user.name.lower()}")
        if existing_channel:
            await interaction.followup.send(f"⚠️ คุณมีห้องยืนยันตัวตนอยู่แล้วครับ ไปที่ {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"verify-{user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🔐 การยืนยันตัวตน",
            description=(
                f"สวัสดีครับคุณ {user.mention}\n\n"
                "กรุณา **พิมพ์ชื่อตัวละคร**, **อายุ**, และ **แนบรูปถ่าย** ส่งเข้ามาในห้องนี้ได้เลยครับ\n\n"
                "เมื่อพิมพ์และแนบรูปเสร็จเรียบร้อยแล้ว **ให้กดปุ่ม ยืนยันการส่งข้อมูล ด้านล่าง** ข้อมูลทั้งหมดของคุณจะเด้งไปที่ห้องแนะนำตัวหมอ อัตโนมัติครับ"
            ),
            color=discord.Color.yellow()
        )
        
        user_view = TicketUserView(user_to_verify=user, db=self.db)
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=user_view)
        
        await interaction.followup.send(f"✅ เปิดห้องยืนยันตัวตนให้แล้วครับ ไปที่ {ticket_channel.mention}", ephemeral=True)


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = get_db()
        except Exception:
            self.db = None

    async def cog_load(self):
        self.bot.add_view(VerifyStartView(self.bot, self.db))

    @app_commands.command(name="setup_verify", description="สร้างปุ่มให้พนักงานกดยืนยันตัวตน")
    @app_commands.default_permissions(manage_roles=True)
    async def setup_verify(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔐 ยืนยันตัวตนพนักงาน (Verification)",
            description=(
                "พนักงานใหม่ทุกท่านจำเป็นต้องยืนยันตัวตนก่อนเข้าใช้งาน\n\n"
                "👇 **กรุณากดปุ่มด้านล่างเพื่อพิมพ์ชื่อตัวละคร, อายุ และแนบรูปภาพครับ**"
            ),
            color=discord.Color.blue()
        )
        
        view = VerifyStartView(self.bot, self.db)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ สร้างปุ่มยืนยันตัวตนเรียบร้อยแล้ว", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Verification(bot))
