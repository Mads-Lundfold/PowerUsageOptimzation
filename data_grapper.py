import pandas as pd
import datetime
import os
import numpy as np
from pulp import LpProblem, LpVariable, LpBinary, LpMinimize
#import psutil

USAGE_THRESHOLD = 0.2

class DataManager():
    time_associations = {}
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


    # --------------------------------------------------------
    #               IMPORTING RAW DATA
    # --------------------------------------------------------
    def get_usage_data(self, start, end):
        data = pd.read_csv("./Data/house_1_2014_15min_watts.csv").query("Time >= @start and Time <= @end")
        data['Time'] = pd.to_datetime(data['Time'], unit='s')
        data.set_index('Time', inplace=True)

        # TODO : Implement real power thresholds.
        for app in data:
            data[app] = data[app].apply(lambda power: power if (power > self.power_thresholds.get(app, 5)) else 0) 

        #data = data.applymap(lambda x: x if (x >= 5) else 0)
        # threshold_df[column] = watt_dataframe[column].apply(lambda power: power if (power > threshold_dict.get(column, 5)) else 0)

        #print(data)
    
        self.get_time_associations(data)

        events = self.get_events(data)
        self.export_events_as_csv(events)
        #self.export_events_for_pattern_mining(events)
        #print(events)
        

        return data


    def get_price_data(self, start, end):
        data = pd.read_csv("./Data/Electricity_price_dataset_new.csv").drop(columns="cet_cest_timestamp").dropna()

        data['utc_timestamp'] = pd.to_datetime(data['utc_timestamp']).dt.tz_localize(None)

        data = data.rename(columns={'utc_timestamp' : 'Time'})

        print(data)

        data = data.query('Time.between(@start, @end)')
        return data

    # --------------------------------------------------------
    #               EXTRACTING EVENTS FROM DATA
    # --------------------------------------------------------
    # TODO: Fix get_events function to make clean and nice
    def get_events(self, data: pd.DataFrame):
        
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
        print(pd.DataFrame(events))
        return pd.DataFrame(events)
    
    def read_events_from_csv(self, filename):
        events = pd.read_csv(filename)
        events['start'] = pd.to_datetime(events['start'])
        events['end'] = pd.to_datetime(events['end'])

        return events

    def export_events_as_csv(self, events):
        events.to_csv("events.csv", index=False)

    def export_events_for_pattern_mining(self, events):
        events = events.drop(columns = ['duration', 'profile'])
        events['start'] = events['start'].map(pd.Timestamp.timestamp)
        events['start'] = events['start'].astype(int)
        events['end'] = events['end'].map(pd.Timestamp.timestamp)
        events['end'] = events['end'].astype(int)

        events.to_csv("mining_events.csv", index=False, header=False)
    
    # --------------------------------------------------------
    #               FINDING TIME ASSOCIATIONS
    # --------------------------------------------------------
    def get_time_associations(self, data):
        time_associations = {}

        data = data.astype(bool)

        usage = data.groupby(data.index.time).sum()

        for app in usage:
            high_usage = usage[app].where(usage[app].gt(usage[app].max() * USAGE_THRESHOLD)).dropna().index.tolist()

            time_associations[app] = (list(map(lambda x: x.hour*4 + (x.minute // 15), high_usage)))

        print(time_associations)
        self.time_associations = time_associations
        print(self.time_associations)

           
    # --------------------------------------------------------
    #               PATTERNS
    # --------------------------------------------------------
    def mine_temporal_patterns(self, support, confidence):
        command = f"py ./TPM/main.py -i mining_events.csv -o output -ms {support} -mc {confidence} -mps 2"
        print(command)
        os.system(command)


    # --------------------------------------------------------
    #               OPTIMIZATION
    # --------------------------------------------------------
    def optimize(self):
        prices = self.get_price_data(datetime.datetime(2015, 2, 1), datetime.datetime(2015, 2, 2))

        #print(prices)

        price_vector = np.array(np.repeat(prices['GB_GBN_price_day_ahead'], 4))
        print(price_vector)

        events = self.read_events_from_csv('events.csv').drop(columns=['end', 'day'])
        events = events[events['start'].between(datetime.datetime(2014, 2, 1), datetime.datetime(2014, 2, 2))]

        events['start'] = events['start'].apply(lambda x: x.hour*4 + (x.minute // 15))
        events['duration'] = events['duration'].apply(lambda x: x // 15)
        events['profile'] = events['profile'].apply(lambda x: [float(idx) for idx in x.strip("[]").split(', ')])

        print(events)
        #print(self.time_associations)

        potential_start_times = {}

        for event in events.itertuples():
            valid_start_times = list()
            for start_time in self.time_associations[event.app]:
                valid_sequence = True
                for i in range(start_time, start_time + int(event.duration)):
                    if i not in self.time_associations[event.app]:
                        valid_sequence = False
                        break

                if valid_sequence:
                    valid_start_times.append(start_time)

            potential_start_times[str(event.Index)] = valid_start_times
        
        print(potential_start_times)


        # LINEAR PRORGAMMING SHIT
        # Just try to make it work with the washing machine, event 317

        # Define the minimization problem
        problem = LpProblem("Appliance_Rescheduling", LpMinimize)

        # Define binary variables for each possible starting time
        x_variables = {value: LpVariable(f'x_{value}', cat=LpBinary) for value in potential_start_times['317']}

        # Constraint: Each event can only have one starting time
        problem += sum(x_variables[value] for value in potential_start_times['317']) == 1


        for value in potential_start_times['317']:
            print(value)
            print(x_variables[value])
            print(np.sum(events.loc[317, 'profile'] * price_vector[value : value + int(events.loc[317, 'duration'])]))

        # Objective: Find the lowest cost for the event
        objective_x = sum(x_variables[value] * np.sum(events.loc[317, 'profile'] * price_vector[value : value + int(events.loc[317, 'duration'])]) for value in potential_start_times['317'])

    
        #objective_x = sum(np.sum(events['profile'][317], price_vector[value * x_variables[value] : value*x_variables[value] + events['duration'][317]]) for value in potential_start_times['317'])
        problem += objective_x

        problem.solve()

        