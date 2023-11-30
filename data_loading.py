import pandas as pd
import os
import re

start = 1388617200
end = 1420066799

appliances_of_interest = ['laptop', 'washing_machine', 'dishwasher', 'tv', 'htpc', 'kettle', 
                          'toaster', 'microwave', 'lcd_office', 'hifi_office', 'breadmaker', 
                          'amp_livingroom', 'hoover', 'subwoofer_livingroom', 'DAB_radio_livingroom', 
                          'coffee_machine', 'kitchen_radio', 'hair_dryer', 'straighteners', 'iron', 
                          'gas_oven', 'office_pc', 'office_fan']

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

data_directory = 'data/derived/'

def rename_channel_files_to_appliance_names(directory_path: str):
    labels = pd.read_csv(f'{directory_path}\\labels.dat', sep=' ', names=['channel', 'label']).set_index('channel')
    print(labels)

    for file in os.listdir(directory_path):
        if not re.compile('channel_[0-9]+.dat').match(file):
            continue

        channel_number = file.replace('channel_', '').replace('.dat', '') # Very crude, but it works
        print(labels.loc[int(channel_number), 'label'])
        
        os.rename(f'{directory_path}\\{file}', f'{directory_path}\\{labels.loc[int(channel_number), 'label']}')



def load_data():
    #print('Insert path to data directory:')
    directory_path = 'c:\\ukdale\\house_1'

    df = []

    for file in os.listdir(directory_path):
        if file not in appliances_of_interest:
            continue

        data = pd.read_csv(f'{directory_path}\\{file}', sep=' ', names=['Time', f'{file}']).set_index('Time').query("Time >= @start and Time <= @end")
        
        threshold = power_thresholds.get(file, 5)
        data[file] = data[file].apply(lambda x: x if x > threshold else 0) 

        data.index = data.index // 900 * 900
        data.index = pd.to_datetime(data.index, unit='s')

        data = data.groupby('Time').mean()

        print(data)
        df.append(data)
    
    df = pd.concat(df, axis=1).fillna(0.0)
    print(df)

    write_usage_data_to_csv(df)


def write_usage_data_to_csv(data: pd.DataFrame):
    data.to_csv(data_directory + 'usage_data.csv')

def read_usage_data_csv() -> pd.DataFrame:
    df = pd.read_csv(data_directory + 'usage_data.csv')
    df['Time'] = pd.to_datetime(df['Time'])
    df = df.set_index('Time')
    return df

