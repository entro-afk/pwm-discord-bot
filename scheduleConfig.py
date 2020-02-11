class ScheduleConfig:
    def __init__(self):
        pass

    @staticmethod
    def get_event_listing():
        return {
            'Monday': [
                {
                    'event_name': 'Bounty Hunter',
                    'length_type': 'all-day',
                    'time_start': '10:30',
                    'time_end': '23:00'
                },
                {
                    'event_name': 'Exorcists Trial',
                    'length_type': 'all-day',
                    'time_start': '12:00',
                    'time_end': '23:40'
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '12:00',
                },
                {
                    'event_name': 'Path of Five',
                    'length_type': 'all-day',
                    'time_start': '10:30',
                    'time_end': '23:00'
                },
                {
                    'event_name': 'Celestial Hunt',
                    'length_type': 'limited',
                    'time_start': '19:30',
                },
                {
                    'event_name': 'Arena',
                    'length_type': 'registration',
                    'time_start': '20:00',
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '21:00',
                },
            ],
            'Tuesday': [
                {
                    'event_name': 'Exorcists Trial',
                    'length_type': 'all-day',
                    'time_start': '12:00',
                    'time_end': '23:40'
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '12:00',
                },
                {
                    'event_name': 'Bandit Battle',
                    'length_type': 'all-day',
                    'is_guild_event': True,
                    'time_start': '13:00',
                    'time_end': '19:15'
                },
                {
                    'event_name': 'Cultivator Clan Elder',
                    'length_type': 'limited',
                    'is_guild_event': True,
                    'time_start': '19:30',
                },
                {
                    'event_name': 'Path of Asura',
                    'length_type': 'registration',
                    'time_start': '20:00',
                },
            ],
            'Wednesday': [
                {
                    'event_name': 'Exorcists Trial',
                    'length_type': 'all-day',
                    'time_start': '12:00',
                    'time_end': '23:40'
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '12:00',
                },
                {
                    'event_name': 'Path of Five',
                    'length_type': 'all-day',
                    'time_start': '10:30',
                    'time_end': '23:00'
                },
                {
                    'event_name': 'Guild Beast',
                    'length_type': 'limited',
                    'is_guild_event': True,
                    'time_start': '19:30',
                },
                {
                    'event_name': 'Guild League',
                    'length_type': 'registration',
                    'is_guild_event': True,
                    'time_start': '20:00',
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '21:00',
                },
            ],
            'Thursday': [
                {
                    'event_name': 'Exorcists Trial',
                    'length_type': 'all-day',
                    'time_start': '12:00',
                    'time_end': '23:40'
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '12:00',
                },
                {
                    'event_name': 'Bandit Battle',
                    'length_type': 'all-day',
                    'is_guild_event': True,
                    'time_start': '13:00',
                    'time_end': '19:15'
                },
                {
                    'event_name': 'Cultivator Clan Elder',
                    'length_type': 'limited',
                    'is_guild_event': True,
                    'time_start': '19:30',
                },
                {
                    'event_name': 'Guild League',
                    'length_type': 'registration',
                    'is_guild_event': True,
                    'time_start': '20:00',
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '21:00',
                },
            ],
            'Friday': [
                {
                    'event_name': 'Bounty Hunter',
                    'length_type': 'all-day',
                    'time_start': '10:30',
                    'time_end': '23:00'
                },
                {
                    'event_name': 'Exorcists Trial',
                    'length_type': 'all-day',
                    'time_start': '12:00',
                    'time_end': '23:40'
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '12:00',
                },
                {
                    'event_name': 'Path of Five',
                    'length_type': 'all-day',
                    'time_start': '10:30',
                    'time_end': '23:00'
                },
                {
                    'event_name': 'Celestial Hunt',
                    'length_type': 'limited',
                    'time_start': '19:30',
                },
                {
                    'event_name': 'Demonic Beast Invasion',
                    'length_type': 'limited',
                    'time_start': '20:00',
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '21:00',
                },
            ],
            'Saturday': [
                {
                    'event_name': 'Exorcists Trial',
                    'length_type': 'all-day',
                    'time_start': '12:00',
                    'time_end': '23:40'
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '12:00',
                },
                {
                    'event_name': 'Path of Five',
                    'length_type': 'all-day',
                    'time_start': '10:30',
                    'time_end': '23:00'
                },
                {
                    'event_name': 'Guild Beast',
                    'length_type': 'limited',
                    'is_guild_event': True,
                    'time_start': '19:30',
                },
                {
                    'event_name': 'Territory War',
                    'length_type': 'limited',
                    'is_guild_event': True,
                    'time_start': '20:00',
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '21:00',
                },
            ],
            'Sunday': [
                {
                    'event_name': 'Exorcists Trial',
                    'length_type': 'all-day',
                    'time_start': '12:00',
                    'time_end': '23:40'
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '12:00',
                },
                {
                    'event_name': 'Safari Bear',
                    'length_type': 'limited',
                    'is_guild_event': True,
                    'time_start': '19:30',
                },
                {
                    'event_name': 'Divine Valley',
                    'length_type': 'registration',
                    'time_start': '21:00',
                },
                {
                    'event_name': 'Frozen Frontier',
                    'length_type': 'limited',
                    'is_guild_event': True,
                    'time_start': '21:00 or chosen by guild leader',
                },
                {
                    'event_name': 'Realm War',
                    'length_type': 'limited',
                    'time_start': '20:00',
                },
            ]
        }
