import os
import discord

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# الأرقام الخاصة بك التي حددتها
TARGET_ROLE_ID = 1527939953881911468
TARGET_MEMBER_ID = 1422918463034228757

@client.event
async def on_ready():
    print(f"Logged in as {client.user} and ready for Railway!")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # إذا تحتوي الرسالة على المعرفين معاً
    if str(TARGET_ROLE_ID) in message.content and str(TARGET_MEMBER_ID) in message.content:
        guild = message.guild
        if not guild:
            return

        member = guild.get_member(TARGET_MEMBER_ID)
        role = guild.get_role(TARGET_ROLE_ID)

        if member and role:
            try:
                await member.add_roles(role)
                await message.channel.send("✅ تم إعطاؤك الرتبة بنجاح!")
            except discord.Forbidden:
                await message.channel.send("❌ ارفع رتبة البوت فوق الرتبة المطلوبة في إعدادات السيرفر.")
            except Exception as e:
                await message.channel.send(f"❌ خطأ: {e}")

# جلب التوكن من متغيرات البيئة الخاصة بـ Railway لحماية بوتك
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    client.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN variable is not set!")
