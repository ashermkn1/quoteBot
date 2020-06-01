from discord import *
import os
import sqlite3
import random

from discord.ext import commands

bot = commands.Bot(command_prefix='!')
TOKEN = os.getenv('DISCORD_TOKEN')
conn = sqlite3.connect('quotes.db')
db = conn.cursor()


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')
    await bot.change_presence(status=Status.online)


@bot.command(name='qadd', help="adds a specific message with given message id to a user's list of quotes")
async def add_quote(ctx: commands.Context, message_id: Message.id):
    quote = ctx.channel.get_message(message_id).content
    speaker = ctx.channel.get_message(message_id).author.id
    db.execute('INSERT into quotes (user_id, quote) VALUES (?, ?)', (speaker, quote))
    conn.commit()
    await ctx.send("Done!")


@bot.command(name='qget', help="gets a random message from given user that has been added using !qadd")
async def get_quote(ctx: commands.Context, person: User):
    db.execute("SELECT quote, datetime(time, 'localtime') FROM quotes WHERE user_id=?", person.id)
    quotes = db.fetchall()
    randQuote = random.choice(quotes)
    datetime = randQuote[1].split()
    await ctx.send(f'''At {datetime[1]} on {datetime[0]}, {person.mention} said 
        ```
        {randQuote[0]}
        ```
        ''')


bot.run(TOKEN)
