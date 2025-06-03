def success_rate(channels_with_success: tuple):
    success_rate = list()
    for channel in channels_with_success:
        channel_id, channel_title, success_count, fail_count = channel
        rate = success_count / fail_count
        success_rate.append((channel_id, channel_title, rate))
    return success_rate

all = [
    (1, "Free Bitcoin", 3, 5),
    (2, "Free Dickoin", 4, 10),
]

print(success_rate(all))