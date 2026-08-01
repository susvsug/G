import discord
from discord.ext import commands

# إعداد الصلاحيات اللازمة
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# معرفات (IDs) الرتبة والحساب التي زودتني بها
TARGET_MEMBER_ID = 1422918463034228757
TARGET_ROLE_ID = 1527939953881911468

@bot.event
async def on_ready():
    print(f"البوت جاهز ويعمل كـ: {bot.user}")

@bot.command()
async def assign(ctx):
    # جلب العضو المستهدف من السيرفر باستخدام الـ ID
    member = ctx.guild.get_member(TARGET_MEMBER_ID)
    # جلب الرتبة المستهدفة من السيرفر باستخدام الـ ID
    role = ctx.guild.get_role(TARGET_ROLE_ID)

    # التحقق من وجود العضو في السيرفر
    if not member:
        await ctx.send("❌ لم يتم العثور على الحساب المستهدف في هذا السيرفر.")
        return

    # التحقق من وجود الرتبة في السيرفر
    if not role:
        await ctx.send("❌ لم يتم العثور على الرتبة المستهدفة في هذا السيرفر.")
        return

    try:
        # إعطاء الرتبة للعضو
        await member.add_roles(role)
        await ctx.send(f"✅ تم إعطاء رتبة <@&{TARGET_ROLE_ID}> للحساب <@{TARGET_MEMBER_ID}> بنجاح!")
    except discord.Forbidden:
        await ctx.send("❌ لا أملك الصلاحيات الكافية. تأكد من رفع رتبة البوت فوق الرتبة المراد إعطاؤها في إعدادات السيرفر.")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ غير متوقع: {e}")

# ضع توكن البوت الخاص بك هنا
bot.run("YOUR_BOT_TOKEN")
