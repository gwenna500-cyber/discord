import discord
from discord import app_commands
from discord.ext import commands
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firebase_config import get_db

class PromotionUserView(discord.ui.View):
    def __init__(self, user: discord.Member, db):
        super().__init__(timeout=None)
        self.user = user
        self.db = db

    async def get_or_create_promo_log_channel(self, guild: discord.Guild):
        channel_name = "การเลื่อนตำแหน่ง"
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            channel = await guild.create_text_channel(channel_name)
        return channel

    @discord.ui.button(label="ยืนยันการส่งข้อมูล", style=discord.ButtonStyle.success, custom_id="promo_submit")
    async def submit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ ปุ่มนี้สำหรับผู้ลงทะเบียนเท่านั้นครับ", ephemeral=True)
            return

        await interaction.response.defer()

        guild = interaction.guild
        
        messages = [msg async for msg in interaction.channel.history(limit=50, oldest_first=True)]
        user_messages = []
        attachments = []
        
        for msg in messages:
            if msg.author == self.user:
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

        announce_channel = await self.get_or_create_promo_log_channel(guild)
        
        embed = discord.Embed(
            title="📋 ขอแจ้งเลื่อนขั้น",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="ผู้ลงทะเบียน", value=self.user.mention, inline=False)
        
        char_name = "ไม่ได้ระบุชื่อ"
        if user_messages:
            char_name = "\n".join(user_messages)[:1000]
            embed.add_field(name="รายละเอียด", value=char_name, inline=False)
            
        try:
            await announce_channel.send(embed=embed, files=attachments)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการส่งข้อมูลไปที่ห้อง การเลื่อนตำแหน่ง: {e}", ephemeral=True)
            return

        # บันทึกลงฐานข้อมูล Firebase
        if self.db:
            self.db.collection('promotions').document(str(self.user.id)).set({
                'user_id': str(self.user.id),
                'discord_name': self.user.name,
                'character_name': char_name,
                'timestamp': discord.utils.utcnow(),
                'status': 'Pending'
            })

        try:
            await self.user.send("✅ **ข้อมูลขอเลื่อนขั้นถูกส่งไปยังห้องการเลื่อนตำแหน่งเรียบร้อยแล้วครับ!**")
        except:
            pass

        try:
            await interaction.channel.delete(reason="User Submitted Promotion")
        except Exception:
            pass


class PromotionStartView(discord.ui.View):
    def __init__(self, bot, db):
        super().__init__(timeout=None)
        self.bot = bot
        self.db = db

    @discord.ui.button(label="ลงทะเบียนขอเลื่อนขั้น", style=discord.ButtonStyle.success, emoji="⭐", custom_id="start_promo_ticket")
    async def start_promo(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(guild.categories, name="Promotion Tickets")
        if not category:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            category = await guild.create_category("Promotion Tickets", overwrites=overwrites)

        existing_channel = discord.utils.get(category.text_channels, name=f"promo-{user.name.lower()}")
        if existing_channel:
            await interaction.followup.send(f"⚠️ คุณมีห้องขอเลื่อนขั้นอยู่แล้วครับ ไปที่ {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"promo-{user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="⭐ ลงทะเบียนขอเลื่อนขั้น",
            description=(
                f"สวัสดีครับ {user.mention}\n\n"
                "📌 **เงื่อนไขสำหรับการเลื่อนขั้นเป็น หมอชุดขาว (Rank 1):**\n"
                "• ต้องมีเหรียญตราสะสม **60,000 เหรียญ**\n"
                "• ต้องมีค่าประสบการณ์ (XP) **50,000 XP**\n\n"
                "หากคุณมีคะแนนครบตามเงื่อนไขแล้ว กรุณาทำตามนี้:\n"
                "1. **พิมพ์ชื่อตัวละครของคุณ** ลงในแชทนี้\n"
                "2. **ส่งภาพถ่ายหน้าจอ (Screenshot)** ที่เห็นคะแนนอย่างชัดเจน\n\n"
                "เมื่อเสร็จแล้ว **ให้กดปุ่ม ยืนยันการส่งข้อมูล ด้านล่าง** ข้อมูลจะถูกส่งไปที่ห้อง การเลื่อนตำแหน่ง ทันทีครับ"
            ),
            color=discord.Color.green()
        )
        
        user_view = PromotionUserView(user=user, db=self.db)
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=user_view)
        
        await interaction.followup.send(f"✅ สร้างห้องขอเลื่อนขั้นให้แล้วครับ ไปที่ {ticket_channel.mention} เพื่อส่งข้อมูลได้เลยครับ", ephemeral=True)


class Promotion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = get_db()
        except Exception:
            self.db = None

    async def cog_load(self):
        self.bot.add_view(PromotionStartView(self.bot, self.db))

    @app_commands.command(name="setup_promotion", description="สร้างปุ่มลงทะเบียนเลื่อนขั้น (เฉพาะแอดมิน)")
    @app_commands.default_permissions(manage_roles=True)
    async def setup_promotion(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⭐ ลงทะเบียนขอเลื่อนขั้น (Promotion)",
            description=(
                "เปิดรับลงทะเบียนผู้มีสิทธิ์เลื่อนขั้นเป็น **หมอชุดขาว (Rank 1)**\n\n"
                "เงื่อนไข: เหรียญตรา 60,000 / 50,000 XP\n"
                "หากคุณมีคะแนนครบแล้ว กรุณากดปุ่มด้านล่างเพื่อพิมพ์ชื่อตัวละครและแนบหลักฐานครับ"
            ),
            color=discord.Color.gold()
        )
        
        view = PromotionStartView(self.bot, self.db)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ สร้างระบบลงทะเบียนขอเลื่อนขั้นเรียบร้อยแล้ว", ephemeral=True)

    @app_commands.command(name="promo_list", description="ดูรายชื่อคนที่ลงทะเบียนขอเลื่อนขั้น (เฉพาะแอดมิน)")
    @app_commands.default_permissions(manage_roles=True)
    async def promo_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.db:
            await interaction.followup.send("❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้", ephemeral=True)
            return

        docs = self.db.collection('promotions').stream()
        promo_list = list(docs)

        if not promo_list:
            await interaction.followup.send("📋 ยังไม่มีใครลงทะเบียนขอเลื่อนขั้นครับ", ephemeral=True)
            return

        embed = discord.Embed(title="📋 รายชื่อผู้ลงทะเบียนขอเลื่อนขั้น", color=discord.Color.gold())
        
        for doc in promo_list:
            data = doc.to_dict()
            discord_name = data.get('discord_name', 'Unknown')
            char_name = data.get('character_name', 'ไม่ระบุ')
            
            # Remove linebreaks from char_name for cleaner display
            char_name = char_name.replace('\n', ' ')
            if len(char_name) > 50:
                char_name = char_name[:50] + "..."
                
            embed.add_field(name=f"👤 {discord_name}", value=f"ชื่อตัวละคร: {char_name}", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Promotion(bot))
