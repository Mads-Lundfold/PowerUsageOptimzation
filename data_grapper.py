import pandas as pd
import datetime
import os
import numpy as np
from pulp import LpProblem, LpVariable, LpBinary, LpMinimize
import re

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

    cost_before = 0
    cost_after = 0


    # --------------------------------------------------------
    #               IMPORTING RAW DATA
    # --------------------------------------------------------
    def get_usage_data(self, start, end):
        data = pd.read_csv("./data/raw/house_1_2014_15min_watts.csv").query("Time >= @start and Time <= @end")
        data['Time'] = pd.to_datetime(data['Time'], unit='s')
        data.set_index('Time', inplace=True)

        # TODO : Implement real power thresholds.
        for app in data:
            data[app] = data[app].apply(lambda power: power if (power > self.power_thresholds.get(app, 5)) else 0) 

        #data = data.applymap(lambda x: x if (x >= 5) else 0)
        # threshold_df[column] = watt_dataframe[column].apply(lambda power: power if (power > threshold_dict.get(column, 5)) else 0)

        #print(data)
    
        self.get_time_associations(data)

        #events = self.get_events(data)
        #self.export_events_as_csv(events)
        #self.export_events_for_pattern_mining(events)
        #self.mine_temporal_patterns(support=0.1, confidence=0.6)
        #print(events)
        

        return data


    def get_price_data(self, start, end):
        data = pd.read_csv("./data/raw/Electricity_price_dataset_new.csv").drop(columns="cet_cest_timestamp").dropna()

        data['utc_timestamp'] = pd.to_datetime(data['utc_timestamp']).dt.tz_localize(None)

        data = data.rename(columns={'utc_timestamp' : 'Time'})

        #print(data)

        data = data.query('Time.between(@start, @end)')
        
        if len(data) < 25:
            data = data.set_index('Time').resample('H').asfreq().reset_index()
            data = data.fillna(method='ffill')
                    

        data["GB_GBN_price_day_ahead"] = data["GB_GBN_price_day_ahead"].astype(float) / 1000000

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
        #print(pd.DataFrame(events))
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

        #print(time_associations)
        self.time_associations = time_associations
        #print(self.time_associations)

           
    # --------------------------------------------------------
    #               PATTERNS
    # --------------------------------------------------------
    def mine_temporal_patterns(self, support, confidence):
        command = f"py ./TPM/main.py -i mining_events.csv -o output -ms {support} -mc {confidence} -mps 2"
        print(command)
        os.system(command)

    # This function is a mess, but I will have to change how pattern mining works to change that.
    def find_patterns_on_day(self, file_path, events):
        extracted_data = pd.read_json(file_path)

        patterns = list()

        for data in extracted_data['patterns']:
            for pattern in data:
                for key in pattern['time']:
                    if key == str(events['day'].iloc[0]):
                        pattern_type = re.split('(>|->|\|)', pattern['pattern'])
                        #print(pattern_type)

                        first_time = pd.to_datetime(pattern['time'][key][0][0][0]).time()
                        first_time = first_time.hour*4 + (first_time.minute // 15)

                        second_time = pd.to_datetime(pattern['time'][key][0][1][0]).time()
                        second_time = second_time.hour*4 + (second_time.minute // 15)
                        #print(first_time, second_time)

                        first_event = events.query('start == @first_time and app == @pattern_type[0]').index.item()
                        second_event = events.query('start == @second_time and app == @pattern_type[2]').index.item()
                        patterns.append({'type': pattern_type[1], 
                                         'first': first_event,
                                         'second': second_event})
                        
        #print(patterns)

        return patterns

    # --------------------------------------------------------
    #               OPTIMIZATION
    # --------------------------------------------------------
    # TODO Break this up, it's really hefty
    def optimize(self, day, next_day):
        day_price = day.replace(year = 2015)
        next_day_price = next_day.replace(year = 2015, hour = 23)
        #print(day_price, next_day_price)
        prices = self.get_price_data(day_price, next_day_price)

        #print(prices)

        price_vector = np.array(np.repeat(prices['GB_GBN_price_day_ahead'], 4))
        #print(price_vector)

        events = self.read_events_from_csv('events.csv').drop(columns=['end'])
        events = events[events['start'].between(day, next_day)]

        if len(events) == 0:
            return 0

        events['start'] = events['start'].apply(lambda x: x.hour*4 + (x.minute // 15))
        events['duration'] = events['duration'].apply(lambda x: x // 15)
        events['profile'] = events['profile'].apply(lambda x: [float(idx) for idx in x.strip("[]").split(', ')])


        #print(events)

        patterns = self.find_patterns_on_day('output/Experiment_minsup0.1_minconf_0.6/level2.json', events)
        #print(self.time_associations)

        potential_start_times = {}

        for event in events.itertuples():
            potential_start_times[str(event.Index)] = self.find_potential_starting_times(event)    
        
        '''
        for key, val in potential_start_times.items():
            print(key, val)
        '''
        
        
        for e in events.itertuples():
            cost = np.sum(e.profile * price_vector[int(e.start) : int(e.start) + int(len(e.profile))])
            self.cost_before += cost
        
        
        

        # LINEAR PRORGAMMING SHIT

        # Define the minimization problem
        problem = LpProblem("Appliance_Rescheduling", LpMinimize)

        # Create binary variables for each appliance we need to schedule
        variables = {}
        for key in potential_start_times:           
            # Binary variable for each potential starting time of the event. 
            # If the event is started at the time slot, then the value is 1.
            variables[key] = {value: LpVariable(f'{key}_{value}', cat=LpBinary) for value in potential_start_times[key]}
            #print(variables[key])

            # Constraint: Each event can only have one starting time
            problem += sum(variables[key][value] for value in potential_start_times[key]) == 1

        # For every event, find the beginning time slot where the price times profile is the lowest
        objective = sum(sum(variables[key][value] * np.sum(events.loc[int(key), 'profile'] * price_vector[value : value + int(len(events.loc[int(key), 'profile']))]) for value in potential_start_times[key]) for key in potential_start_times)

        problem += objective
        
        
        # TODO: Constraint that two events of same appliance cannot overlap.
        # Change event index to a column
        same_type_events = events.drop(columns=['start', 'duration', 'day', 'profile']).reset_index()
        same_type_events = same_type_events.groupby('app')['index'].apply(list)
        # Only keep applications that have more than 2 events in the day
        same_type_events = same_type_events[(same_type_events.str.len()) >= 2]
        #print(same_type_events)

        for t in same_type_events:
            amount = len(t)
            for i in range(0, amount):
                for j in range(i + 1, amount):
                    problem += (sum(value * var for value, var in variables[str(t[i])].items()) + int(events.loc[int(t[i]), 'duration']) + 1 <= sum(value * var for value, var in variables[str(t[j])].items()) 
                                or sum(value * var for value, var in variables[str(t[i])].items()) >= sum(value * var for value, var in variables[str(t[j])].items()) + int(events.loc[int(t[j]), 'duration']) + 1)
        

        for p in patterns:
            if p['type'] == '>':
                problem += sum(value * var for value, var in variables[str(p['first'])].items()) <= sum(value * var for value, var in variables[str(p['second'])].items())
                problem += sum(value * var for value, var in variables[str(p['first'])].items()) + int(events.loc[int(p['first']), 'duration']) >= sum(value * var for value, var in variables[str(p['second'])].items()) + int(events.loc[int(p['second']), 'duration'])
            elif p['type'] == '->':
                problem += sum(value * var for value, var in variables[str(p['first'])].items()) + int(events.loc[int(p['first']), 'duration']) <= sum(value * var for value, var in variables[str(p['second'])].items())
            elif p['type'] == '|':
                # e1 must end before e2 ends
                problem += sum(value * var for value, var in variables[str(p['first'])].items()) + int(events.loc[int(p['first']), 'duration']) <= sum(value * var for value, var in variables[str(p['second'])].items()) + int(events.loc[int(p['second']), 'duration'])
                # e1 must end after e2 begins
                problem += sum(value * var for value, var in variables[str(p['first'])].items()) + int(events.loc[int(p['first']), 'duration']) >= sum(value * var for value, var in variables[str(p['second'])].items())

        problem.solve()

        #print(problem.objective.value())
        self.cost_after += problem.objective.value()

        
        # Print the starting times for each event after solving the problem
        '''
        for v in problem.variables():
            if v.varValue == 1:
                print(v.name, "=", v.varValue)
        '''
        

    def find_potential_starting_times(self, event):
        highest_satis = 0
        valid_start_times = list()

        for start_time in self.time_associations[event.app]:
            if start_time + event.duration > 95: break

            event_range = list(range(start_time, start_time + int(event.duration)))
            satis = len(set(event_range) & set(self.time_associations[event.app]))
            
            if satis > highest_satis:
                highest_satis = satis
                valid_start_times.clear()
                valid_start_times.append(start_time) 
            elif satis == highest_satis:
                valid_start_times.append(start_time)
     
        if (self.time_associations[event.app][0] + event.duration > 95):
            valid_start_times.clear()
            valid_start_times.append(int(95 - event.duration))

        return valid_start_times 



    def check_events_without_starting_times(self):
        day_range = pd.date_range(start='01/03/2014', end='04/15/2014')
        
        events_without_starting_times = []
        for i in day_range:
            day = i.date().strftime('%m-%d')
            next_day = (i.date() + datetime.timedelta(days=1)).strftime('%m-%d')

            prices = self.get_price_data('2015-' + day, '2015-' + next_day)

            #print(prices)

            price_vector = np.array(np.repeat(prices['GB_GBN_price_day_ahead'], 4))
            #print(price_vector)

            events = self.read_events_from_csv('events.csv').drop(columns=['end'])
            events = events[events['start'].between('2014-' + day, '2014-' + next_day)]

            #print(events)

            events['start'] = events['start'].apply(lambda x: x.hour*4 + (x.minute // 15))
            events['duration'] = events['duration'].apply(lambda x: x // 15)
            events['profile'] = events['profile'].apply(lambda x: [float(idx) for idx in x.strip("[]").split(', ')])


            #print(events)

            #patterns = self.find_patterns_on_day('output/Experiment_minsup0.1_minconf_0.6/level2.json', events)
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
            
            for key, val in potential_start_times.items():
                if len(potential_start_times[key]) == 0:
                    events_without_starting_times.append(key)
        
        print(events_without_starting_times)