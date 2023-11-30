import pandas as pd
import numpy as np
import datetime
import sys
import re

from events import get_events
from price_data import get_price_data
from data_loading import read_usage_data_csv, load_data
from time_associations import find_time_associations
from patterns import mine_temporal_patterns, find_patterns_on_day
from optimization import optimize

def main():
    start = 1388617200
    end = 1420066799

    usage = read_usage_data_csv()
    #print(usage)

    events = get_events(usage)
    #print(events)

    time_associations = find_time_associations(usage, threshold=0.1)
    #print(time_associations)

    mine_temporal_patterns(support=0.1, confidence=0.6)

    day_range = pd.date_range(start='01/05/2014', end='12/28/2014')

    for day in day_range:
        try:
            next_day = (day + datetime.timedelta(days=1))

            events_on_day = events[events['start'].between(day, next_day)]

            patterns_on_day = find_patterns_on_day('data/derived/patterns/Experiment_minsup0.1_minconf_0.6/level2.json', events_on_day)

            # Quantizing data
            # FORMAT PRICES
            day_price = day.replace(year = 2015)
            next_day_price = next_day.replace(year = 2015, hour = 23)
            
            prices = get_price_data(day_price, next_day_price)
            price_vector = np.array(np.repeat(prices['GB_GBN_price_day_ahead'], 4))
            
            # FORMAT EVENTS
            events_on_day['start'] = events_on_day['start'].apply(lambda x: x.hour*4 + (x.minute // 15))
            events_on_day['duration'] = events_on_day['duration'].apply(lambda x: x // 15)

            optimize(events=events_on_day, prices=price_vector, patterns=patterns_on_day, time_associations=time_associations)

        except Exception as e:
            pass


main()