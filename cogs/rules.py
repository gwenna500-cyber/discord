import discord
from discord import app_commands
from discord.ext import commands

class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rules", description="ดูระเบียบและข้อบังคับขององค์กร")
    async def rules(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📜 กฎระเบียบและข้อบังคับภายในองค์กร",
            description="ข้อพึงปฏิบัติสำหรับการใช้งานช่องทางนี้",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="1. นโยบายข้อมูลคนไข้ (HIPAA/PDPA)", 
            value="ห้ามส่ง แจ้ง หรือพิมพ์ข้อมูลส่วนบุคคลของคนไข้ เช่น ชื่อ-สกุล, รูปถ่าย, ประวัติการรักษา (PHI) ลงในช่องทางนี้โดยเด็ดขาด", 
            inline=False
        )
        embed.add_field(
            name="2. การเข้า-ออกเวร", 
            value="แพทย์และบุคลากรทุกท่านต้องใช้คำสั่ง `/checkin` เมื่อเริ่มงาน และ `/checkout` เมื่อออกเวรเสมอ", 
            inline=False
        )
        embed.add_field(
            name="3. การลา", 
            value="สามารถใช้คำสั่ง `/leave` ในการดูโควต้าและบันทึกวันลาได้", 
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Rules(bot))
