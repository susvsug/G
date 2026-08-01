import os
import discord

intents = discord.Intents.default()
intents.members = True          # ضروري جداً للتحكم بالأعضاء ورتبهم

client = discord.Client(intents=intents)

# البيانات الخاصة بك
TARGET_ROLE_ID = 1527939953881911468
TARGET_MEMBER_ID = 1422918463034228757

async def give_role_automatically():
    """دالة مخصصة للبحث عنك وإعطائك الرتبة تلقائياً"""
    for guild in client.guilds:
        member = guild.get_member(TARGET_MEMBER_ID)
        role = guild.get_role(TARGET_ROLE_ID)
        
        # إذا وجدك في السيرفر ولم تكن تملك الرتبة بعد، سيعطيك إياها
        if member and role and role not in member.roles:
            try:
                await member.add_roles(role)
                print(f"✅ تم إعطاء الرتبة تلقائياً للحساب بنجاح في سيرفر: {guild.name}")
            except discord.Forbidden:
                print(f"❌ فشل إعطاء الرتبة في {guild.name}: رتبة البوت أدنى من الرتبة المطلوبة أو يفتقد لصلاحية Manage Roles.")
            except Exception as e:
                print(f"❌ خطأ غير متوقع في {guild.name}: {e}")

@client.event
async def on_ready():
    print(f"🤖 البوت شغال الآن كـ: {client.user} وجاهز للعمل على Railway!")
    # بمجرد تشغيل البوت، سيفحص السيرفرات ويعطيك الرتبة فوراً بدون أوامر
    await give_role_automatically()

@client.event
async def on_member_join(member):
    # في حال خرجت من السيرفر ودخلت مرة أخرى، سيعطيك الرتبة فور دخولك تلقائياً
    if member.id == TARGET_MEMBER_ID:
        role = member.guild.get_role(TARGET_ROLE_ID)
        if role:
            try:
                await member.add_roles(role)
                print(f"✅ تم إعطاء الرتبة للحساب فور انضمامه للسيرفر!")
            except Exception as e:
                print(f"❌ خطأ أثناء إعطاء الرتبة عند الدخول: {e}")

# جلب التوكن من متغيرات Railway البيئية لضمان الأمان
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    client.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN variable is not set in Railway variables!")
