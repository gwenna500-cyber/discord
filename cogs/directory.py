import discord
from discord import app_commands
from discord.ext import commands
import sys
import os

# Add parent directory to path so we can import firebase_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firebase_config import get_db

class Directory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = get_db()
        except Exception as e:
            print(f"Error initializing Firebase in Directory: {e}")
            self.db = None

    @app_commands.command(name="add_doctor", description="เพิ่มรายชื่อแพทย์ลงในระบบ (Admin Only)")
    @app_commands.describe(name="ชื่อ-นามสกุล", department="แผนก", contact="ข้อมูลติดต่อ (เช่น เบอร์ภายใน)", user="Discord User (ถ้ามี)")
    @app_commands.default_permissions(manage_roles=True)
    async def add_doctor(self, interaction: discord.Interaction, name: str, department: str, contact: str, user: discord.Member = None):
        if not self.db:
            await interaction.response.send_message("Database not initialized.", ephemeral=True)
            return

        user_id = str(user.id) if user else None
        
        self.db.collection('directory').add({
            'name': name,
            'department': department,
            'contact_info': contact,
            'user_id': user_id
        })
            
        await interaction.response.send_message(f"✅ เพิ่มรายชื่อ นพ./พญ. **{name}** (แผนก {department}) ลงในระบบเรียบร้อยแล้ว")

    @app_commands.command(name="directory", description="ดูรายชื่อแพทย์และข้อมูลติดต่อ")
    @app_commands.describe(department="ค้นหาตามแผนก (เว้นว่างเพื่อดูทั้งหมด)")
    async def view_directory(self, interaction: discord.Interaction, department: str = None):
        if not self.db:
            await interaction.response.send_message("Database not initialized.", ephemeral=True)
            return

        dir_ref = self.db.collection('directory')
        if department:
            # Firestore doesn't support 'LIKE', so we do exact match or we'd have to filter locally.
            # We'll filter locally for a 'LIKE' effect.
            docs = dir_ref.stream()
            results = [doc.to_dict() for doc in docs if department.lower() in doc.to_dict().get('department', '').lower()]
        else:
            docs = dir_ref.order_by('department').stream()
            results = [doc.to_dict() for doc in docs]

        if not results:
            await interaction.response.send_message("ไม่พบรายชื่อในระบบครับ")
            return
            
        embed = discord.Embed(title="🏥 ทำเนียบรายชื่อแพทย์", color=discord.Color.purple())
        for data in results:
            name = data.get('name')
            dept = data.get('department')
            contact = data.get('contact_info')
            uid = data.get('user_id')
            
            mention = f" (<@{uid}>)" if uid else ""
            embed.add_field(
                name=f"นพ./พญ. {name} {mention}", 
                value=f"**แผนก:** {dept}\n**ติดต่อ:** {contact}", 
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Directory(bot))
