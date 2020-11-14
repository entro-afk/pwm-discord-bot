import discord
from discord.ext import commands
import datetime, pytz
import calendar
from scheduleConfig import ScheduleConfig
import yaml
import httplib2
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import pprint
import datefinder
import re
import redis
import collections
import math
import asyncio
import paramiko
import glob
import os
import numpy
from gyazo import Api
from google.cloud import vision
from sqlalchemy import *
from sqlalchemy.engine import reflection
from discord import File, Member, Role, PermissionOverwrite, ChannelType, Embed
import youtube_dl
import requests

from sshtunnel import SSHTunnelForwarder

scopes = ['https://www.googleapis.com/auth/calendar']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    'quickstart-1581556685975-8959801fbbb6.json', scopes)  # Your json file here

http = httplib2.Http()

http = credentials.authorize(http)
service = build('calendar', 'v3', http=http)
httpRequest = service.calendarList().list()
data = httpRequest.execute()
pprint.pprint(data)

service = build('calendar', 'v3', credentials=credentials)

fmt = "%Y-%m-%d %H:%M:%S %Z%z"

client = commands.Bot(command_prefix='!')
with open(r'conf.yaml') as file:
    # The FullLoader parameter handles the conversion from YAML
    # scalar values to Python the dictionary format
    channelsConf = yaml.load(file, Loader=yaml.FullLoader)

    print(channelsConf)

gyazo_client = Api(access_token=channelsConf['gyazo_token'])
r = redis.Redis(host=channelsConf['remote_server']['host'], port=6379)



song_queue = []
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}


# Search videos from key-words or links
def search(arg):
    try:
        requests.get("".join(arg))
    except:
        arg = " ".join(arg)
    else:
        arg = "".join(arg)
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(f"ytsearch:{arg}", download=False)['entries'][0]

    return {'source': info['formats'][0]['url'], 'title': info['title']}


