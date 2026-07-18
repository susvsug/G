import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# البيانات الثابتة الخاصة بك
TARGET_USER_ID = 1422918463034228757
TARGET_ROLE_ID = 1497438121934061568

@bot.event
async def on_ready():
    print(f"🛡️ نظام التثبيت التلقائي يعمل الآن بواسطة {bot.user.name}")
    print(f"👀 جاري مراقبة الشخص ({TARGET_USER_ID}) لتثبيت الرتبة ({TARGET_ROLE_ID}) عليه دائماً...")
    
    # فحص أولى عند تشغيل البوت للتأكد إن الرتبة معاه حالياً
    for guild in bot.guilds:
        role = guild.get_role(TARGET_ROLE_ID)
        if role:
            member = guild.get_member(TARGET_USER_ID) or await guild.fetch_member(TARGET_USER_ID).catch(None)
            if member and role not in member.roles:
                try:
                    await member.add_roles(role, reason="تثبيت الرتبة التلقائي عند تشغيل البوت")
                    print(f"⚙️ فحص أولي: تم إرجاع الرتبة للشخص في سيرفر {guild.name}")
                except:
                    pass

@bot.event
async def on_member_update(before, after):
    # التحقق من أن التحديث يخص الشخص المطلوب فقط
    if after.id != TARGET_USER_ID:
        return
        
    # إذا تغيرت الرتب (تم حذف رتبة)
    if len(before.roles) > len(after.roles):
        # التأكد من أن الرتبة المحذوفة هي الرتبة المستهدفة
        target_role = after.guild.get_role(TARGET_ROLE_ID)
        
        if target_role and (target_role in before.roles) and (target_role not in after.roles):
            print(f"⚠️ رصد محاولة نزع الرتبة عن الشخص المستهدف في سيرفر {after.guild.name}!")
            
            # محاولة إعادتها فوراً
            try:
                await after.add_roles(target_role, reason="نظام الحماية: ممنوع سحب هذه الرتبة عن هذا الشخص")
                print(f"⚡ تم إرجاع الرتبة للشخص بنجاح رغماً عن المحاولة!")
            except discord.Forbidden:
                print(f"❌ فشل إرجاع الرتبة! تأكد أن رتبة البوت أعلى من الرتبة المستهدفة ولدى البوت صلاحية Manage Roles.")
            except Exception as e:
                print(f"❌ حدث خطأ أثناء محاولة إرجاع الرتبة: {e}")

# تشغيل البوت بمتغير البيئة الخاص بك
BOT_TOKEN = os.environ.get("DISCORD_TOKEN")
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("خطأ: لم يتم العثور على متغير البيئة DISCORD_TOKEN")
