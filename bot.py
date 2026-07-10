import discord
from discord.ext import commands
import asyncio
import datetime
import os
from collections import defaultdict
from threading import Thread
from flask import Flask

# --- خادم ويب وهمي للاستضافة على Railway ---
app = Flask('')

@app.route('/')
def home():
    return "نظام الحماية القصوى يعمل بنجاح 24/7"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web).start()

# --- إعدادات البوت ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# الحسابين الموثوقة (الأونرات) بناءً على طلبك
TRUSTED_IDS = [1422918463034228757, 1423421691773714482]

# الذاكرة المؤقتة للرتب والسبام
removed_roles_backup = {}
action_cooldown = defaultdict(list)

# الصلاحيات الخطيرة المراقبة
DANGEROUS_PERMS = ['administrator', 'manage_guild', 'ban_members', 'kick_members', 'manage_roles', 'manage_channels', 'manage_webhooks']

# --- دالة إرسال الإمبيد التفصيلي للأونرات فقط ---
async def send_owner_embed(title, description, target_info=None, extra_info=None):
    embed = discord.Embed(
        title=f"🛡️ تقرير أمني | {title}",
        description=description,
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    if target_info:
        embed.add_field(name="🔹 الهدف المتأثر (الأساسي):", value=target_info, inline=False)
    if extra_info:
        embed.add_field(name="🔹 تفاصيل إضافية:", value=extra_info, inline=False)
    
    embed.set_footer(text="نظام الحماية التلقائي")
        
    for owner_id in TRUSTED_IDS:
        owner = bot.get_user(owner_id) or await bot.fetch_user(owner_id)
        if owner:
            try: await owner.send(embed=embed)
            except: pass

# --- دالة قشع الرتب (بدون إرسال خاص للمخالف) ---
async def strip_roles(member: discord.Member, reason: str, target_info=None, extra_info=None):
    if member.id in TRUSTED_IDS or member.bot:
        return
    
    all_removable_roles = [role for role in member.roles if not role.is_default() and role.position < member.guild.me.top_role.position]
    
    if all_removable_roles:
        removed_roles_backup[member.id] = all_removable_roles
        try:
            # قشع صامت بدون أي رسالة للمخالف
            await member.remove_roles(*all_removable_roles, reason=f"[الحماية] - {reason}")
            
            # إرسال التفاصيل كاملة للأونرات
            title_msg = "رصد محاولة تخريب وقشع الرتب"
            desc_msg = f"👤 **المسؤول الفاعل:** {member.mention}\n🆔 **ايدي الفاعل:** `{member.id}`\n❓ **السبب:** {reason}"
            await send_owner_embed(title_msg, desc_msg, target_info, extra_info)
        except discord.Forbidden:
            print(f"فشل قشع رتب {member.name}")

# --- دالة فحص السجلات ---
async def get_audit_executor(guild, action_type, check_time=5):
    await asyncio.sleep(0.6)
    async for entry in guild.audit_logs(limit=3, action=action_type):
        now = datetime.datetime.now(datetime.timezone.utc)
        if (now - entry.created_at).total_seconds() < check_time:
            return entry
    return None

# --- دالة مراقبة السبام ---
def check_spam_action(user_id, action_name, max_count=3, seconds=5):
    now = datetime.datetime.utcnow()
    user_actions = action_cooldown[f"{user_id}_{action_name}"]
    user_actions = [t for t in user_actions if (now - t).total_seconds() < seconds]
    user_actions.append(now)
    action_cooldown[f"{user_id}_{action_name}"] = user_actions
    return len(user_actions) > max_count

# ==================== أنظمة الحماية ====================

@bot.event
async def on_guild_channel_delete(channel):
    entry = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_delete)
    if entry and entry.user.id not in TRUSTED_IDS:
        member = channel.guild.get_member(entry.user.id)
        if member:
            await strip_roles(member, "حذف قناة/فئة من السيرفر", f"اسم الروم: {channel.name} | الايدي: `{channel.id}` | النوع: {channel.type}")
            try: await channel.clone(reason="إعادة الحماية")
            except: pass

