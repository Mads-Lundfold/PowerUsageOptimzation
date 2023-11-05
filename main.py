import pandas as pd
from data_grapper import DataManager

#TODO Linear programming optimizer
#TODO Comments on code
#TODO Restructure entire project with nice architecture
#TODO Make frontend :O

start = 1388734400
end = 1398766800

TESTING_OPT = True

dm = DataManager()
dm.get_usage_data(start, end)
print("Successfully loaded the data.")
running = True

if TESTING_OPT:
    #dm.load_temporal_patterns('output/Experiment_minsup0.1_minconf_0.6/level2.json')
    dm.optimize()
else:
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