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


@client.event
async def on_ready():
    print('Bot is ready.')


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


@client.command()
async def find_code_events_winners(ctx):
    async for message in ctx.guild.text_channels[5].history(limit=200):
        if message.author.id in channelsConf['hosters']:
            if "Winners:" in message.clean_content:
                for msg in message.clean_content.split("\n"):
                    if "Winners:" in msg:
                        await ctx.send(msg)


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
    if payload.channel_id == channelsConf['roles_channel']['id'] \
            and payload.message_id in channelsConf['roles_channel_messages'] \
            + channelsConf['code_events_reaction_message_ids']:
        for post in channelsConf['roles_channel_messages']:
            if payload.message_id == post:
                await assign_role(payload, channelsConf['message_id_to_role_mapping'][post])
                break


async def assign_role(payload, role_to_add):
    guild = client.get_guild(payload.guild_id)
    role = discord.utils.get(guild.roles, name=role_to_add)
    member = guild.get_member(payload.user_id)
    await member.add_roles(role, reason=role_to_add)


async def get_reacting_users(msg):
    user_ids = []
    for reaction in msg.reactions:
        async for user in reaction.users():
            user_ids.append(user.id)
    return user_ids


@client.event
async def on_raw_reaction_remove(payload):
    if payload.channel_id == channelsConf['roles_channel']['id']:
        for post in channelsConf['roles_channel_messages']:
            if payload.message_id == post:
                await unassign_role(payload, channelsConf['message_id_to_role_mapping'][post])
                break


async def unassign_role(payload, role_to_remove):
    guild = client.get_guild(payload.guild_id)
    channel = discord.utils.get(guild.text_channels, name=channelsConf['roles_channel']['name'])
    msg = await channel.fetch_message(payload.message_id)

    role = discord.utils.get(guild.roles, name=role_to_remove)
    member = guild.get_member(payload.user_id)
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

@client.event
async def on_message(message):
    if message.channel.name in channelsConf['event_making_channels'] and message.author.id in channelsConf['hosters']:
        event_name = find_name_of_event(message.clean_content)
        emoji_less_text = clean_text([r'<[a-z]*:\w*:\d*>'], message.clean_content)
        at_sign_modified_text = emoji_less_text.replace('@', 'at')
        try:
            create_event(at_sign_modified_text, event_name, duration=1, attendees=None, description=message.clean_content, location=None)
        except Exception as err:
            print(err)
    await client.process_commands(message)


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



# test token
# client.run(channelsConf['test_bot_token'])

# pwm token
client.run(channelsConf['bot_token'])

# pm2 reload eventBot.py --interpreter=python3
