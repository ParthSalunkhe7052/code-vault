"""
Discord Moderation Bot - Medium Complexity Example
A realistic bot that customers might want to license and protect
"""

import discord
from discord.ext import commands
import asyncio
import json
from datetime import datetime, timedelta
import os

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory storage (would be database in production)
warnings_db = {}
muted_users = {}
auto_responses = {}


class ModerationCog(commands.Cog):
    """Moderation commands for server management"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn_user(self, ctx, member: discord.Member, *, reason: str):
        """Warn a user for breaking rules"""
        if member.id not in warnings_db:
            warnings_db[member.id] = []

        warning = {
            "timestamp": datetime.now().isoformat(),
            "moderator": ctx.author.id,
            "reason": reason,
        }
        warnings_db[member.id].append(warning)

        embed = discord.Embed(
            title="⚠️ User Warned",
            color=discord.Color.orange(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(
            name="Total Warnings", value=str(len(warnings_db[member.id])), inline=False
        )

        await ctx.send(embed=embed)

        # Auto-action if too many warnings
        if len(warnings_db[member.id]) >= 3:
            await self.auto_mute(ctx, member, duration=3600)

    @commands.command(name="warnings")
    async def check_warnings(self, ctx, member: discord.Member = None):
        """Check warnings for a user"""
        target = member or ctx.author

        if target.id not in warnings_db or not warnings_db[target.id]:
            await ctx.send(f"✅ {target.display_name} has no warnings!")
            return

        embed = discord.Embed(
            title=f"⚠️ Warnings for {target.display_name}",
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )

        for i, warning in enumerate(warnings_db[target.id], 1):
            moderator = await self.bot.fetch_user(warning["moderator"])
            embed.add_field(
                name=f"Warning #{i}",
                value=f"**Reason:** {warning['reason']}\n**Date:** {warning['timestamp'][:10]}\n**Moderator:** {moderator.name}",
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(name="clearwarnings")
    @commands.has_permissions(administrator=True)
    async def clear_warnings(self, ctx, member: discord.Member):
        """Clear all warnings for a user"""
        if member.id in warnings_db:
            warnings_db[member.id] = []
            await ctx.send(f"✅ Cleared all warnings for {member.mention}")
        else:
            await ctx.send(f"ℹ️ {member.mention} has no warnings to clear")

    async def auto_mute(self, ctx, member: discord.Member, duration: int):
        """Automatically mute user for repeated violations"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")

        if not mute_role:
            # Create mute role if it doesn't exist
            mute_role = await ctx.guild.create_role(
                name="Muted", reason="Auto-mute system"
            )

            # Set permissions for all channels
            for channel in ctx.guild.channels:
                await channel.set_permissions(
                    mute_role, send_messages=False, speak=False
                )

        await member.add_roles(mute_role)
        muted_users[member.id] = datetime.now() + timedelta(seconds=duration)

        await ctx.send(
            f"🔇 {member.mention} has been auto-muted for 1 hour due to excessive warnings!"
        )

        # Schedule unmute
        await asyncio.sleep(duration)
        if member.id in muted_users:
            await member.remove_roles(mute_role)
            del muted_users[member.id]


class UtilityCog(commands.Cog):
    """Utility commands for server management"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="serverinfo")
    async def server_info(self, ctx):
        """Display server information"""
        guild = ctx.guild

        embed = discord.Embed(
            title=f"📊 {guild.name} Server Info",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(
            name="Created On",
            value=guild.created_at.strftime("%Y-%m-%d"),
            inline=True,
        )
        embed.add_field(
            name="Boost Level", value=f"Level {guild.premium_tier}", inline=True
        )

        await ctx.send(embed=embed)

    @commands.command(name="poll")
    async def create_poll(self, ctx, question: str, *options):
        """Create a poll with reactions"""
        if len(options) > 10:
            await ctx.send("❌ Maximum 10 options allowed!")
            return

        if len(options) < 2:
            await ctx.send("❌ Please provide at least 2 options!")
            return

        embed = discord.Embed(title=f"📊 {question}", color=discord.Color.green())

        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        description = ""
        for i, option in enumerate(options):
            description += f"\n{reactions[i]} {option}"

        embed.description = description
        embed.set_footer(text=f"Poll by {ctx.author.display_name}")

        poll_message = await ctx.send(embed=embed)

        for i in range(len(options)):
            await poll_message.add_reaction(reactions[i])


class AutoModCog(commands.Cog):
    """Automatic moderation features"""

    def __init__(self, bot):
        self.bot = bot
        self.spam_tracker = {}
        self.banned_words = ["badword1", "badword2"]  # Example

    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor messages for spam and banned words"""
        if message.author.bot:
            return

        # Spam detection
        user_id = message.author.id
        now = datetime.now()

        if user_id not in self.spam_tracker:
            self.spam_tracker[user_id] = []

        self.spam_tracker[user_id] = [
            msg_time
            for msg_time in self.spam_tracker[user_id]
            if (now - msg_time).seconds < 5
        ]
        self.spam_tracker[user_id].append(now)

        if len(self.spam_tracker[user_id]) > 5:
            await message.delete()
            await message.channel.send(
                f"⚠️ {message.author.mention}, please slow down! (Anti-spam)",
                delete_after=3,
            )

        # Banned words detection
        content_lower = message.content.lower()
        if any(word in content_lower for word in self.banned_words):
            await message.delete()
            await message.channel.send(
                f"⚠️ {message.author.mention}, your message contained inappropriate content!",
                delete_after=5,
            )


# Event handlers
@bot.event
async def on_ready():
    """Bot startup event"""
    print(f"✅ Bot logged in as {bot.user.name}")
    print(f"Connected to {len(bot.guilds)} servers")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="the server")
    )


@bot.event
async def on_member_join(member):
    """Welcome new members"""
    # Find welcome channel
    welcome_channel = discord.utils.get(member.guild.channels, name="welcome")

    if welcome_channel:
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}! 👋",
            description=f"Hey {member.mention}, welcome to our server!\nMake sure to read the rules.",
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        await welcome_channel.send(embed=embed)


@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    print(f"Error in {event}: {args}")


# Register cogs
async def setup_cogs():
    """Load all cogs"""
    await bot.add_cog(ModerationCog(bot))
    await bot.add_cog(UtilityCog(bot))
    await bot.add_cog(AutoModCog(bot))


# Main entry point
if __name__ == "__main__":
    # Load token from environment or config
    TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

    # Setup and run bot
    asyncio.run(setup_cogs())
    bot.run(TOKEN)
