import pandas as pd


def find_time_associations(data: pd.DataFrame, threshold: float):

    time_associations = {}

    data = data.astype(bool)

    usage = data.groupby(data.index.time).sum()

    for app in usage:
        high_usage = usage[app].where(usage[app].gt(usage[app].max() * threshold)).dropna().index.tolist()

        time_associations[app] = (list(map(lambda x: x.hour*4 + (x.minute // 15), high_usage)))

    return time_associations