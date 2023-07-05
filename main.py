import os
import shelve
import sqlite3
import traceback

from discord import *
from discord.ext import commands
from dotenv import load_dotenv

# load bot token
load_dotenv(".env")
TOKEN = os.getenv("DISCORD_TOKEN")
# set up bot
intents = Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
# allow aliases to persist when bot is offline
aliases = shelve.open("aliases")
# set up sqlite3 connection
con = sqlite3.connect(
    "quotes.db", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
)
db = con.cursor()
# shorthand for my discord user object
me: User


@bot.command(name="setalias", help="change your alias to a specified nickname")
async def set_alias(ctx: commands.Context, nickname: str, mention: User = None):
    if not nickname:
        await ctx.send("Please provide a nickname you want")
        return
    # whose alias we are changing
    target = mention.name if mention else ctx.message.author.name
    # Only I can change other people's aliases
    if mention:
        if ctx.author != me:
            await ctx.send("Permission denied. You are not Asher")
            return
    # set new alias
    old = aliases.get(target, default="None")
    aliases[target] = nickname

    await ctx.send(
        f'Changed {target}\'s alias from "{old}" to "{aliases[ctx.message.author.name]}"'
    )


@bot.command(name="getalias", help="get your current alias")
async def get_alias(ctx: commands.Context, mention: User = None):
    # whose alias we are getting
    target = mention.name if mention else ctx.message.author.name

    await ctx.send(
        f"{target}'s current alias is \"{aliases.get(target, default='None')}\""
    )


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user.name}")
    # set up status
    await bot.change_presence(status=Status.online, activity=Game(name="!qhelp"))
    global me
    # me!
    me = await bot.fetch_user(269227960156946454)

@bot.event
async def on_connect():
    global aliases
    aliases = shelve.open("aliases")
@bot.event
async def on_disconnect():
    # sync shelf
    aliases.close()


@bot.event
async def on_command_error(ctx, error):
    # send me dm with traceback
    await me.send("something has errored: here is the traceback")
    await me.send(
        "".join(traceback.format_exception(type(error), error, error.__traceback__))
    )

    await ctx.send("An error has occurred, hopefully its not fatal")


@bot.command(
    name="qadd",
    help="adds a specific message with given message id to a user's list of quotes",
)
async def add_quote(
    ctx: commands.Context, message_id: int = None, mention: User = None
):
    if not message_id:
        await ctx.send("Please provide an id of the message you want to quote")
        return

    quote = await ctx.channel.fetch_message(message_id)
    time = quote.created_at
    # mention can be used to manually override who the quote belongs to
    author_id = mention.id if mention else quote.author.id
    stripped_message = quote.content.strip("'\"` ")
    # add quote to db
    db.execute(
        "INSERT into quotes (user_id, quote, time) VALUES (?, ?, ?)",
        (author_id, stripped_message, time),
    )
    con.commit()

    author = mention or quote.author
    await ctx.send(
        f'Added "{stripped_message}" to {aliases[author.name] if author.name in aliases else author.display_name}\'s quotes!'
    )


@bot.command(
    name="qget",
    help="gets a random message from given user (defaults to user who sent command) that has been added "
    "using !qadd",
)
async def get_quote(ctx: commands.Context, person: User = None, keyword: str = None):
    author = person or ctx.author
    # keyword matching
    # use sql random instead of python, better performance
    if keyword:
        db.execute(
            "SELECT quote, time FROM quotes WHERE user_id=? AND quote LIKE ? ORDER BY RANDOM()",
            (author.id, "%" + keyword + "%"),
        )
    else:
        db.execute(
            "SELECT quote, time FROM quotes WHERE user_id=? ORDER BY RANDOM()",
            (author.id,),
        )

    quote = db.fetchone()
    if not quote:
        if keyword:
            await ctx.send(
                "No quotes found for this user matching the pattern provided"
            )
        else:
            await ctx.send(
                "No quotes found for this user, add some with `!qadd [message_id]`"
            )
        return

    timestamp = quote[1]
    time = timestamp.time()
    date = timestamp.date()
    await ctx.send(
        f'At {time.isoformat(timespec="minutes")} on {date.isoformat()}, {author.mention} said "{quote[0]}"'
    )


@bot.command(name="qremove", help="removes a given message_id from the database")
async def remove_quote(ctx: commands.Context, message_id: int = None):
    if not message_id:
        await ctx.send("Please provide the id of a message you want to remove")
        return

    # first find the quote associated with that id
    # try checking the channel that the command was used in
    try:
        quote = await ctx.fetch_message(message_id)
    except NotFound:
        # check all channels in guild
        for c in ctx.guild.channels:
            try:
                quote = await c.fetch_message(message_id)
                break
            except NotFound:
                pass
        else:
            # triggers if quote was not found
            await ctx.send("No message was found with that id")
            return

    # get quote
    db.execute("SELECT * FROM quotes WHERE quote=?", (quote.content,))
    deleted = list(db.fetchall())

    if not deleted:
        await ctx.send("No quote was found with that id")
        return
    # delete quote from database
    db.execute("DELETE FROM quotes WHERE quote=?", (quote.content,))
    con.commit()

    author = quote.author
    await ctx.send(
        f'Removed "{quote.content}" from {aliases[author.name] if author.name in aliases else author.display_name}\'s quotes '
    )


@bot.command(name="qgetall", help="get all quotes by a user")
async def get_all(ctx: commands.Context, mention: User = None):
    author = mention if mention else ctx.author
    # get all quotes
    db.execute("SELECT quote, time FROM quotes WHERE user_id=?", (author.id,))
    quotes = db.fetchall()

    if not quotes or len(quotes) == 0:
        await ctx.send(
            "No quotes found for this user, add some with `!qadd [message_id]`"
        )
        return

    await ctx.send(f"Now listing all quotes for {author.mention}\n")
    for quote in quotes:
        datetime = quote[1]
        time = datetime.time()
        date = datetime.date()
        await ctx.send(
            f'At {time.isoformat(timespec="minutes")} on {date.strftime("%m/%d")}, '
            f'{aliases.get(author.name, default=author.display_name)} said "{quote[0]}" '
        )


@bot.command(name="qhelp", help="list of commands and brief description")
async def help(ctx: commands.Context):
    await ctx.send(
        "!getalias to get your current alias\n"
        + "!setalias [alias] to change your alias to the one provided\n"
        + "!qadd [message_id] (mention) to add that message as a quote, use mention to override the author "
        "to the user mentioned\n "
        + "!qget (user_mention) (keyword) (list) to get a random quote from the specified user (or yourself if user is "
        'not provided) matching keyword if provided. providing "list" will print out all of the matching quotes\n '
        + "!qgetall (user_mention) to get all the quotes from a user (defaults to user who sent command)\n"
        + "!qremove [message_id] to remove that message as a quote\n"
        + "!qhelp to show this message again"
    )


bot.run(TOKEN)
