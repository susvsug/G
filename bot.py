import discord
from discord.ext import commands
import asyncio
import datetime
import os
from collections import defaultdict
from threading import Thread
from flask import Flask

# --- إعداد خادم ويب وهمي للاستضافة لمنع إغلاق البوت ---
app = Flask('')

@app.route('/')
def home():
    return "البوت يعمل بنجاح على استضافة Railway!"

def run_web():
    # Railway تلقائياً يوفر منفذ متغير اسمه PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# تشغيل خادم الويب في مسار جانبي (Thread)
Thread(target=run_web).start()

# --- إعدادات البوت الأساسية ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

TRUSTED_IDS = [1423421691773714482, 1422918463034228757]

removed_roles_backup = {}
action_cooldown = defaultdict(list)

# دالة إرسال الإمبيد للأونرات بالتنسيق الصحيح
async def send_owner_embed(title, description, target_info=None, extra_info=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    if target_info:
        embed.add_field(name="الهدف المستهدف", value=target_info, inline=False)
    if extra_info:
        embed.add_field(name="تفاصيل إضافية", value=extra_info, inline=False)
        
    for owner_id in TRUSTED_IDS:
        owner = bot.get_user(owner_id) or await bot.fetch_user(owner_id)
        if owner:
            try: await owner.send(embed=embed)
            except: pass

# دالة قشع الرتب
async def strip_roles(member: discord.Member, reason: str, target_info=None, extra_info=None):
    if member.id in TRUSTED_IDS or member.bot:
        return
    
    all_removable_roles = [role for role in member.roles if not role.is_default() and role.position < member.guild.me.top_role.position]
    
    if all_removable_roles:
        removed_roles_backup[member.id] = all_removable_roles
        
        try:
            await member.remove_roles(*all_removable_roles, reason=f"[Protection] - {reason}")
            
            try:
                user_embed = discord.Embed(
                    title="تنبيه أمني",
                    description=f"تم سحب رتبك وصلاحياتك من السيرفر بسبب: {reason}",
                    color=discord.Color.orange()
                )
                await member.send(embed=user_embed)
            except: pass
            
            title_msg = "رصد محاولة تخريب وقشع الرتب"
            desc_msg = f"العضو: {member.mention}\nالايدي: `{member.id}`\nالسبب: {reason}"
            await send_owner_embed(title_msg, desc_msg, target_info, extra_info)
            
        except discord.Forbidden:
            print(f"فشل قشع رتب {member.name}")

async def get_audit_executor(guild, action_type, check_time=5):
    await asyncio.sleep(0.6)
    async for entry in guild.audit_logs(limit=3, action=action_type):
        now = datetime.datetime.now(datetime.timezone.utc)
        if (now - entry.created_at).total_seconds() < check_time:
            return entry.user
    return None

def check_spam_action(user_id, action_name, max_count=3, seconds=5):
    now = datetime.datetime.utcnow()
    user_actions = action_cooldown[f"{user_id}_{action_name}"]
    user_actions = [t for t in user_actions if (now - t).total_seconds() < seconds]
    user_actions.append(now)
    action_cooldown[f"{user_id}_{action_name}"] = user_actions
    return len(user_actions) > max_count

# --- الأحداث والأنظمة ---

@bot.event
async def on_guild_channel_delete(channel):
    executor = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_delete)
    if executor and executor.id not in TRUSTED_IDS:
        member = channel.guild.get_member(executor.id)
        if member:
            await strip_roles(member, "محاولة حذف روم من السيرفر", f"الاسم: {channel.name} | الايدي: `{channel.id}`")
            try: await channel.clone(reason="إعادة الروم بواسطة الحماية")
            except: pass

@bot.event
async def on_guild_channel_update(before, after):
    executor = await get_audit_executor(after.guild, discord.AuditLogAction.channel_update)
    if executor and executor.id not in TRUSTED_IDS:
        member = after.guild.get_member(executor.id)
        if member:
            await strip_roles(member, "تعديل خصائص أو صلاحيات الروم بدون إذن", f"{after.mention} (`{after.id}`)")
            try: await after.edit(name=before.name, topic=before.topic, nsfw=before.nsfw)
            except: pass

@bot.event
async def on_guild_channel_create(channel):
    executor = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_create)
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "channel_create", max_count=3, seconds=10):
            member = channel.guild.get_member(executor.id)
            if member: await strip_roles(member, "إنشاء رومات بشكل مكثف وسريع")
            try: await channel.delete(reason="تصفية رومات التخريب")
            except: pass

@bot.event
async def on_guild_role_create(role):
    executor = await get_audit_executor(role.guild, discord.AuditLogAction.role_create)
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "role_create", max_count=3, seconds=10):
            member = role.guild.get_member(executor.id)
            if member: await strip_roles(member, "إنشاء رتب بشكل مكثف وسريع")
            try: await role.delete(reason="تصفية رتب التخريب")
            except: pass

