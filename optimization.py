import pandas as pd
import numpy as np
from pulp import LpProblem, LpVariable, LpBinary, LpMinimize

def optimize(events: pd.DataFrame, prices: pd.DataFrame, patterns: list, time_associations: dict):
    potential_start_times = {}

    for event in events.itertuples():
        potential_start_times[str(event.Index)] = find_potential_starting_times(event, time_associations)    

    '''
    for key, val in potential_start_times.items():
        print(f'{key}: {val}')
    '''


    cost_before = 0

    for e in events.itertuples():
        cost = np.sum(e.profile * prices[int(e.start) : int(e.start) + int(len(e.profile))])
        cost_before += cost
    
    print(cost_before)


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
    objective = sum(sum(variables[key][value] * np.sum(events.loc[int(key), 'profile'] * prices[value : value + int(len(events.loc[int(key), 'profile']))]) for value in potential_start_times[key]) for key in potential_start_times)

    problem += objective
    
    
    # TODO: Constraint that two events of same appliance cannot overlap.
    # Change event index to a column
    same_type_events = events.drop(columns=['start', 'duration', 'profile']).reset_index()
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
            problem += first_start_before_second_start(p, variables)
            problem += first_end_after_second_end(p, variables, events)
        elif p['type'] == '->':
            problem += first_end_before_second_start(p, variables, events)
        elif p['type'] == '|':
            problem += first_start_before_second_start(p, variables)
            problem += first_end_before_second_end(p, variables, events)
    
    problem.solve()

    #print(problem.objective.value())
    cost_after = problem.objective.value()
    print(cost_after)

    
    # Print the starting times for each event after solving the problem
    '''
    for v in problem.variables():
        if v.varValue == 1:
            print(v.name, "=", v.varValue)
    '''

def first_start_before_second_start(p, variables):
    return sum(value * var for value, var in variables[str(p['first'])].items()) <= sum(value * var for value, var in variables[str(p['second'])].items())

def first_end_after_second_end(p, variables, events):
    return sum(value * var for value, var in variables[str(p['first'])].items()) + int(events.loc[int(p['first']), 'duration']) >= sum(value * var for value, var in variables[str(p['second'])].items()) + int(events.loc[int(p['second']), 'duration'])

def first_end_before_second_start(p, variables, events):
    return sum(value * var for value, var in variables[str(p['first'])].items()) + int(events.loc[int(p['first']), 'duration']) <= sum(value * var for value, var in variables[str(p['second'])].items())

def first_end_before_second_end(p, variables, events):
    return sum(value * var for value, var in variables[str(p['first'])].items()) + int(events.loc[int(p['first']), 'duration']) <= sum(value * var for value, var in variables[str(p['second'])].items()) + int(events.loc[int(p['second']), 'duration'])


def find_potential_starting_times(event, time_associations: dict):
    highest_satis = 0
    valid_start_times = list()

    for start_time in time_associations[event.app]:
        if start_time + event.duration > 95: break

        event_range = list(range(start_time, start_time + int(event.duration)))
        satis = len(set(event_range) & set(time_associations[event.app]))
        
        if satis > highest_satis:
            highest_satis = satis
            valid_start_times.clear()
            valid_start_times.append(start_time) 
        elif satis == highest_satis:
            valid_start_times.append(start_time)
    
    if (time_associations[event.app][0] + event.duration > 95):
        valid_start_times.clear()
        valid_start_times.append(int(95 - event.duration))

    return valid_start_times 