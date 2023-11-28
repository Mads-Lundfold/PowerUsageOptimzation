import pandas as pd
from datetime import datetime

def get_price_data(start, end):
    start = datetime.fromtimestamp(start)
    start = start.replace(year=2015)
    end = datetime.fromtimestamp(end)
    end = end.replace(year=2015)
    
    data = pd.read_csv("./data/raw/Electricity_price_dataset_new.csv").drop(columns="cet_cest_timestamp").dropna()

    data['utc_timestamp'] = pd.to_datetime(data['utc_timestamp']).dt.tz_localize(None)

    data = data.rename(columns={'utc_timestamp' : 'Time'})

    data = data.query('Time.between(@start, @end)')

    if len(data) < 25:
            data = data.set_index('Time').resample('H').asfreq().reset_index()
            data = data.fillna(method='ffill')
                    
    data["GB_GBN_price_day_ahead"] = data["GB_GBN_price_day_ahead"].divide(1000000)

    return data
