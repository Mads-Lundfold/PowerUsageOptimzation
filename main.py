import pandas as pd
import datetime
import sys
from data_grapper import DataManager

from events import get_events
from price_data import get_price_data
from data_loading import read_usage_data_csv
from time_associations import find_time_associations
from patterns import mine_temporal_patterns, find_patterns_on_day

df = read_usage_data_csv()
print(df)

events = get_events(df)
print(events)

time_associations = find_time_associations(df, threshold=0.15)
print(time_associations)

mine_temporal_patterns(support=0.1, confidence=0.6)


day = datetime.datetime(year=2014, month=1, day=17)
next_day = day + datetime.timedelta(days=1)

events_on_day = events[events['start'].between(day, next_day)]

print(find_patterns_on_day('output/Experiment_minsup0.1_minconf_0.6/level2.json', events_on_day))

sys.exit()

#TODO Comments on code
#TODO Restructure entire project with nice architecture
#TODO Make frontend :O

start = 1388617200
end = 1420066799


TESTING_OPT = True
TESTING_ONE_DAY = not True


dm = DataManager()
dm.get_usage_data(start, end)
print("Successfully loaded the data.")
running = True


if TESTING_ONE_DAY:
    day = datetime.datetime(year=2014, month=1, day=17)
    next_day = day + datetime.timedelta(days=1)
    try:
        dm.optimize(day, next_day)
    except:
        print('whoopsie')

    print(f'Cost before {dm.cost_before}')
    print(f'Cost after  {dm.cost_after}')
    

if TESTING_OPT:
    #dm.load_temporal_patterns('output/Experiment_minsup0.1_minconf_0.6/level2.json')
    total_cost = 0
    exception_days = list()
    day_range = pd.date_range(start='01/04/2014', end='12/28/2014')
    for i in day_range:
        try:
            next_day = (i + datetime.timedelta(days=1))
            
            dm.optimize(i, next_day)

        except Exception as e:
            exception_days.append({'day': i, 'msg': e})
            pass
    
    print(f'Cost before {dm.cost_before}')
    print(f'Cost after  {dm.cost_after}')
    
    for e in exception_days:
        print(e['day'], e['msg'])
    
    #dm.check_events_without_starting_times()
elif False:
    while(running):
        print("Enter a command:")
        command = input(">> ")

        match command:
            case 'load':
                dm.get_usage_data(start, end)

                print("Successfully loaded the data.")
            case 'mine':
                support = 0.10
                confidence = 0.60
                dm.mine_temporal_patterns(support, confidence)
            case 'o':
                dm.optimize()
            case 'q':
                running = False
            case '_':
                print('Command Not recognized.')


#data = dm.get_usage_data(start, end)

#dm.get_price_data(1,2)
'''
def main():
    print('Finding events.')
    events = get_events_from_data(start, end)
    print('Found events:')
    print(events)
    
    price_data = get_price_data(start, end)
    print(price_data)

    return
    find_time_associations()
    find_temporal_patterns()

    problem = create_optimization_problem()
    problem.solve()




def find_time_associations():
    return True

def find_temporal_patterns():
    return True

def create_optimization_problem():
    return 

main()
'''