@bot.event
async def on_guild_channel_update(before, after):
    entry = await get_audit_executor(after.guild, discord.AuditLogAction.channel_update)
    if entry and entry.user.id not in TRUSTED_IDS:
        member = after.guild.get_member(entry.user.id)
        if member:
            await strip_roles(member, "تعديل خصائص أو صلاحيات القنوات", f"الروم المتأثر: {after.mention} (`{after.id}`)", f"الاسم قبل: {before.name} | بعد: {after.name}")
            try: await after.edit(name=before.name, topic=before.topic, nsfw=before.nsfw, category=before.category, sync_permissions=True)
            except: pass

@bot.event
async def on_guild_channel_create(channel):
    entry = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_create)
    if entry and entry.user.id not in TRUSTED_IDS:
        if check_spam_action(entry.user.id, "channel_create", max_count=3, seconds=10):
            member = channel.guild.get_member(entry.user.id)
            if member: await strip_roles(member, "سبام إنشاء قنوات مكثف", f"الروم المكتشف: {channel.name}")
            try: await channel.delete()
            except: pass

@bot.event
async def on_guild_role_delete(role):
    entry = await get_audit_executor(role.guild, discord.AuditLogAction.role_delete)
    if entry and entry.user.id not in TRUSTED_IDS:
        member = role.guild.get_member(entry.user.id)
        if member:
            await strip_roles(member, "حذف رتبة من السيرفر", f"اسم الرتبة المحذوفة: {role.name} (`{role.id}`)")
            try: await role.guild.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, mentionable=role.mentionable)
            except: pass

@bot.event
async def on_guild_role_create(role):
    entry = await get_audit_executor(role.guild, discord.AuditLogAction.role_create)
    if entry and entry.user.id not in TRUSTED_IDS:
        if check_spam_action(entry.user.id, "role_create", max_count=3, seconds=10):
            member = role.guild.get_member(entry.user.id)
            if member: await strip_roles(member, "سبام إنشاء رتب مكثف", f"الرتبة المكتشفة: {role.name}")
            try: await role.delete()
            except: pass

@bot.event
async def on_guild_role_update(before, after):
    entry = await get_audit_executor(after.guild, discord.AuditLogAction.role_update)
    if entry and entry.user.id not in TRUSTED_IDS:
        member = after.guild.get_member(entry.user.id)
        if member:
            for perm in DANGEROUS_PERMS:
                if getattr(after.permissions, perm) and not getattr(before.permissions, perm):
                    await strip_roles(member, f"محاولة تفعيل صلاحية خطيرة ({perm})", f"الرتبة المعدلة: {after.name} (`{after.id}`)")
                    try: await after.edit(permissions=before.permissions)
                    except: pass
                    return
            await strip_roles(member, "تعديل رتبة بشكل غير مصرح به", f"الرتبة المعدلة: {after.name} (`{after.id}`)")
            try: await after.edit(permissions=before.permissions, color=before.color, hoist=before.hoist, mentionable=before.mentionable)
            except: pass

@bot.event
async def on_member_update(before, after):
    # حماية إعطاء رتب خطيرة لأعضاء أو تعديل صلاحياتهم المباشرة
    if len(before.roles) != len(after.roles):
        entry = await get_audit_executor(after.guild, discord.AuditLogAction.member_role_update)
        if entry and entry.user.id not in TRUSTED_IDS:
            added_roles = [r for r in after.roles if r not in before.roles]
            for role in added_roles:
                if any(getattr(role.permissions, perm) for perm in DANGEROUS_PERMS):
                    admin_member = after.guild.get_member(entry.user.id)
                    if admin_member:
                        # جلب الشخص المستهدف الذي كان سيعطى الرتبة
                        await strip_roles(admin_member, "إعطاء رتبة خطيرة أو صلاحيات إدارة لعضو آخر", 
                                          f"الرتبة الخطيرة: {role.name} (`{role.id}`)", 
                                          f"👤 **الشخص المستهدف الممنوح له:** {after.mention} (`{after.id}`)")
                        try: await after.remove_roles(role)
                        except: pass