@bot.event
async def on_guild_role_update(before, after):
    executor = await get_audit_executor(after.guild, discord.AuditLogAction.role_update)
    if executor and executor.id not in TRUSTED_IDS:
        member = after.guild.get_member(executor.id)
        if member:
            if not before.permissions.administrator and after.permissions.administrator:
                await strip_roles(member, "محاولة تفعيل صلاحية Administrator لرتبة", f"{after.name} (`{after.id}`)")
                try: await after.edit(permissions=before.permissions)
                except: pass
                return
            
            await strip_roles(member, "تعديل صلاحيات أو خصائص رتبة بشكل غير مصرح به", f"{after.name} (`{after.id}`)")
            try: await after.edit(permissions=before.permissions, color=before.color, hoist=before.hoist, mentionable=before.mentionable)
            except: pass

@bot.event
async def on_guild_emojis_update(guild, before, after):
    if len(before) > len(after):
        executor = await get_audit_executor(guild, discord.AuditLogAction.emoji_delete)
        if executor and executor.id not in TRUSTED_IDS:
            member = guild.get_member(executor.id)
            if member: await strip_roles(member, "حذف إيموجيات السيرفر")

@bot.event
async def on_guild_stickers_update(guild, before, after):
    if len(before) > len(after):
        executor = await get_audit_executor(guild, discord.AuditLogAction.sticker_delete)
        if executor and executor.id not in TRUSTED_IDS:
            member = guild.get_member(executor.id)
            if member: await strip_roles(member, "حذف ستيكرات السيرفر")

@bot.event
async def on_webhooks_update(channel):
    executor = await get_audit_executor(channel.guild, discord.AuditLogAction.webhook_delete)
    if executor and executor.id not in TRUSTED_IDS:
        member = channel.guild.get_member(executor.id)
        if member: await strip_roles(member, "تعديل أو حذف ويب هوك", f"الروم: {channel.mention}")

@bot.event
async def on_member_join(member):
    if member.bot:
        executor = await get_audit_executor(member.guild, discord.AuditLogAction.bot_add)
        if executor and executor.id not in TRUSTED_IDS:
            try:
                await member.ban(reason="دخول بوت غير مصرح به")
                inviter = member.guild.get_member(executor.id)
                if inviter: await strip_roles(inviter, "إدخال بوت غريب للسيرفر", f"البوت: {member.name} (`{member.id}`)")
            except: pass

@bot.event
async def on_message(message):
    if not message.guild or message.author.bot or message.author.id in TRUSTED_IDS:
        await bot.process_commands(message)
        return

    if message.mention_everyone:
        if check_spam_action(message.author.id, "mention_everyone", max_count=3, seconds=300):
            await strip_roles(message.author, "تكرار منشن ايفري/هير خلال 5 دقائق", extra_info=f"المحتوى: {message.content}")

    await bot.process_commands(message)

@bot.event
async def on_member_ban(guild, user):
    executor = await get_audit_executor(guild, discord.AuditLogAction.ban)
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "mass_ban", max_count=3, seconds=300):
            member = guild.get_member(executor.id)
            if member: await strip_roles(member, "تجاوز حد الباندات المسموح بها خلال 5 دقائق")

# --- الأوامر الحصرية ---

@bot.command(name="انطم")
async def mute_all(ctx):
    if ctx.author.id not in TRUSTED_IDS: return
    if ctx.author.voice and ctx.author.voice.channel:
        for member in ctx.author.voice.channel.members:
            if member.id not in TRUSTED_IDS and not member.bot:
                await member.edit(mute=True)
        await ctx.send("تم كتم جميع المتواجدين في الروم الصوتي")
    else: await ctx.send("يجب أن تكون داخل روم صوتي أولاً")

@bot.command(name="تكلم")
async def unmute_all(ctx):
    if ctx.author.id not in TRUSTED_IDS: return
    if ctx.author.voice and ctx.author.voice.channel:
        for member in ctx.author.voice.channel.members:
            await member.edit(mute=False)
        await ctx.send("تم فتح المايك عن الجميع")
    else: await ctx.send("يجب أن تكون داخل روم صوتي أولاً")

@bot.command(name="فك")
async def restore_roles(ctx, member: discord.Member):
    if ctx.author.id not in TRUSTED_IDS: return
    if member.id in removed_roles_backup:
        roles_to_add = [r for r in removed_roles_backup[member.id] if r in ctx.guild.roles and r.position < ctx.guild.me.top_role.position]
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason=f"إعادة الرتب بواسطة الأونر")
                del removed_roles_backup[member.id]
                await ctx.send(f"تم إعادة الرتب بنجاح للعضو: {member.mention}")
            except: await ctx.send("حدث خطأ، تأكد من صلاحيات البوت")
        else: await ctx.send("لم يتم العثور على رتب صالحة لإعادتها")
    else: await ctx.send("لا توجد رتب محفوظة لهذا الشخص في الرام")

# قراءة التوكن بأمان من متغيرات البيئة في الاستضافة
BOT_TOKEN = os.environ.get("DISCORD_TOKEN")
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("خطأ: لم يتم العثور على متغير البيئة DISCORD_TOKEN")
