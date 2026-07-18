import discord
import os

intents = discord.Intents.all()
client = discord.Client(intents=intents)

# البيانات الخاصة بك
TARGET_USER_ID = 1422918463034228757
TARGET_ROLE_ID = 1497438121934061568

@client.event
async def on_ready():
    print(f"🤖 البوت {client.user.name} متصل... جاري البحث عن الشخص وإعطائه الرتبة.")
    
    # البحث عن السيرفر الذي تتواجد فيه الرتبة والشخص
    for guild in client.guilds:
        role = guild.get_role(TARGET_ROLE_ID)
        if role:
            try:
                # جلب العضو مباشرة من السيرفر
                member = await guild.fetch_member(TARGET_USER_ID)
                if member:
                    await member.add_roles(role, reason="تفعيل الرتبة التلقائي للشخص المحدد")
                    print(f"✅ تم بنجاح إعطاء الرتبة للشخص المحدد في سيرفر: {guild.name}")
                    await client.close() # إغلاق السكربت بعد النجاح
                    return
            except discord.NotFound:
                continue # الشخص ليس في هذا السيرفر، يبحث في السيرفر التالي
            except discord.Forbidden:
                print(f"❌ خطأ: رتبة البوت أدنى من الرتبة المراد إعطاؤها في سيرفر {guild.name}!")
                await client.close()
                return
            except Exception as e:
                print(f"❌ حدث خطأ: {e}")
                await client.close()
                return

    print("❌ لم يتم العثور على الشخص أو الرتبة في السيرفرات المشتركة مع البوت.")
    await client.close()

# تشغيل
BOT_TOKEN = os.environ.get("DISCORD_TOKEN")
if BOT_TOKEN:
    client.run(BOT_TOKEN)
else:
    print("خطأ: لم يتم العثور على متغير البيئة DISCORD_TOKEN")
