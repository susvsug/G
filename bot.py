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

# قائمة الحسابات الموثوقة (الأونرات)
TRUSTED_IDS = [1423421691773714482, 1422918463034228757]

# الذاكرة المؤقتة للرتب والسبام
removed_roles_backup = {}
action_cooldown = defaultdict(list)

# الصلاحيات الخطيرة التي سيتم مراقبتها ومنع منحها
DANGEROUS_PERMS = ['administrator', 'manage_guild', 'ban_members', 'kick_members', 'manage_roles', 'manage_channels', 'manage_webhooks']

# --- دالة إرسال الإمبيد التفصيلي للأونرات على الخاص ---
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

# --- دالة قشع الرتب ---
async def strip_roles(member: discord.Member, reason: str, target_info=None, extra_info=None):
    if member.id in TRUSTED_IDS or member.bot:
        return
    
    all_removable_roles = [role for role in member.roles if not role.is_default() and role.position < member.guild.me.top_role.position]
    
    if all_removable_roles:
        removed_roles_backup[member.id] = all_removable_roles
        try:
            await member.remove_roles(*all_removable_roles, reason=f"[الحماية القصوى] - {reason}")
            try:
                await member.send("⚠️ تم سحب رتبك وصلاحياتك من السيرفر بسبب محاولة تخريب أو تجاوز الأنظمة.")
            except: pass
            
            title_msg = "🚨 رصد محاولة تخريب وقشع الرتب"
            desc_msg = f"👤 **العضو المخالف:** {member.mention}\n🆔 **ايدي العضو:** `{member.id}`\n❓ **السبب:** {reason}"
            await send_owner_embed(title_msg, desc_msg, target_info, extra_info)
        except discord.Forbidden:
            print(f"فشل قشع رتب {member.name}")

# --- دالة التحقق الدقيق من فاعل الإجراء ---
async def get_audit_executor(guild, action_type, check_time=5):
    await asyncio.sleep(0.6)
    async for entry in guild.audit_logs(limit=3, action=action_type):
        now = datetime.datetime.now(datetime.timezone.utc)
        if (now - entry.created_at).total_seconds() < check_time:
            return entry.user
    return None

# --- دالة مراقبة السبام والتكرار ---
def check_spam_action(user_id, action_name, max_count=3, seconds=5):
    now = datetime.datetime.utcnow()
    user_actions = action_cooldown[f"{user_id}_{action_name}"]
    user_actions = [t for t in user_actions if (now - t).total_seconds() < seconds]
    user_actions.append(now)
    action_cooldown[f"{user_id}_{action_name}"] = user_actions
    return len(user_actions) > max_count

# ==================== أنظمة الحماية (Events) ====================

# 1. حماية الرومات (حذف، تعديل، إنشاء، واسترجاع الخصائص والفئات والصوتيات والمنتديات)
@bot.event
async def on_guild_channel_delete(channel):
    executor = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_delete)
    if executor and executor.id not in TRUSTED_IDS:
        member = channel.guild.get_member(executor.id)
        if member:
            await strip_roles(member, "حذف قناة/فئة من السيرفر", f"الاسم: {channel.name} | النوع: {channel.type}")
            try: await channel.clone(reason="إعادة القناة المحذوفة تلقائياً بواسطة الحماية")
            except: pass

@bot.event
async def on_guild_channel_update(before, after):
    executor = await get_audit_executor(after.guild, discord.AuditLogAction.channel_update)
    if executor and executor.id not in TRUSTED_IDS:
        member = after.guild.get_member(executor.id)
        if member:
            await strip_roles(member, "تعديل غير مصرح به على خصائص أو صلاحيات القنوات", f"القناة: {after.mention}")
            try: await after.edit(name=before.name, topic=before.topic, nsfw=before.nsfw, category=before.category, sync_permissions=True)
            except: pass

@bot.event
async def on_guild_channel_create(channel):
    executor = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_create)
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "channel_create", max_count=3, seconds=10):
            member = channel.guild.get_member(executor.id)
            if member: await strip_roles(member, "سبام إنشاء قنوات (Channel Nuke)")
            try: await channel.delete(reason="تصفية رومات التخريب")
            except: pass

