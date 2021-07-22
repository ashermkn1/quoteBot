import os
import random
import shelve
import sys
import traceback
import sqlite3

import pytz
from discord import *
from discord.ext import commands
from dotenv import load_dotenv

# load bot token
load_dotenv('.env')
TOKEN = os.getenv('DISCORD_TOKEN')
# set up bot
bot = commands.Bot(command_prefix='!')

# set up sqlite3 connection
conn = sqlite3.connect('quotes.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
db = conn.cursor()



@bot.command(name='setalias',
             help='change your alias to a specified nickname')
async def set_alias(ctx: commands.Context, nickname: str, mention: User = None):
    if not nickname:
        await ctx.send('Please provide a nickname you want')
        return

    if mention:
        if ctx.author != me:
            await ctx.send("Permission denied. Get fucked")
            return

        old = aliases.get(mention.name,default="None")
        aliases[mention.name] = nickname
        await ctx.send(
            f'Changed {mention.name}\'s  alias from "{old}" to "{aliases[mention.name]}"'
        )
        return

    old = aliases.get(ctx.message.author.name, default="None")
    aliases[ctx.message.author.name] = nickname

    await ctx.send(
        f'Changed your alias from "{old}" to "{aliases[ctx.message.author.name]}"'
    )


@bot.command(name='getalias', help='get your current alias')
async def get_alias(ctx: commands.Context, mention: User = None):
    if mention:
        await ctx.send(f"{mention.name}'s current alias is \"{aliases[mention.name]}\"")
    else:
        await ctx.send(f'Your current alias is "{aliases[ctx.message.author.name]}"')


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')
    # load aliases from shelf
    global aliases
    aliases = shelve.open('aliases')
    # set up status
    await bot.change_presence(status=Status.online, activity=Game(name='!qhelp'))
    global me
    # me!
    me = await bot.fetch_user(269227960156946454)


@bot.event
async def on_disconnect():
    # sync shelf
    aliases.close()


@bot.event
async def on_command_error(ctx, error):
    # send me dm with traceback
    await me.send('something has errored: here is the traceback')
    await me.send("".join(traceback.format_exception(type(error), error, error.__traceback__)))
    await ctx.send("An error has occurred, hopefully its not fatal")


@bot.command(name='qadd',
             help="adds a specific message with given message id to a user's list of quotes")
async def add_quote(ctx: commands.Context, message_id: int = None, mention: User = None):
    if not message_id:
        await ctx.send('Please provide an id of the message you want to quote')
        return

    quote = await ctx.channel.fetch_message(message_id)
    time = quote.created_at
    # add quote to db
    if mention:
        db.execute(
            'INSERT into quotes (user_id, quote, time) VALUES (?, ?, ?)',
            (mention.id, quote.content.strip('```'), time))
    else:
        db.execute(
            'INSERT into quotes (user_id, quote, time) VALUES (?, ?, ?)',
            (quote.author.id, quote.content.strip('```'), time))
    conn.commit()

    author = mention.name if mention else quote.author.name
    await ctx.send(
        f'Added "{quote.content}" to {aliases[author] if author in aliases else quote.author.display_name}\'s quotes!'
    )


@bot.command(name='qget',
             help="gets a random message from given user (defaults to user who sent command) that has been added "
                  "using !qadd")
async def get_quote(ctx: commands.Context,
                    person: User = None,
                    keyword: str = None,
                    all: str = None):

    author = person or ctx.author
    # keyword matching
    if keyword:
        db.execute(
            "SELECT quote, time FROM quotes WHERE user_id=? AND quote LIKE ?",
            (author.id, '%' + keyword + '%'))

    else:
        db.execute("SELECT quote, time FROM quotes WHERE user_id=?",
                   (author.id,))

    quotes = db.fetchall()
    if len(quotes) == 0:
        if keyword:
            await ctx.send(
                'No quotes found for this user matching the pattern provided'
            )
            return
        await ctx.send(
            'No quotes found for this user, add some with `!qadd [message_id]`'
        )
        return
    if all == 'list':
        for quote in quotes:
            timestamp = quote[1].astimezone(pytz.timezone("US/Eastern"))
            time = timestamp.time()
            date = timestamp.date()
            await ctx.send(
                f'''At {time.isoformat(timespec='minutes')} on {date.isoformat()}, {person.mention} said "{quote[0]}"'''
            )
        return

    rand_quote = random.choice(quotes)
    timestamp = rand_quote[1]
    time = timestamp.time()
    date = timestamp.date()
    await ctx.send(
        f'At {time.isoformat(timespec="minutes")} on {date.isoformat()}, {person.mention} said "{rand_quote[0]}"'
    )


@bot.command(name='qremove',
             help="removes a given message_id from the database")
async def remove_quote(ctx: commands.Context, message_id: int = None):
    if not message_id:
        await ctx.send('Please provide the id of a message you want to remove')
        return

    # try checking the channel that the command was used it
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
            await ctx.send('No message was found with that id')
            return

    # get quote
    db.execute('SELECT * FROM quotes WHERE quote=?', (quote.content,))
    deleted = list(db.fetchall())

    if not deleted:
        await ctx.send('No quote was found with that id')
        return

    db.execute('DELETE FROM quotes WHERE quote=?', (quote.content,))
    conn.commit()

    await ctx.send(
        f'Removed "{quote.content}" from {aliases[quote.author.name] if quote.author.name in aliases else quote.author.display_name}\'s quotes '
    )


@bot.command(name='qhelp', help='list of commands and brief description')
async def help(ctx: commands.Context):
    await ctx.send(
        '!getalias to get your current alias\n' +
        '!setalias [alias] to change your alias to the one provided\n' +
        '!qadd [message_id] (mention) to add that message as a quote, use mention to override the author '
        'to the user mentioned\n '
        +
        '!qget (user_mention) (keyword) (list) to get a random quote from the specified user (or yourself if user is '
        'not provided) matching keyword if provided. providing "list" will print out all of the matching quotes\n '
        + '!qgetall (user_mention) to get all the quotes from a user (defaults to user who sent command)\n' +
        '!qremove [message_id] to remove that message as a quote\n' +
        '!qhelp to show this message again')


@bot.command(name='qgetall', help='get all quotes by a user')
async def get_all(ctx: commands.Context, mention: User = None):

    author = mention if mention else ctx.author

    db.execute("SELECT quote, time FROM quotes WHERE user_id=?", (author.id,))
    quotes = db.fetchall()

    if not quotes:
        await ctx.send('No quotes found for this user, add some with `!qadd [message_id]`')
        return

    await ctx.send(f'Now listing all quotes for {author.mention}\n')
    for quote in quotes:
        datetime = quote[1]
        time = datetime.time()
        date = datetime.date()
        await ctx.send(
            f'At {time.isoformat(timespec="minutes")} on {date.strftime("%m/%d")}, '
            f'{aliases.get(author.name, default=author.display_name)} said "{quote[0]}" '
        )


bot.run(TOKEN)
