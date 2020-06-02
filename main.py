from discord import *
import os
import sqlite3
import random
from datetime import datetime, timezone, timedelta

from discord.ext import commands

bot = commands.Bot(command_prefix='!')
TOKEN = os.getenv('DISCORD_TOKEN')
conn = sqlite3.connect('quotes.db', detect_types=sqlite3.PARSE_DECLTYPES |
                                           sqlite3.PARSE_COLNAMES)
db = conn.cursor()


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')
    await bot.change_presence(status=Status.online)


@bot.command(name='qadd', help="adds a specific message with given message id to a user's list of quotes")
async def add_quote(ctx: commands.Context, message_id: int):
    quote = await ctx.channel.fetch_message(message_id)
    # quote = quote.content
    db.execute('INSERT into quotes (user_id, quote, time) VALUES (?, ?, ?)', (quote.author.id, quote.content.strip('```'), datetime.now(tz=timezone(-timedelta(hours=4)))))
    conn.commit()
    await ctx.send("Done!")


@bot.command(name='qget', help="gets a random message from given user that has been added using !qadd")
async def get_quote(ctx: commands.Context, person: User):
    db.execute("SELECT quote, time FROM quotes WHERE user_id=?", (int(person.id),))
    quotes = db.fetchall()
    randQuote = random.choice(quotes)
    datetime = randQuote[1]
    time = datetime.time()
    date = datetime.date()
    await ctx.send(f'''At {time.isoformat(timespec='minutes')} on {date.isoformat()}, {person.mention} said 
        ```
        {randQuote[0]}
        ```
        ''')


bot.run(TOKEN)