# Plays the next song in the queue
def play_next(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if len(song_queue) > 1:
        del song_queue[0]
        voice.play(discord.FFmpegPCMAudio(song_queue[0]['source'], executable="ffmpeg.exe", before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn'), after=lambda e: play_next(ctx))
        voice.is_playing()

ytdl_format_options = {
    'format': 'bestaudio',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        data_url = data['url'] if "manifest" not in data['url'] and 'fragment_base_url' not in data['url'] else data['fragment_base_url']
        print('data url----------', data_url)
        filename = data_url if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


@client.command()
async def volume(ctx, volume: int):
    """Changes the player's volume"""

    if ctx.voice_client is None:
        return await ctx.send("Not connected to a voice channel.")

    ctx.voice_client.source.volume = volume / 100
    await ctx.send("Changed volume to {}%".format(volume))

@client.command('sendmsg')
async def send_message(ctx, *args):
    msg = ' '.join(args)
    await ctx.send(msg)

@client.command()
async def join(ctx, *, channel: discord.VoiceChannel):
    """Joins a voice channel"""

    if ctx.voice_client is not None:
        return await ctx.voice_client.move_to(channel)

    await channel.connect()

@client.command()
async def play(ctx, *arg):
    channel = ctx.message.author.voice.channel
    await play_on_channel("".join(arg), channel, ctx.guild, ctx.message.channel)

async def play_on_channel(link, voice_channel, guild, message):
    if voice_channel:
        voice = discord.utils.get(client.voice_clients, guild=guild)
        song = await YTDLSource.from_url(link, loop=client.loop,  stream=True)
        print('where is my song------------------', song)
        if not song_queue:
            song_queue.append(song)
        if voice and voice.is_connected():
            await voice.move_to(voice_channel)
        else:
            voice = await voice_channel.connect()
        print('do i even get to connect to my voice---------', voice)
        if not voice.is_playing():
            print('do i even get to before i play--------')
            guild.voice_client.play(song_queue[0], after=current_song_finished)
            voice.is_playing()
    else:
        await message.channel.send("You're not connected to any channel!")

async def stop_on_channel(voice_channel, guild, message_channel):
    if voice_channel:
        voice = discord.utils.get(client.voice_clients, guild=guild)
        if voice and voice.is_connected() and voice.is_playing():
            guild.voice_client.pause()
        else:
            await message_channel.send("Stopped.")
    else:
        await message_channel.send("You're not connected to any channel!")

async def rewind_on_channel(link, voice_channel, guild, message):
    if voice_channel:
        voice = discord.utils.get(client.voice_clients, guild=guild)
        song = await YTDLSource.from_url(link, loop=client.loop, stream=True)
        if voice and voice.is_connected():
            await voice.move_to(voice_channel)
        else:
            voice = await voice_channel.connect()

        if voice.is_playing():
            song_queue.append(song)
            guild.voice_client.stop()
            song_queue.pop(0)
            guild.voice_client.play(song_queue[0], after=current_song_finished)
            voice.is_playing()
        else:
            guild.voice_client.stop()
            if song_queue:
                song_queue.pop(0)
    else:
        await message.channel.send("You're not connected to any channel!")

def current_song_finished(e):
    print(e)
    if song_queue:
        song_queue.pop(0)

async def handle_player_emoji(message, emoji, author):
    if message.embeds[0].video:
        print('url------------', message.embeds[0])
        print(message.embeds[0].url)
        if emoji.name == '▶':
            await play_on_channel(message.embeds[0].url, author.voice.channel, message.guild, message)
            await message.remove_reaction('⏹', author)
            await message.remove_reaction('⏮', author)
        elif emoji.name == '⏹':
            await stop_on_channel(author.voice.channel, message.guild, message.channel)
            await message.remove_reaction('▶', author)
        elif emoji.name == '⏮':
            await rewind_on_channel(message.embeds[0].url, author.voice.channel, message.guild, message)
            await message.remove_reaction('⏮', author)


@client.event
async def on_ready():
    print('Bot is ready.')

@client.event
async def on_member_join(member):
  print(member)


@client.command()
async def events(ctx, day=""):
    now = datetime.datetime.now(tz=pytz.timezone('US/Eastern'))
    print("now time is: ", now)
    current_weekday = day if day else calendar.day_name[now.weekday()]
    message_events = []
    await get_message_events(message_events, current_weekday)
    if day:
        await ctx.send('Events for {}\n'.format(day) + '\n'.join(message_events))
    else:
        await ctx.send('Events today\n' + '\n'.join(message_events))


# @client.command()
# async def party(ctx):
#     r.lpush('screenshot', 1)
#     r.brpop('screenshotTaken')
#     list_of_files = glob.glob(r'/Users/popor/Pictures/BlueStacks/*') # * means all if need specific format then *.csv
#     latest_file = max(list_of_files, key=os.path.getctime)
#     print(latest_file)
#     ssh = paramiko.SSHClient()
#     ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     ssh.connect(channelsConf['remote_server']['host'], username='root', password=channelsConf['remote_server']['password'])
#     sftp = ssh.open_sftp()
#     print(os.path.basename(latest_file))
#     sftp.put(latest_file, os.path.join('/root', os.path.basename(latest_file)))
#     with sftp.open(os.path.join('/root', os.path.basename(latest_file)), 'rb') as f:
#         image = gyazo_client.upload_image(f)
#         print(image.to_json())
#         print(gyazo_client.get_oembed(image.permalink_url))
#         await ctx.send(image.permalink_url)
#     sftp.remove(os.path.join('/root', os.path.basename(latest_file)))
#     sftp.close()
#     ssh.close()

# r.set('foo', 'bar')
# print(r.get('foo'))

@client.command()
async def find_code_events_winners(ctx):
    async for message in ctx.guild.text_channels[5].history(limit=200):
        if message.author.id in channelsConf['hosters']:
            if "Winners:" in message.clean_content:
                for msg in message.clean_content.split("\n"):
                    if "Winners:" in msg:
                        await ctx.send(msg)

@client.command()
async def partystats(ctx, date=""):
    print(ctx)
    db_string = "postgres+psycopg2://postgres:{password}@{host}:5432/postgres".format(username='root', password='Iwd34mfb1wrm', host='localhost')
    print('string--------')
    print(db_string)
    db = create_engine(db_string, echo=True)
    # conn = db.connect()
    # inspector = inspect(conn)

    # for table_name in inspector.get_table_names():
    #     for column in inspector.get_columns(table_name):
    #         print("Column: %s" % column['name'])


    # insp = reflection.Inspector.from_engine(conn)
    # print(insp.get_table_names())
    metadata = MetaData(schema="pwm")
    # print(metadata)
    # table = Table('partyHistory', metadata, autoload=True, autoload_with=conn)
    # select_st = select([table])
    # res = conn.execute(select_st)
    # for _row in res:
    #     print('my row')
    #     print(_row)
    new_words = []
    orig_words = []
    guild = client.get_guild(ctx.guild.id)
    channel = discord.utils.get(guild.text_channels, name='party-history-logs')
    previous_day = 24
    hit_previous_day = False
    async for message in channel.history(limit=500):
        if hit_previous_day == True:
            continue
        if message.clean_content.startswith('https://gyazo.com/'):
            words = [w.split(",") if "," in w else w for w in detect_text_uri(message.clean_content+'.jpg')]
            output = []

            def flatten(l):
                for el in l:
                    if isinstance(el, collections.Iterable) and not isinstance(el, (str, bytes)):
                        yield from flatten(el)
                    else:
                        yield el

            output = list(flatten(words))
            for i, text in enumerate(output):
                if "Twe" in text:
                    print(text)
                if ("Recruit" in text and text != "Recruit") or "(Lv." in text or "级" in text or '(Nv.' in text or 'Nv.' in text or "/6" in text or "/12" in text or "/24" in text:
                    if "级" in text or text.startswith("(Lv.") or text.startswith("(Nv."):
                        text = output[i-1] + " " + text
                    new_words.append(text)
                    if "/6" in text or "/12" in text or "/24" in text:
                        if message.created_at.day == previous_day:
                            hit_previous_day = True
                        new_words.append(message.created_at)
                    # if "Recruit" in text:
                    #     with db.connect() as conn:
                    #         insert_statement = table.insert().values(eventName="Doctor Strange",director="Scott Derrickson", year="2016")
    print(new_words)
    print(orig_words)
    while new_words and isinstance(new_words[0], str) and "Recruit" not in new_words[0]:
        del new_words[0]
    while new_words and isinstance(new_words[-1], str):
        del new_words[-1]
    i = 0
    j = 0
    filled_new_words = []
    while(j < len(new_words)):
        text = new_words[j]
        if isinstance(text, str):
            if "Recruit" in text and i == 0:
                filled_new_words.append(text)
                j += 1
            elif ("(Lv." in text or "(Lv." in text or "级" in text or '(Nv.' in text or 'Nv.' in text) and i == 1:
                filled_new_words.append(text)
                j += 1
            elif ("/6" in text or "/12" in text or "/24" in text) and i == 2:
                filled_new_words.append(text)
                j += 1
            else:
                filled_new_words.append(None)
        elif isinstance(text, datetime.datetime) and i == 3:
            filled_new_words.append(text)
            j += 1
        else:
            filled_new_words.append(None)
        i += 1
        if i == 4:
            i = 0
    filled_new_words = list(chunks(filled_new_words, 4))
    print(new_words)
    for chunk in filled_new_words:
        with db.connect() as conn:
            table = Table('partyHistory', metadata, autoload=True, autoload_with=conn)
            if isinstance(chunk[0], str):
                party_leader = re.sub(r'\([^)]*\)', '', chunk[0])
                party_leader = re.sub(r'\[[^\]]*\]', '', party_leader)
                party_leader = re.sub("Recruit", '', party_leader)
                party_leader = re.sub("\\(", '', party_leader)
                party_leader = re.sub("\\[", '', party_leader)
                party_leader = re.sub("]", '', party_leader)
                party_leader = re.sub("\\)", '', party_leader)
                party_leader = party_leader.strip()
                if len(party_leader) == 1:
                    if "]" in party_leader[0]:
                        party_leader = chunk[0].split("]")[-1]
                    elif ")" in party_leader[0]:
                        party_leader = chunk[0].split(")")[-1]

                select_st = select([table]).where(
                    and_(
                        table.c.partyleader == party_leader,
                        table.c.eventname == chunk[1],
                        table.c.timeformed == chunk[3]
                    )
                )
                res = conn.execute(select_st)
                if res.first() is None:
                    party_size = chunk[2] and re.sub("[^0-9]", '', chunk[2].strip().split("/")[0]) or None
                    if chunk[1] and party_leader and chunk[3]:
                        insert_statement = table.insert().values(eventname=chunk[1], partyleader=party_leader, partysize=party_size, timeformed=chunk[3])
                        conn.execute(insert_statement)

# if "Recruit" in text:
            #     with db.connect() as conn:
            #         insert_statement = table.insert().values(eventName="Doctor Strange",director="Scott Derrickson", year="2016")

            # guild = client.get_guild(payload.guild_id)
    # channel = discord.utils.get(guild.text_channels, name=channelsConf['roles_channel']['name'])
    # msg = await channel.fetch_message(payload.message_id)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def get_message_events(message_events, current_weekday):
    for event_obj in ScheduleConfig.get_event_listing()[current_weekday]:
        if event_obj['length_type'] == 'all-day':
            message_events.append(
                '[{}-{}] {}'.format(event_obj['time_start'], event_obj['time_end'], event_obj['event_name']))
        elif event_obj['length_type'] == 'registration':
            message_events.append('[{}] {} Registration opens'.format(event_obj['time_start'], event_obj['event_name']))
        else:
            message_events.append('[{}] {}'.format(event_obj['time_start'], event_obj['event_name']))


# async def assign_role():
#
#     reaction = await client.wait_for_reaction(emoji="🏃", message=message)
#     await bot.add_roles(reaction.message.author, role)


@client.event
async def on_raw_reaction_add(payload):
    channel = client.get_channel(payload.channel_id)
    if payload.member.id != client.user.id and channel.name in ['song-request', 'test-zone']:
        video_msg = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        await handle_player_emoji(video_msg, payload.emoji, payload.member)
    if payload.channel_id == channelsConf['roles_channel']['id'] and payload.member.id != client.user.id or channel.name == 'fanclub-subscriptions':
        for post in channelsConf['roles_channel_messages']:
            if payload.message_id == post:
                await assign_role(payload, channelsConf['message_id_to_role_mapping'][post])
                break
        if channel.name == 'fanclub-subscriptions':
            roles_msg = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        else:
            roles_msg = await client.get_channel(channelsConf['roles_channel']['id']).fetch_message(payload.message_id)
        roles_rows = roles_msg.embeds[0].description.split("\n")
        found_pair = None
        for emoji_role_pair in roles_rows:
            if payload.emoji.name in emoji_role_pair:
                found_pair = emoji_role_pair
                break
        if found_pair:
            found_role = ' '.join(found_pair.strip().split(" ")[1:])
            if channel.name != 'fanclub-subscriptions':
                await assign_role(payload, found_role)
            else:
                list_id = None
                found_role = ' '.join(found_pair.strip().split(" ")[1:])
                if '[' in found_role:
                    found_role = found_role.split("[")[0].strip()
                list_name = f"{found_role} Fanclub"
                list_names = [listy['list_name'] for listy in get_lists(payload.guild_id)]
                if list_name not in list_names:
                    create_db_list(list_name, '', [], payload.guild_id)
                add_to_db_list(list_id, list_name, f"<@!{payload.member.id}>", [], payload.guild_id)



async def assign_role(payload, role_to_add):
    guild = client.get_guild(payload.guild_id)
    role = discord.utils.get(guild.roles, name=role_to_add)
    if not role:
        await guild.create_role(name=role_to_add)
        role = discord.utils.get(guild.roles, name=role_to_add)
    member = payload.member
    await member.add_roles(role, reason=role_to_add)



async def get_reacting_users(msg):
    user_ids = []
    for reaction in msg.reactions:
        async for user in reaction.users():
            user_ids.append(user.id)
    return user_ids


@client.event
async def on_raw_reaction_remove(payload):
    if payload.channel_id == channelsConf['roles_channel']['id'] and payload.user_id != client.user.id:

        for post in channelsConf['roles_channel_messages']:
            if payload.message_id == post:
                await unassign_role(payload, channelsConf['message_id_to_role_mapping'][post])
                break
        if payload.message_id in channelsConf['role_setup_msg_id']:
            roles_msg = await client.get_channel(channelsConf['roles_channel']['id']).fetch_message(payload.message_id)
            roles_rows = roles_msg.embeds[0].description.split("\n")
            found_pair = None
            for emoji_role_pair in roles_rows:
                if payload.emoji.name in emoji_role_pair:
                    found_pair = emoji_role_pair
                    break
            if found_pair:
                found_role = ' '.join(found_pair.strip().split(" ")[1:])
                member = await(await client.fetch_guild(payload.guild_id)).fetch_member(payload.user_id)
                await unassign_role_from_member(payload.guild_id, member, found_role)




async def unassign_role(payload, role_to_remove):
    guild = client.get_guild(payload.guild_id)
    channel = discord.utils.get(guild.text_channels, name=channelsConf['roles_channel']['name'])
    msg = await channel.fetch_message(payload.message_id)

    role = discord.utils.get(guild.roles, name=role_to_remove)
    member = await(await client.fetch_guild(payload.guild_id)).fetch_member(payload.user_id)
    user_ids = await get_reacting_users(msg)
    if payload.user_id not in user_ids:
        await member.remove_roles(role, reason=role_to_remove)


@client.command()
async def clean_mismatched_roles(ctx):
    for post in channelsConf['roles_channel_messages']:
        channel = discord.utils.get(ctx.guild.text_channels, name=channelsConf['roles_channel']['name'])
        msg = await channel.fetch_message(post)

        role = discord.utils.get(ctx.guild.roles, name=channelsConf['message_id_to_role_mapping'][post])
        user_ids = await get_reacting_users(msg)
        members_with_role = [member for member in ctx.guild.members if
                             role.name in [member_role.name for member_role in member.roles]]
        for member in members_with_role:
            if member.id not in user_ids:
                await member.remove_roles(role, reason=channelsConf['message_id_to_role_mapping'][post])
    pass

@client.command(pass_context=True, name='giverole')
async def assign_role_to_member(guild_id, member: Member, role_to_add):
    guild = client.get_guild(guild_id)
    role = discord.utils.get(guild.roles, name=role_to_add)
    if not role:
        await guild.create_role(name=role_to_add)
        role = discord.utils.get(guild.roles, name=role_to_add)
    member = guild.get_member(member.id)
    await member.add_roles(role, reason=role_to_add)

@client.command(pass_context=True, name='removerole')
async def unassign_role_from_member(guild_id, member: Member, role_to_remove):
    member_has_role_to_be_removed = discord.utils.get(member.roles, name=role_to_remove)
    if member_has_role_to_be_removed:
        guild = client.get_guild(guild_id)
        role = discord.utils.get(guild.roles, name=role_to_remove)
        member = await(await client.fetch_guild(guild_id)).fetch_member(member.id)
        await member.remove_roles(role, reason=role_to_remove)


@client.command(pass_context=True, name='giveallroleexcept')
async def give_everyone_this_role_except(ctx, role_name):
    roles_mentioned = ctx.message.role_mentions[1:] if role_name.startswith('<@') else ctx.message.role_mentions
    users_mentioned = ctx.message.mentions
    for role in roles_mentioned:
        for role_member in role.members:
            users_mentioned.append(role_member)
    for member in ctx.guild.members:
        marker_for_recent_people = datetime.datetime(2020, 1, 8)
        if member not in users_mentioned and member.joined_at > marker_for_recent_people:
            await assign_role_to_member(ctx.guild.id, member, role_name)
            print('Gave role to ', member.display_name)
        if member in users_mentioned:
            await unassign_role_from_member(ctx.guild.id, member, role_name)
            print('Tried to remove role from ', member.display_name)

async def add_music_reaction(message):
    if message.embeds and message.embeds[0].video:
        await message.add_reaction('▶')
        await message.add_reaction('⏹')
        await message.add_reaction('⏮')

@client.event
async def on_message(message):
    owo_filter_msg = message.clean_content.lower()
    if message.channel.type != discord.ChannelType.private and message.channel.name in channelsConf['event_making_channels'] and message.author.id in channelsConf['hosters']:
        event_name = find_name_of_event(message.clean_content)
        emoji_less_text = clean_text([r'<[a-z]*:\w*:\d*>'], message.clean_content)
        at_sign_modified_text = emoji_less_text.replace('@', 'at')
        try:
            create_event(at_sign_modified_text, event_name, duration=1, attendees=None, description=message.clean_content, location=None)
        except Exception as err:
            print(err)
    if message.channel.name in ['song-request', 'test-zone']:
        await add_music_reaction(message)
    if owo_filter_msg.startswith("owo") or message.author.name == "OwO":
        if owo_filter_msg != "" and owo_filter_msg.split(" ")[1] in ["insult", "kill", "lick", "punch"] or any(word in message.embeds[0].author.name for word in ["insult", "kill", "lick", "punch"]):
            await message.delete()
    else:
        await client.process_commands(message)
@client.event
async def on_event(event_name):
    print(f"{event_name} is dispatched")

def delete_list_by_id(list_id, guild_id):
    db_string = "postgres+psycopg2://postgres:{password}@{host}:{port}/postgres".format(username='root', password=channelsConf['postgres']['pwd'], host=channelsConf['postgres']['host'], port=channelsConf['postgres']['port'])
    db = create_engine(db_string)
    metadata = MetaData(schema="pwm")
    try:
        with db.connect() as conn:
            list_names_table = Table('listNames', metadata, autoload=True, autoload_with=conn)
            delete_query = f"DELETE FROM pwm.\"listNames\" WHERE id={list_id} AND guild_id={guild_id}"
            res = conn.execute(delete_query)
            delete_items_query = f"DELETE FROM pwm.\"listItems\" WHERE \"listID\"={list_id} AND guild_id={guild_id}"
            res2 = conn.execute(delete_items_query)
    except Exception as err:
        print(err)
        if conn:
            conn.close()
        db.dispose()

@client.command(pass_context=True, name="deleteitem")
async def delete_item(ctx, id):
    guild_id = ctx.guild.id
    result_rom_deletion = delete_item_by_id(id, guild_id)
    if result_rom_deletion:
        embed = Embed(title=f"Item #{id} Deleted:", color=0x00ff00)
        await ctx.message.channel.send(embed=embed)


def delete_item_by_id(item_id, guild_id):
    db_string = "postgres+psycopg2://postgres:{password}@{host}:{port}/postgres".format(username='root', password=channelsConf['postgres']['pwd'], host=channelsConf['postgres']['host'], port=channelsConf['postgres']['port'])
    db = create_engine(db_string)
    metadata = MetaData(schema="pwm")
    try:
        with db.connect() as conn:
            delete_answers_query = f"DELETE FROM pwm.\"listItems\" WHERE \"itemID\"={item_id} AND guild_id={guild_id}"
            res2 = conn.execute(delete_answers_query)
            return True
    except Exception as err:
        print(err)
        if conn:
            conn.close()
        db.dispose()

def clear_list_items(list_id, guild_id):
    db_string = "postgres+psycopg2://postgres:{password}@{host}:{port}/postgres".format(username='root', password=channelsConf['postgres']['pwd'], host=channelsConf['postgres']['host'], port=channelsConf['postgres']['port'])
    db = create_engine(db_string)
    metadata = MetaData(schema="pwm")
    try:
        with db.connect() as conn:
            delete_items_query = f"DELETE FROM pwm.\"listItems\" WHERE \"listID\"={list_id} AND guild_id={guild_id}"
            res2 = conn.execute(delete_items_query)
    except Exception as err:
        print(err)
        if conn:
            conn.close()
        db.dispose()

@client.command(pass_context=True, name="clearlist")
@commands.has_any_role('Event Hoster', 'Moderator')
async def clear_list(ctx, id):
    guild_id = ctx.guild.id
    list_name = get_list_name_by_id(id, guild_id)
    clear_list_items(id, guild_id)
    if not get_table_list_items(id, None, guild_id):
        embed = Embed(title=f"List #{id} Cleared:", description=list_name, color=0x00ff00)
        await ctx.message.channel.send(embed=embed)

@client.command(pass_context=True, name="listnames")
async def get_lists_table(ctx):
    list_rows = get_lists(ctx.guild.id)
    description_rows = []

    for row in list_rows:
        description_rows.append(f"#{row['list_id']}: {row['list_name']}")
    max_n = math.ceil(len(description_rows) / 20)
    embed_sets = []
    i = 0
    while i < max_n:
        begin_num = i*20
        embed = Embed(title=f"Existing Lists", description='\n'.join(description_rows[begin_num:begin_num+20]), color=0x00ff00)
        embed_sets.append(embed)
        i += 1
    for embed in embed_sets:
        await ctx.message.channel.send(embed=embed)


@client.command(pass_context=True, name="delete")
@commands.has_any_role('Event Hoster', 'Moderator', 'Jiselicious', 'Holy Trinity')
async def delete_list(ctx, id):
    guild_id = ctx.guild.id
    list_name = get_list_name_by_id(id, guild_id)
    delete_list_by_id(id, guild_id)
    if not get_list_name_by_id(id, guild_id):
        embed = Embed(title=f"List #{id} Deleted:", description=list_name, color=0x00ff00)
        await ctx.message.channel.send(embed=embed)


@client.command(pass_context=True, name="listcreate")
async def create_list(ctx, *args):
    list_name = ""
    items = []
    if "|" in args:
        list_name = ' '.join(args).split("|")[0]
        items = ' '.join(args).split("|")[1]
    else:
        list_name = ' '.join(args)
    list_name = list_name.strip()
    list_items = []
    table_id = create_db_list(list_name, items, list_items, ctx.guild.id)
    embed = Embed(title=f"List #{table_id} Created", description='\n'.join(list_items), color=0x00ff00)
    embed.add_field(name='List ID', value=f"{table_id}", inline=True)
    embed.add_field(name='List Name', value=f"{list_name}", inline=True)
    await ctx.message.channel.send(embed=embed)


def create_db_list(list_name, items, list_items, guild_id):
    try:
        db_string = "postgres+psycopg2://postgres:{password}@{host}:{port}/postgres".format(username='root', password=
        channelsConf['postgres']['pwd'], host=channelsConf['postgres']['host'], port=channelsConf['postgres']['port'])
        db = create_engine(db_string)
        metadata = MetaData(schema="pwm")

        with db.connect() as conn:
            list_names_table = Table('listNames', metadata, autoload=True, autoload_with=conn)
            insert_statement = list_names_table.insert().values(listName=list_name, guild_id=guild_id)
            res = conn.execute(insert_statement)
            table_id = res.inserted_primary_key[0]


            list_items_table = Table('listItems', metadata, autoload=True, autoload_with=conn)
            select_st = select([list_items_table])
            lowest_position_number = 0

            for item in items and items.split(","):
                insert_statement = list_items_table.insert().values(itemName=item.strip(), listID=table_id, position=lowest_position_number, guild_id=guild_id)
                conn.execute(insert_statement)
            select_st = select([list_items_table]).where(
                and_(
                    list_items_table.c.listID == table_id,
                    list_items_table.c.guild_id == guild_id
                )
            )
            res = conn.execute(select_st)
            for row in res:
                list_items.append("▫️" + row.itemName)
            return table_id
    except Exception as err:
        print(err)
        if conn:
            conn.close()
        db.dispose()

@client.command(pass_context=True, name="rolesetup")
async def post_roles(ctx, *args):
    title = ' '.join(args)
    if ctx.message.channel.name == 'fanclub-subscriptions':
        roles_channel = ctx.message.channel
    else:
        roles_channel = client.get_channel(channelsConf['roles_channel']['id'])
    try:
        embed = Embed(title=title, description="", color=0x00ff00)
        await roles_channel.send(embed=embed)
    except Exception as err:
        print(err)

@client.command(pass_context=True, name="color")
async def set_color(ctx, hex_str):
    if "#" in hex_str:
        hex_str = hex_str.replace("#", "")
    new_color_role = discord.utils.get(ctx.guild.roles, name=f"#{hex_str}")
    dj_role = discord.utils.get(ctx.guild.roles, name='DJ')
    if not new_color_role:
        new_color_role = await ctx.guild.create_role(name=f"#{hex_str}", color=discord.Color(value=int(hex_str, 16)))
        print([role.position for role in ctx.message.author.roles])
        print('position of DJ---------', dj_role.position)
        await asyncio.sleep(1.0)
        await new_color_role.edit(position=dj_role.position-1)
    print('position of DJ---------', new_color_role.position)
    current_color_role = [role for role in ctx.message.author.roles if role.name.startswith("#")]
    if current_color_role:
        await ctx.message.author.remove_roles(current_color_role[0])
    await ctx.message.author.add_roles(new_color_role)

def get_id_of_list(list_name):
    db_string = "postgres+psycopg2://postgres:{password}@{host}:{port}/postgres".format(username='root', password=channelsConf['postgres']['pwd'], host=channelsConf['postgres']['host'], port=channelsConf['postgres']['port'])
    db = create_engine(db_string)
    metadata = MetaData(schema="pwm")
    try:
        with db.connect() as conn:
            list_names_table = Table('listNames', metadata, autoload=True, autoload_with=conn)
            select_st = select([list_names_table]).where(list_names_table.c.listName == list_name)
            res = conn.execute(select_st)
            for row in res:
                list_name = row[1]
                list_id = row[0]
                break
            return list_id
    except Exception as err:
        print(err)
        if conn:
            conn.close()
        db.dispose()

@client.command(pass_context=True, name="newrole")
async def add_new_role(ctx, channel_id, message_id, *args):
    description_msg = []
    list_emoji_role_pairs = re.sub('\n', ",", ' '.join(args)).split(",")
    emoji_role_mapping = []
    channel = await client.fetch_channel(int(channel_id))
    for pair in list_emoji_role_pairs:
        emoji_role_pair = pair.strip().split(" ")
        emoji = emoji_role_pair[0].strip()
        role_name = ' '.join(emoji_role_pair[1:]).strip()
        role_description = ""
        if '|' in role_name:
            role_description = f" [{role_name.split('|')[1].strip()}]"
        role_name = role_name if '|' not in role_name else role_name.split("|")[0].strip()
        emoji_role_mapping.append((emoji, role_name))
        description_msg.append(f"{emoji} {role_name}{role_description}")
    if channel.name == 'fanclub-subscriptions':
        roles_msg = await channel.fetch_message(message_id)
    else:
        roles_msg = await client.get_channel(channelsConf['roles_channel']['id']).fetch_message(message_id)
    try:
        embed = Embed(title=roles_msg.embeds[0].title, description='\n'.join(description_msg), color=0x00ff00)
        await roles_msg.edit(embed=embed)
        for emoji_role_tuple in emoji_role_mapping:
            emoji = discord.utils.get(client.emojis, name=emoji_role_tuple[0])
            if not emoji:
                await roles_msg.add_reaction(emoji_role_tuple[0])
            else:
                await roles_msg.add_reaction(emoji)


    except Exception as err:
        print(err)

@client.command(pass_context=True, name="getlist")
async def get_list(ctx, *args):
    nice_list = False
    list_name = None
    list_id = None
    items = []
    potential_name_or_id = ' '.join(args).split("|")[0].strip()
    if "|" in args:
        nice_list = ' '.join(args).split("|")[1].strip().lower() == 'nice'
    if potential_name_or_id.strip().isnumeric():
        list_id = potential_name_or_id
    else:
        list_name = potential_name_or_id


    try:
        list_items = []
        table_list_items = get_table_list_items(list_id, list_name, ctx.guild.id)
        for item_name in table_list_items:
            list_items.append("▫️" + item_name['itemName'])
        if list_id:
            list_name = get_list_name_by_id(list_id, ctx.guild.id)
        else:
            list_id = get_id_of_list(list_name)

        i = 0
        embed_sets = []
        max_n = math.ceil(len(table_list_items) / 20)
        while i < max_n:
            begin_num = i * 20
            embed = Embed(title=f"{list_name}", description=f"ID#{list_id}" if i == 0 else "Continued", color=0x00ff00)
            item_ids = '\n'.join([str(item_row['id']) for item_row in table_list_items[begin_num:begin_num + 20]])
            item_texts = '\n'.join([item_row['itemName'] for item_row in table_list_items[begin_num:begin_num + 20]])
            embed.add_field(name='Item ID', value=f"{item_ids}", inline=True)
            embed.add_field(name='Item', value=f"{item_texts}", inline=True)
            embed_sets.append(embed)
            i += 1
        if not nice_list:
            for embed in embed_sets:
                await ctx.message.channel.send(embed=embed)

        if nice_list:
            embed = Embed(title=f"{list_name}", description=f"The list:\n" + '\n'.join(list_items), color=0x00ff00)
            await ctx.message.channel.send(embed=embed)

    except Exception as err:
        print(err)

def get_lists(guild_id):
    db_string = "postgres+psycopg2://postgres:{password}@{host}:{port}/postgres".format(username='root', password=channelsConf['postgres']['pwd'], host=channelsConf['postgres']['host'], port=channelsConf['postgres']['port'])
    db = create_engine(db_string)
    metadata = MetaData(schema="pwm")
    try:
        with db.connect() as conn:
            lists = []
            list_names_table = Table('listNames', metadata, autoload=True, autoload_with=conn)
            select_st = select([list_names_table]).where(list_names_table.c.guild_id == guild_id)
            res = conn.execute(select_st)
            for row in res:
                list_name = row[1]
                lists.append({
                    "list_id": row[0],
                    "list_name" : list_name,
                })
            return lists
    except Exception as err:
        print(err)
        if conn:
            conn.close()
        db.dispose()


@client.command(pass_context=True, name="sendping")
async def send_ping_from_list(ctx, *args):
    list_name = None
    list_id = None
    items = []
    list_name = ' '.join(args).split("|")[0]
    if list_name.strip().isnumeric():
        list_id = list_name
    if "fanclub" not in list_name.lower():
        list_name = list_name.strip() + " Fanclub"
    tags_in_list = get_table_list_items(list_id, list_name, ctx.guild.id)
    if list_id:
        list_name = get_list_name_by_id(list_id, ctx.guild.id)

    singer = client.get_user(int(re.sub("[^0-9]", "", list_name)))
    for tag in tags_in_list:
        tag_id = int(re.sub("[^0-9]", "", tag['itemName']))
        ping_receiver = client.get_user(tag_id)
        embed = Embed(title=f"{singer.name} is about to sing", description='Please join us at discord.gg/nQAAEx8',
                      color=0x00ff00)
        if tag_id != client.user.id:
            await ping_receiver.send(embed=embed)


def get_list_name_by_id(list_id, guild_id):
    db_string = "postgres+psycopg2://postgres:{password}@{host}:{port}/postgres".format(username='root', password=channelsConf['postgres']['pwd'], host=channelsConf['postgres']['host'], port=channelsConf['postgres']['port'])
    db = create_engine(db_string)
    metadata = MetaData(schema="pwm")
    try:
        with db.connect() as conn:
            list_names_table = Table('listNames', metadata, autoload=True, autoload_with=conn)
            select_st = select([list_names_table]).where(
                and_(
                    list_names_table.c.id == list_id,
                    list_names_table.c.guild_id == guild_id
                )
            )
            res = conn.execute(select_st)
            for row in res:
                list_name = row[1]
            return list_name
    except Exception as err:
        print(err)
        if conn:
            conn.close()
        db.dispose()


def get_table_list_items(list_id, list_name, guild_id):
    db_string = "postgres+psycopg2://postgres:{password}@{host}:{port}/postgres".format(username='root', password=channelsConf['postgres']['pwd'], host=channelsConf['postgres']['host'], port=channelsConf['postgres']['port'])
    db = create_engine(db_string)
    metadata = MetaData(schema="pwm")
    try:
        with db.connect() as conn:
            list_names_table = Table('listNames', metadata, autoload=True, autoload_with=conn)
            if list_id:
                condition = list_names_table.c.id == list_id
            else:
                condition = list_names_table.c.listName == list_name
            select_st = select([list_names_table]).where(
                and_(
                    condition,
                    list_names_table.c.guild_id == guild_id
                )
            )
            res = conn.execute(select_st)
            for row in res:
                list_name = row[1]
                list_id = row[0]
            list_items_table = Table('listItems', metadata, autoload=True, autoload_with=conn)
            select_st = select([list_items_table]).where(
                and_(
                    list_items_table.c.listID == list_id,
                    list_items_table.c.guild_id == guild_id
                )
            )
            res = conn.execute(select_st)
            table_list_items = []
            for row in res:
                table_list_items.append({
                    'id': row.itemID,
                    'itemName': row.itemName
                })

            return table_list_items
    except Exception as err:
        print(err)
        if conn:
            conn.close()
        db.dispose()


async def emoji_success_feedback(message):
    emoji = discord.utils.get(client.emojis, name='yes')
    await message.add_reaction(emoji)

@client.command(pass_context=True, name="affirm")
async def create_affirmation(ctx):
    from_name = ""
    stripped_content = ctx.message.content.lstrip('!affirm ')
    title = stripped_content
    message = ""
    affirm_channel = discord.utils.get(ctx.guild.text_channels, name='affirmations-and-salutes')
    if "|" in stripped_content:
        title = stripped_content.split("|")[0].strip()
        message = stripped_content.split("|")[1].strip()

    if len(stripped_content.split("|")) > 2:
        from_name = stripped_content.split("|")[2].strip()

    embed = Embed(title=title, description=message, color=0x9bcaee)
    if from_name:
        embed.set_footer(text=f"— {from_name}")
    if ctx.message.attachments:
        embed.set_image(url=ctx.message.attachments[0].url)

    await affirm_channel.send(embed=embed)

@client.command(pass_context=True, name="sendletter")
async def mail_affirmation(ctx):
    if ctx.message.channel.type == discord.ChannelType.private:
        message = ctx.message.clean_content.lstrip('!sendletter ')
        author = 'anon'
        guild = client.get_guild(channelsConf['guild_id'])
        print('guild id------------', guild.id)
        channel = discord.utils.get(guild.text_channels, id=751344514517434450)
        await asyncio.sleep(1.0)
        if message.lower().startswith('signed'):
            author = ctx.author.name + f' ({ctx.author.id})'
            message = message.lstrip('signed')
        embed = Embed(title=f"From {author}", description=message, color=0xb83fe4)
        await channel.send(embed=embed)
        await emoji_success_feedback(ctx.message)
        for atchment in ctx.message.attachments:
            embed.set_image(url=atchment.url)
            await channel.send(embed=embed)
            await emoji_success_feedback(ctx.message)

@client.command(pass_context=True, name="add")
async def add_to_list(ctx, *args):
    list_id = None
    list_name = ""

    items = []
    list_name = ' '.join(args).split("|")[0]
    items = ' '.join(args).split("|")[1]

    try:
        if list_name.strip().isnumeric():
            list_id = int(list_name.strip())
        list_items = []
        _list = add_to_db_list(list_id, list_name.strip(), items, list_items, ctx.guild.id)
        embed_sets = []
        i = 0
        max_n = math.ceil(len(list_items) / 20)
        while i < max_n:
            begin_num = i * 20
            embed = Embed(title=f"Added to List ID#{list_id}" if i == 0 else "Continued", description=_list['listName'], color=0x00ff00)
            list_items_ids = '\n'.join([str(item_row['id']) for item_row in list_items[begin_num:begin_num + 20]])
            list_items_texts = '\n'.join([item_row['itemName'] for item_row in list_items[begin_num:begin_num + 20]])
            embed.add_field(name='Item ID', value=f"{list_items_ids}")
            embed.add_field(name='Item', value=f"{list_items_texts}")
            embed_sets.append(embed)
            i += 1

        for embed in embed_sets:
            await ctx.message.channel.send(embed=embed)

    except Exception as err:
        print(err)

def add_to_db_list(list_id, list_name, items, list_items, guild_id):
    db_string = "postgres+psycopg2://postgres:{password}@{host}:{port}/postgres".format(username='root', password=channelsConf['postgres']['pwd'], host=channelsConf['postgres']['host'], port=channelsConf['postgres']['port'])
    db = create_engine(db_string)
    metadata = MetaData(schema="pwm")

    try:
        with db.connect() as conn:
            list_names_table = Table('listNames', metadata, autoload=True, autoload_with=conn)
            if list_id:
                condition = list_names_table.c.id == list_id
            else:
                condition = list_names_table.c.listName == list_name
            select_st = select([list_names_table]).where(
                and_(
                    condition,
                    list_names_table.c.guild_id == guild_id
                )
            )
            res = conn.execute(select_st)
            _list = [{column: value for column, value in rowproxy.items()} for rowproxy in res][0]


            list_items_table = Table('listItems', metadata, autoload=True, autoload_with=conn)
            select_st = select([list_items_table]).order_by(list_items_table.c.position.asc())
            lowest_position_number = 0
            for item in items.split(","):
                insert_statement = list_items_table.insert().values(itemName=item.strip(), listID=_list['id'], position= lowest_position_number, guild_id=guild_id)
                conn.execute(insert_statement)
            select_st = select([list_items_table]).where(
                and_(
                    list_items_table.c.listID == _list['id'],
                    list_names_table.c.guild_id == guild_id
                )
            )
            res = conn.execute(select_st)
            for row in res:
                list_items.append({
                    'id': row.itemID,
                    'itemName': row.itemName
                })
            return _list

    except Exception as err:
        print(err)
        if conn:
            conn.close()
        db.dispose()




def clean_text(rgx_list, text):
    new_text = text
    for rgx_match in rgx_list:
        new_text = re.sub(rgx_match, '', new_text)
    return new_text

def find_name_of_event(content):
    content_lines = content.split("\n")
    i = 0
    while content_lines[i].startswith('@') or content_lines[i] == "":
        i += 1
    return content_lines[i]


def create_event(start_time_str, summary, duration=1, attendees=None, description=None, location=None):
    matches = list(datefinder.find_dates(start_time_str))
    if len(matches):
        start_time = matches[0]
        end_time = start_time + datetime.timedelta(hours=duration)

    event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'America/New_York',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    pprint.pprint('''*** %r event added:
    With: %s
    Start: %s
    End:   %s''' % (summary.encode('utf-8'),
                    attendees, start_time, end_time))

    return service.events().insert(calendarId='mjlpifi9n5pllj790v99rlq61k@group.calendar.google.com',
                                   body=event).execute()



def detect_text_uri(uri):
    """Detects text in the file."""
    # client = vision.ImageAnnotatorClient()
    client = vision.ImageAnnotatorClient.from_service_account_json(r'/Users/popor/PycharmProjects/testDiscordBot.py/pwm-discord-bot/quickstart-1581556685975-8959801fbbb6.json')


    image = vision.types.Image()
    image.source.image_uri = uri
    response = client.text_detection(image=image)
    texts = response.text_annotations

    return texts and texts[0].description.split("\n") or []
    # for text in texts:
    #     return ('"{}"'.format(text.description))

        # vertices = (['({},{})'.format(vertex.x, vertex.y)
        #             for vertex in text.bounding_poly.vertices])
        #
        # print('bounds: {}'.format(','.join(vertices)))

    # if response.error.message:
    #     raise Exception(
    #         '{}\nFor more info on error messages, check: '
    #         'https://cloud.google.com/apis/design/errors'.format(
    #             response.error.message))




# test token
# client.run(channelsConf['test_bot_token'])

# pwm token
client.run(channelsConf['bot_token'])

# pm2 reload eventBot.py --interpreter=python3
