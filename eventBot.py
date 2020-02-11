import discord
from discord.ext import commands
import datetime, pytz
import calendar
from scheduleConfig import ScheduleConfig
import yaml

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


# test token
# client.run(channelsConf['test_bot_token'])

# pwm token
client.run(channelsConf['bot_token'])

# pm2 reload eventBot.py --interpreter=python3
