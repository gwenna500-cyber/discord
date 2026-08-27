import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        
        # 1. ให้ยศ Unverified (ถ้ามี หรือจะสร้างใหม่ก็ได้)
        role_name = "Unverified"
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                role = await guild.create_role(name=role_name, color=discord.Color.light_grey())
            except Exception:
                pass
                
        if role:
            try:
                await member.add_roles(role)
            except Exception:
                pass

        # 2. ส่งข้อความต้อนรับ
        # หาห้องที่ชื่อ "ต้อนรับ" หรือ "welcome"
        welcome_channel = None
        for channel in guild.text_channels:
            if "ต้อนรับ" in channel.name or "welcome" in channel.name.lower():
                welcome_channel = channel
                break
                
        # ถ้าหาห้องต้อนรับไม่เจอ ให้ส่งข้อความไปหาแชทส่วนตัว (DM)
        if welcome_channel:
            embed = discord.Embed(
                title="🏥 ยินดีต้อนรับบุคลากรใหม่!",
                description=(
                    f"สวัสดีครับคุณ {member.mention} ยินดีต้อนรับสู่โรงพยาบาลของเราครับ!\n\n"
                    "👉 **เพื่อเริ่มต้นการทำงาน กรุณาไปที่ห้อง ยืนยันตัวตน เพื่อลงทะเบียนประวัติพนักงานครับ**\n"
                    "เมื่อยืนยันตัวตนสำเร็จแล้ว ระบบจะมอบยศ `Gen.` ให้โดยอัตโนมัติครับ"
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await welcome_channel.send(content=member.mention, embed=embed)
            except Exception:
                pass
        else:
            # Send DM if welcome channel doesn't exist
            embed = discord.Embed(
                title="🏥 ยินดีต้อนรับบุคลากรใหม่!",
                description=(
                    f"สวัสดีครับคุณ {member.name} ยินดีต้อนรับสู่โรงพยาบาลของเราครับ!\n\n"
                    "👉 **กรุณาไปที่ห้อง ยืนยันตัวตน ในเซิร์ฟเวอร์เพื่อลงทะเบียนประวัติพนักงานครับ**\n"
                    "เมื่อยืนยันตัวตนสำเร็จแล้ว ระบบจะมอบยศ `Gen.` ให้โดยอัตโนมัติครับ"
                ),
                color=discord.Color.green()
            )
            try:
                await member.send(embed=embed)
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(Welcome(bot))