@bot.event
async def on_webhooks_update(channel):
    await asyncio.sleep(0.5)
    async for entry in channel.guild.audit_logs(limit=1):
        if entry.action in [discord.AuditLogAction.webhook_create, discord.AuditLogAction.webhook_update, discord.AuditLogAction.webhook_delete]:
            if entry.user.id not in TRUSTED_IDS:
                member = channel.guild.get_member(entry.user.id)
                if member:
                    action_name = "إنشاء" if entry.action == discord.AuditLogAction.webhook_create else "تعديل" if entry.action == discord.AuditLogAction.webhook_update else "حذف"
                    await strip_roles(member, f"التلاعب بالويب هوك ({action_name})", f"الروم المتأثر: {channel.mention}", f"اسم الويب هوك: {entry.target.name if entry.target else 'غير معروف'}")
                    if entry.action == discord.AuditLogAction.webhook_create:
                        try:
                            wh = await bot.fetch_webhook(entry.target.id)
                            await wh.delete()
                        except: pass

@bot.event
async def on_guild_update(before, after):
    entry = await get_audit_executor(after, discord.AuditLogAction.guild_update)
    if entry and entry.user.id not in TRUSTED_IDS:
        member = after.get_member(entry.user.id)
        if member:
            await strip_roles(member, "تعديل وتخريب إعدادات وهواية السيرفر", f"اسم السيرفر: {after.name}", f"تم محاولة تعديل (الاسم/الأيقونة/البانر/مستوى التحقق)")
            try: await after.edit(name=before.name, icon=before.icon, banner=before.banner, description=before.description, verification_level=before.verification_level, mfa_level=before.mfa_level)
            except: pass

@bot.event
async def on_guild_emojis_update(guild, before, after):
    if len(before) > len(after):
        entry = await get_audit_executor(guild, discord.AuditLogAction.emoji_delete)
        if entry and entry.user.id not in TRUSTED_IDS:
            member = guild.get_member(entry.user.id)
            if member: await strip_roles(member, "حذف إيموجيات السيرفر")

@bot.event
async def on_guild_stickers_update(guild, before, after):
    if len(before) > len(after):
        entry = await get_audit_executor(guild, discord.AuditLogAction.sticker_delete)
        if entry and entry.user.id not in TRUSTED_IDS:
            member = guild.get_member(entry.user.id)
            if member: await strip_roles(member, "حذف ستيكرات السيرفر")

@bot.event
async def on_invite_create(invite):
    executor = invite.inviter
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "invite_create", max_count=4, seconds=10):
            member = invite.guild.get_member(executor.id)
            if member: await strip_roles(member, "سبام إنشاء روابط دعوات مكثف", f"كود الدعوة المحدث: {invite.code}")
            try: await invite.delete()
            except: pass

@bot.event
async def on_member_ban(guild, user):
    entry = await get_audit_executor(guild, discord.AuditLogAction.ban)
    if entry and entry.user.id not in TRUSTED_IDS:
        if check_spam_action(entry.user.id, "mass_ban", max_count=3, seconds=300):
            member = guild.get_member(entry.user.id)
            if member: await strip_roles(member, "سبام باندات عشوائية ومكثفة (Mass Ban)", f"آخر عضو تم تبنيده: {user.name}")

@bot.event
async def on_member_remove(member):
    entry = await get_audit_executor(member.guild, discord.AuditLogAction.kick)
    if entry and entry.user.id not in TRUSTED_IDS:
        if check_spam_action(entry.user.id, "mass_kick", max_count=3, seconds=300):
            admin_member = member.guild.get_member(entry.user.id)
            if admin_member: await strip_roles(admin_member, "سبام طرد للأعضاء (Kick Spam)", f"آخر عضو طُرد: {member.name}")

