from discord import *
import os
import sqlite3
import random
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from discord.ext import commands
load_dotenv('.env')
bot = commands.Bot(command_prefix='!')
TOKEN = os.getenv('DISCORD_TOKEN')
print(TOKEN)
conn = sqlite3.connect('quotes.db', detect_types=sqlite3.PARSE_DECLTYPES |
                                           sqlite3.PARSE_COLNAMES)
db = conn.cursor()

aliases = {
  'robotgirl2k4' : "fucking idiot",
  'Sandy' : "Sandy",
  'MagicMosasaur' : "Charlie",
  "JuliaTheSciNerd" : "Julia",
  "Nicole" : "Nicole",
  "avm" : "AlexaV",
  "Mathtician" : "Aresh",
  "GhostDragon" : "fucking idiot #2"
  }
  
@bot.command(name='changealias', help='change your alias to a specified nickname')
async def change_alias(ctx: commands.Context, nickname: str):
  if not nickname:
    await ctx.send('Please provide a nickname you want')
    return
  old = aliases[ctx.message.author.name]
  aliases[ctx.message.author.name] = nickname
  await ctx.send(f'Changed your alias from "{old}" to "{aliases[ctx.message.author.name]}"')


@bot.command(name='getalias', help='get your current alias')
async def get_alias(ctx: commands.Context):
  await ctx.send(f'Your current alias is "{aliases[ctx.message.author.name]}"')
  
  
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')
    activity = Game(name='!qhelp')
    await bot.change_presence(status=Status.online, activity=activity)


@bot.command(name='qadd', help="adds a specific message with given message id to a user's list of quotes")
async def add_quote(ctx: commands.Context, message_id: int=None, mention: User=None):
    if not message_id:
      await ctx.send('Please provide an id of the message you want to quote')
      return
    quote = await ctx.channel.fetch_message(message_id)
    time = quote.created_at.replace(tzinfo=timezone(-timedelta(hours=4)))
    if mention:
      db.execute('INSERT into quotes (user_id, quote, time) VALUES (?, ?, ?)', 
      (mention.id, quote.content.strip('```'), time))
    else:
      db.execute('INSERT into quotes (user_id, quote, time) VALUES (?, ?, ?)', 
        (quote.author.id, quote.content.strip('```'), time))
    conn.commit()
    author = mention.name if mention else quote.author.name
    await ctx.send(f'Added "{quote.content}" to {aliases[author] if author in aliases else quote.author.display_name}\'s quotes!')


@bot.command(name='qget', help="gets a random message from given user that has been added using !qadd")
async def get_quote(ctx: commands.Context, person: User=None, keyword: str=None, all: str=None):
    if not person:
       await ctx.send('Please mention a user to get a random quote from')
       return
       
    if keyword:
      db.execute("SELECT quote, time FROM quotes WHERE user_id=? AND quote LIKE ?", (int(person.id),
            '%' + keyword + '%'))
      
    else:
      db.execute("SELECT quote, time FROM quotes WHERE user_id=?", (int(person.id),))
    quotes = db.fetchall()
    if len(quotes) == 0:
      if keyword:
        await ctx.send('No quotes found for this user matching the pattern provided')
        return
      await ctx.send('No quotes found for this user, add some with `!qadd [message_id]`')
      return
    if all == 'list':
      for quote in quotes:
        datetime = quote[1]
        time = datetime.time()
        date = datetime.date()
        await ctx.send(f'''At {time.isoformat(timespec='minutes')} on {date.isoformat()}, {person.mention} said "{quote[0]}"''')
      return
    
    randQuote = random.choice(quotes)
    datetime = randQuote[1]
    time = datetime.time()
    date = datetime.date()
    await ctx.send(f'''At {time.isoformat(timespec='minutes')} on {date.isoformat()}, {person.mention} said "{randQuote[0]}"''')

@bot.command(name='qremove', help="removes a given message_id from the database")
async def remove_quote(ctx: commands.Context, message_id: int=None):
    if not message_id:
      await ctx.send('Please provide the id of a message you want to remove')
      return
    quote = await ctx.channel.fetch_message(message_id)
    deleted = db.execute('DELETE FROM quotes WHERE quote=?', (quote.content,))
    conn.commit()
    author = bot.get_user(deleted[0]['user_id'])
    await ctx.send(f'Removed "{quote.content}" from {aliases[quote.author.name] if quote.author.name in aliases else quote.author.display_name}\'s quotes')

@bot.command(name='qhelp', help='list of commands and brief description')
async def help(ctx: commands.Context):
    await ctx.send(
    '!getalias to get your current alias\n' + 
    '!changealias [alias] to change your alias to the one provided\n' +
    '!qadd [message_id] [mention (optional)] to add that message as a quote, use mention to override the author to the user mentioned\n' +
    '!qget [user_mention] [keyword] [list] to get a random quote from the specified user matching keyword if provided. providing "list" will print out all of the matching quotes\n' +
    '!qremove [message_id] to remove that message as a quote\n' +
    '!qhelp to show this message again'
    )
bot.run(TOKEN)

