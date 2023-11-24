import pandas as pd

power_thresholds = {
        'washing_machine' : 20,
        'dishwasher' : 10,
        'tv' : 10,
        'htpc' : 20,
        'kettle' : 2000,
        'toaster' : 1000,
        'fridge' : 50,
        'microwave' : 200,
        'kitchen_radio' : 2,
        'bedroom_chargers' : 1,
        'gas_oven' : 10
    }

def get_events_from_data(start, end):
    data = pd.read_csv("./data/raw/house_1_2014_15min_watts.csv").query("Time >= @start and Time <= @end")
    data['Time'] = pd.to_datetime(data['Time'], unit='s')
    data.set_index('Time', inplace=True)

    # TODO : Implement real power thresholds.
    for app in data:
        data[app] = data[app].apply(lambda power: power if (power > power_thresholds.get(app, 5)) else 0) 

    events = get_events(data)
    return events


def get_events(data: pd.DataFrame):
        
    # Initialize list for events
    events = list()

    # Find first day from dataframe
    first_day = data.index[0].date()

    # Find the last timestamp in the dataframe
    last_day = data.index[-1].date()

    # Iterate through each app of the dataframe
    for app in data.columns:

        onoff = data[app].astype(bool)

        # Check if the app gets turned on/off between following timestamps
        # If it does, save the time where it changes
        status_changes = onoff.where(onoff != onoff.shift()).dropna()
        #print(status_changes)

        # Create an iterable out of the timestamps
        timestamps = iter(status_changes.index.tolist())
        #print(timestamps)
        
        # Create an event for each change where the app was turned on
        for time in timestamps:
            if status_changes[time] != 0:
                start = time
                end = next(timestamps, time)
                events.append({
                    'start': start,
                    'end': end,
                    'duration': (end - start).seconds / 60.0,
                    'app': app,
                    'day': (time.date() - first_day).days,
                    'profile': data[app].loc[start : end].iloc[:-1].tolist() # find better solution than end - 1
                })
    
    # Sort events in chronological order
    events = sorted(events, key=lambda x: x['start'])
    #print(pd.DataFrame(events))
    return pd.DataFrame(events)