@bot.event
async def on_member_join(member):
    if member.bot:
        entry = await get_audit_executor(member.guild, discord.AuditLogAction.bot_add)
        if entry and entry.user.id not in TRUSTED_IDS:
            try:
                await member.ban(reason="دخول بوت غير مصرح به")
                inviter = member.guild.get_member(entry.user.id)
                if inviter: 
                    await strip_roles(inviter, "إدخال بوت غريب ومخرب للسيرفر", 
                                      f"🤖 **البوت الذي طُرد:** {member.mention} (`{member.id}`)")
            except: pass

@bot.event
async def on_message(message):
    if not message.guild or message.author.bot or message.author.id in TRUSTED_IDS:
        await bot.process_commands(message)
        return

    # حماية منشن ايفري وهير أو منشن أكثر من 10 أعضاء
    if message.mention_everyone or len(message.mentions) >= 10:
        if check_spam_action(message.author.id, "mass_mention", max_count=3, seconds=300):
            await strip_roles(message.author, "سبام منشن جماعي أو عشوائي للأعضاء (Mass Mention)")
            return

    # حماية سبام المنشن العادي (إذا كرر منشن شخص أو رتبة 3 مرات ورا بعض بسرعة)
    if len(message.mentions) > 0 or len(message.role_mentions) > 0:
        if check_spam_action(message.author.id, "mention_spam", max_count=3, seconds=10):
            await strip_roles(message.author, "سبام وتكرار المنشن المزعج للأعضاء أو الرتب")
            return

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if not message.guild or message.author.bot:
        return
    entry = await get_audit_executor(message.guild, discord.AuditLogAction.message_delete)
    if entry and entry.user.id not in TRUSTED_IDS:
        if check_spam_action(entry.user.id, "message_delete_spam", max_count=15, seconds=10):
            member = message.guild.get_member(entry.user.id)
            if member: await strip_roles(member, "سبام حذف رسائل الأعضاء بكثرة")

# ==================== أوامر التحكم والفك ====================

@bot.command(name="انطم")
async def mute_all(ctx):
    if ctx.author.id not in TRUSTED_IDS: return
    if ctx.author.voice and ctx.author.voice.channel:
        for member in ctx.author.voice.channel.members:
            if member.id not in TRUSTED_IDS and not member.bot:
                await member.edit(mute=True)
        await ctx.send("🤫 تم كتم الجميع في الروم الصوتي.")
    else: await ctx.send("يجب أن تكون داخل روم صوتي أولاً")

@bot.command(name="تكلم")
async def unmute_all(ctx):
    if ctx.author.id not in TRUSTED_IDS: return
    if ctx.author.voice and ctx.author.voice.channel:
        for member in ctx.author.voice.channel.members:
            await member.edit(mute=False)
        await ctx.send("🔊 تم فتح المايك عن الجميع.")
    else: await ctx.send("يجب أن تكون داخل روم صوتي أولاً")

@bot.command(name="فك")
async def restore_roles(ctx, member: discord.Member):
    if ctx.author.id not in TRUSTED_IDS: return
    if member.id in removed_roles_backup:
        roles_to_add = [r for r in removed_roles_backup[member.id] if r in ctx.guild.roles and r.position < ctx.guild.me.top_role.position]
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="إعادة الرتب بواسطة الأونر")
                del removed_roles_backup[member.id]
                await ctx.send(f"✅ تم إعادة الرتب بنجاح للعضو: {member.mention}")
            except: await ctx.send("حدث خطأ، تأكد من صلاحيات وترتيب رتبة البوت.")
        else: await ctx.send("لم يتم العثور على رتب صالحة لإعادتها.")
    else: await ctx.send("لا توجد رتب محفوظة ومقشوعة لهذا الشخص في الرام.")

BOT_TOKEN = os.environ.get("DISCORD_TOKEN")
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("خطأ: لم يتم العثور على متغير البيئة DISCORD_TOKEN")