# 2. حماية الرتب (حذف، إنشاء، تعديل، وحماية الصلاحيات الخطيرة ورتبة Administrator)
@bot.event
async def on_guild_role_delete(role):
    executor = await get_audit_executor(role.guild, discord.AuditLogAction.role_delete)
    if executor and executor.id not in TRUSTED_IDS:
        member = role.guild.get_member(executor.id)
        if member:
            await strip_roles(member, f"حذف رتبة من السيرفر ({role.name})")
            try: await role.guild.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, mentionable=role.mentionable, reason="إعادة الرتبة المحذوفة بواسطة الحماية")
            except: pass

@bot.event
async def on_guild_role_create(role):
    executor = await get_audit_executor(role.guild, discord.AuditLogAction.role_create)
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "role_create", max_count=3, seconds=10):
            member = role.guild.get_member(executor.id)
            if member: await strip_roles(member, "سبام إنشاء رتب (Role Nuke)")
            try: await role.delete()
            except: pass

@bot.event
async def on_guild_role_update(before, after):
    executor = await get_audit_executor(after.guild, discord.AuditLogAction.role_update)
    if executor and executor.id not in TRUSTED_IDS:
        member = after.guild.get_member(executor.id)
        if member:
            # التحقق من الصلاحيات الخطيرة المضافة
            for perm in DANGEROUS_PERMS:
                if getattr(after.permissions, perm) and not getattr(before.permissions, perm):
                    await strip_roles(member, f"محاولة تفعيل صلاحية خطيرة ({perm}) على رتبة: {after.name}")
                    try: await after.edit(permissions=before.permissions)
                    except: pass
                    return

            await strip_roles(member, "تعديل خصائص أو صلاحيات رتبة بشكل غير مصرح به", f"الرتبة: {after.name}")
            try: await after.edit(permissions=before.permissions, color=before.color, hoist=before.hoist, mentionable=before.mentionable)
            except: pass

# 3. حماية تعديل صلاحيات الأعضاء المباشرة ومنحهم رتب خطيرة
@bot.event
async def on_member_update(before, after):
    if len(before.roles) != len(after.roles):
        executor = await get_audit_executor(after.guild, discord.AuditLogAction.member_role_update)
        if executor and executor.id not in TRUSTED_IDS:
            # إذا تم إضافة رتبة جديدة للعضو
            added_roles = [r for r in after.roles if r not in before.roles]
            for role in added_roles:
                # التحقق إذا كانت الرتبة الممنوحة تحتوي على أي صلاحية خطيرة
                if any(getattr(role.permissions, perm) for perm in DANGEROUS_PERMS):
                    admin_member = after.guild.get_member(executor.id)
                    if admin_member:
                        await strip_roles(admin_member, f"محاولة إعطاء رتبة خطيرة تحتوي على صلاحيات إدارة للعضو {after.name}")
                        try: await after.remove_roles(role, reason="إلغاء الرتبة الخطيرة فوراً")
                        except: pass

# 4. حماية الويب هوك الكاملة (إنشاء، تعديل، حذف)
@bot.event
async def on_webhooks_update(channel):
    # نتحقق من نوع التعديل عبر سجلات التدقيق
    await asyncio.sleep(0.5)
    async for entry in channel.guild.audit_logs(limit=1):
        if entry.action in [discord.AuditLogAction.webhook_create, discord.AuditLogAction.webhook_update, discord.AuditLogAction.webhook_delete]:
            if entry.user.id not in TRUSTED_IDS:
                member = channel.guild.get_member(entry.user.id)
                if member:
                    await strip_roles(member, f"التلاعب بالويب هوك (إنشاء/تعديل/حذف) في روم {channel.name}")
                    if entry.action == discord.AuditLogAction.webhook_create:
                        try:
                            wh = await bot.fetch_webhook(entry.target.id)
                            await wh.delete(reason="حذف الويب هوك المحدث بواسطة المخرب")
                        except: pass

