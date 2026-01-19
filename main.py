import discord
from discord.ext import commands
from discord import app_commands
import json

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "owner": None,
            "admin": None,
            "log_channel": None,
            "watched_channels": []
        }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ───────────── READY ─────────────
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

# ───────────── HELPERS ─────────────
def owner_or_admin(interaction: discord.Interaction):
    return interaction.user.id in (data["owner"], data["admin"])

# ───────────── SLASH COMMANDS ─────────────
@tree.command(name="setowner", description="Set the bot owner (one time)")
async def setowner(interaction: discord.Interaction):
    if data["owner"] is not None:
        await interaction.response.send_message("❌ Owner already set.", ephemeral=True)
        return

    data["owner"] = interaction.user.id
    save_data(data)
    await interaction.response.send_message("✅ You are now the owner.", ephemeral=True)

@tree.command(name="setadmin", description="Set bot admin")
@app_commands.describe(user="User to set as admin")
async def setadmin(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != data["owner"]:
        await interaction.response.send_message("❌ Only owner can do this.", ephemeral=True)
        return

    data["admin"] = user.id
    save_data(data)
    await interaction.response.send_message(f"✅ {user.mention} is now admin.", ephemeral=True)

@tree.command(name="setlog", description="Set log channel")
@app_commands.describe(channel="Log channel")
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    if not owner_or_admin(interaction):
        await interaction.response.send_message("❌ Not authorized.", ephemeral=True)
        return

    data["log_channel"] = channel.id
    save_data(data)
    await interaction.response.send_message("✅ Log channel set.", ephemeral=True)

@tree.command(name="watch", description="Watch a channel for deletions")
@app_commands.describe(channel="Channel to watch")
async def watch(interaction: discord.Interaction, channel: discord.TextChannel):
    if not owner_or_admin(interaction):
        await interaction.response.send_message("❌ Not authorized.", ephemeral=True)
        return

    if channel.id not in data["watched_channels"]:
        data["watched_channels"].append(channel.id)
        save_data(data)

    await interaction.response.send_message("👀 Channel is now monitored.", ephemeral=True)


# ───────────── MESSAGE DELETE EVENT ─────────────
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    if message.channel.id not in data["watched_channels"]:
        return

    guild = message.guild
    author = message.author

    embed = discord.Embed(
        title="🗑️ Message Deleted",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(name="User", value=f"{author} ({author.id})", inline=False)
    embed.add_field(name="Channel", value=message.channel.mention, inline=False)
    embed.add_field(
        name="Message",
        value=message.content if message.content else "*No text (embed / image)*",
        inline=False
    )

    if message.attachments:
        embed.add_field(
            name="Attachments",
            value="\n".join(a.url for a in message.attachments),
            inline=False
        )

    embed.set_footer(text=f"Server: {guild.name}")

    # Send to log channel
    if not data["log_channel"]:
        return

    log_channel = bot.get_channel(data["log_channel"])

    if log_channel:
        await log_channel.send(embed=embed)

    # DM owner
    try:
            owner = bot.get_user(data["owner"])
            if owner:
                await owner.send(embed=embed)

    except:
        pass


# ───────────── RUN ─────────────
import os
bot.run(os.getenv("DISCORD_TOKEN"))
