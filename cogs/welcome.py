import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Create a welcome embed
        embed = discord.Embed(
            title="👋 ยินดีต้อนรับสู่เซิร์ฟเวอร์!",
            description=f"สวัสดีคุณ {member.mention} ยินดีต้อนรับเข้าสู่ระบบสื่อสารภายในองค์กรครับ",
            color=discord.Color.teal()
        )
        
        embed.add_field(
            name="📜 สิ่งที่ต้องทำเป็นอันดับแรก", 
            value="กรุณาใช้คำสั่ง `/rules` ในช่องแชทเพื่ออ่านกฎระเบียบและข้อบังคับขององค์กร (โดยเฉพาะเรื่องนโยบายความลับของคนไข้)", 
            inline=False
        )
        
        embed.add_field(
            name="🔐 การยืนยันตัวตน", 
            value="หากคุณเป็นพนักงาน กรุณาใช้คำสั่ง `/verify` ตามด้วยรหัสพนักงานของคุณ เพื่อรับสิทธิ์การเข้าถึงห้องแชทต่างๆ", 
            inline=False
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="หากมีข้อสงสัย กรุณาติดต่อผู้ดูแลระบบ (Admin)")

        # Try to send to the server's system channel (if set)
        if member.guild.system_channel:
            await member.guild.system_channel.send(embed=embed)
        else:
            # If no system channel is set, try to find a general channel
            channel = discord.utils.get(member.guild.text_channels, name='general') or \
                      discord.utils.get(member.guild.text_channels, name='ทั่วไป')
            if channel:
                await channel.send(embed=embed)
            else:
                # Fallback: Send a Direct Message
                try:
                    await member.send(embed=embed)
                except discord.Forbidden:
                    pass

async def setup(bot):
    await bot.add_cog(Welcome(bot))