# 5. حماية إعدادات السيرفر (الاسم، الأيقونة، البانر، الوصف، مستوى التحقق، MFA)
@bot.event
async def on_guild_update(before, after):
    executor = await get_audit_executor(after, discord.AuditLogAction.guild_update)
    if executor and executor.id not in TRUSTED_IDS:
        member = after.get_member(executor.id)
        if member:
            await strip_roles(member, "تعديل إعدادات أو هوية ومظهر السيرفر")
            try:
                # استرجاع الخصائص الأساسية فوراً
                await after.edit(
                    name=before.name, icon=before.icon, banner=before.banner, 
                    description=before.description, verification_level=before.verification_level,
                    mfa_level=before.mfa_level
                )
            except: pass

# 6. حماية الإيموجيات، الستيكرات، وإنشاء الدعوات المكثف (Invite Spam)
@bot.event
async def on_guild_emojis_update(guild, before, after):
    if len(before) > len(after):
        executor = await get_audit_executor(guild, discord.AuditLogAction.emoji_delete)
        if executor and executor.id not in TRUSTED_IDS:
            member = guild.get_member(executor.id)
            if member: await strip_roles(member, "حذف وتخريب إيموجيات السيرفر")

@bot.event
async def on_guild_stickers_update(guild, before, after):
    if len(before) > len(after):
        executor = await get_audit_executor(guild, discord.AuditLogAction.sticker_delete)
        if executor and executor.id not in TRUSTED_IDS:
            member = guild.get_member(executor.id)
            if member: await strip_roles(member, "حذف وتخريب ستيكرات السيرفر")

@bot.event
async def on_invite_create(invite):
    executor = invite.inviter
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "invite_create", max_count=4, seconds=10):
            member = invite.guild.get_member(executor.id)
            if member: await strip_roles(member, "سبام إنشاء روابط دعوات مكثف (Invite Spam)")
            try: await invite.delete()
            except: pass

# 7. حماية طرد وحظر الأعضاء المكثف (Mass Ban / Kick Spam) والبوتات الغريبة
@bot.event
async def on_member_ban(guild, user):
    executor = await get_audit_executor(guild, discord.AuditLogAction.ban)
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "mass_ban", max_count=3, seconds=300):
            member = guild.get_member(executor.id)
            if member: await strip_roles(member, "عمل باندات عشوائية ومكثفة للأعضاء")

@bot.event
async def on_member_remove(member):
    # تفحص إذا كان الخروج طرد (Kick) وليس مغادرة عادية
    executor = await get_audit_executor(member.guild, discord.AuditLogAction.kick)
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "mass_kick", max_count=3, seconds=300):
            admin_member = member.guild.get_member(executor.id)
            if admin_member: await strip_roles(admin_member, "سبام طرد للأعضاء من السيرفر (Kick Spam)")

@bot.event
async def on_member_join(member):
    if member.bot:
        executor = await get_audit_executor(member.guild, discord.AuditLogAction.bot_add)
        if executor and executor.id not in TRUSTED_IDS:
            try:
                await member.ban(reason="دخول بوت غير مصرح به")
                inviter = member.guild.get_member(executor.id)
                if inviter: await strip_roles(inviter, "إدخال بوت غريب للسيرفر", f"البوت: {member.name}")
            except: pass

# 8. حماية الرسائل والمنشن الجماعي وحذف الرسائل (Delete Message Spam)
@bot.event
async def on_message(message):
    if not message.guild or message.author.bot or message.author.id in TRUSTED_IDS:
        await bot.process_commands(message)
        return

    # حماية منشن ايفري وهير أو منشن عدد كبير من الأعضاء في رسالة واحدة (أكثر من 10 أعضاء)
    if message.mention_everyone or len(message.mentions) >= 10:
        if check_spam_action(message.author.id, "mass_mention", max_count=3, seconds=300):
            await strip_roles(message.author, "سبام منشن جماعي أو منشن عشوائي للأعضاء (Mass Mention)")

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if not message.guild or message.author.bot:
        return
    executor = await get_audit_executor(message.guild, discord.AuditLogAction.message_delete)
    if executor and executor.id not in TRUSTED_IDS:
        if check_spam_action(executor.id, "message_delete_spam", max_count=15, seconds=10):
            member = message.guild.get_member(executor.id)
            if member: await strip_roles(member, "سبام حذف رسائل الأعضاء بكثرة (Delete Message Spam)")

# ==================== أوامر التحكم والفك الحصرية ====================

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
