import pandas as pd
import os
import re

data_directory = 'data/derived/'

def format_events_for_pattern_mining():
    events = pd.read_csv(data_directory + 'events.csv')
    events = events.drop(columns=['Unnamed: 0', 'duration', 'profile'])

    events['start'] = pd.to_datetime(events['start']).map(pd.Timestamp.timestamp)
    events['start'] = events['start'].astype(int)
    events['end'] = pd.to_datetime(events['end']).map(pd.Timestamp.timestamp)
    events['end'] = events['end'].astype(int)

    events.to_csv(data_directory + 'mining_events.csv', index=False, header=False)


def mine_temporal_patterns(support, confidence):
    format_events_for_pattern_mining()
    command = f"py ./TPM/main.py -i data/derived/mining_events.csv -o data/derived/patterns -ms {support} -mc {confidence} -mps 2"
    print(command)
    os.system(command)


# This function is a mess, but I will have to change how pattern mining works to change that.
def find_patterns_on_day(file_path, events):
    extracted_data = pd.read_json(file_path)

    patterns = list()

    for data in extracted_data['patterns']:
        for pattern in data:
            for key in pattern['time']:
                if key == str(events['day'].iloc[0]):
                    pattern_type = re.split('(>|->|\|)', pattern['pattern'])
                    #print(pattern_type)

                    first_time = pd.to_datetime(pattern['time'][key][0][0][0])

                    second_time = pd.to_datetime(pattern['time'][key][0][1][0])

                    first_event = events.query('start == @first_time and app == @pattern_type[0]').index.item()
                    second_event = events.query('start == @second_time and app == @pattern_type[2]').index.item()
                    patterns.append({'type': pattern_type[1], 
                                        'first': first_event,
                                        'second': second_event})
                    
    #print(patterns)

    return patterns