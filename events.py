import pandas as pd

# Find continous usage in the data, create events from these

def get_events(data: pd.DataFrame):
        
    # Initialize list for events
    events = list()

    # Find first day from dataframe
    first_day = pd.to_datetime(data.index[0]).date()

    # Iterate through each app of the dataframe
    for app in data.columns:

        onoff = data[app].astype(bool)

        # Check if the app gets turned on/off between following timestamps
        # If it does, save the time where it changes
        status_changes = onoff.where(onoff != onoff.shift()).dropna()
        #print(status_changes)

        # Create an iterable out of the timestamps
        timestamps = iter(status_changes.index.tolist())
        
        # Create an event for each change where the app was turned on
        for time in timestamps:
            if status_changes[time] != 0:
                start = time
                end = next(timestamps, time)
                
                event = {
                    'start': start,
                    'end': end,
                    'duration': (end - start).seconds / 60.0,
                    'app': app,
                    'day': (time.date() - first_day).days,
                    'profile': data[app].loc[start : end].iloc[:-1].tolist() # find better solution than end - 1
                }

                if len(event['profile']) < 96:
                    events.append(event)
    
    # Sort events in chronological order
    events = sorted(events, key=lambda x: x['start'])
    events = pd.DataFrame(events)
    
    write_events_to_csv(events)

    return events


def write_events_to_csv(events: pd.DataFrame):
    data_directory = 'data/derived/'
    events.to_csv(data_directory + 'events.csv')

