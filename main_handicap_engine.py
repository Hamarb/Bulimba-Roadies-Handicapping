import os
import requests
import pandas as pd
from datetime import datetime

def compute_handicaps(df):
    # 1. Sort from fastest to slowest
    df = df.sort_values(by="Segment Time (s)").reset_index(drop=True)
    
    fastest = df["Segment Time (s)"].min()
    slowest = df["Segment Time (s)"].max()
    delta = slowest - fastest
    count = len(df)
    
    # 2. Assign handicaps: Fastest gets the full penalty, slowest gets 0 penalty
    # We reverse the index: i=0 (fastest) gets (delta), i=last (slowest) gets 0
    handicaps = []
    for i in range(count):
        if count > 1:
            h = delta * (1 - (i / (count - 1))) 
        else:
            h = 0.0
        handicaps.append(round(h))
        
    df["Handicap_Sec"] = handicaps
    
    # 3. Add the handicap (penalty) to the actual time
    # This brings the fastest riders' times up to match the slowest rider
    df["Adjusted_Sec"] = df["Segment Time (s)"] + df["Handicap_Sec"]
    
    # 4. Sort final results by Adjusted Time
    df = df.sort_values(by="Adjusted_Sec").reset_index(drop=True)
    df["Place"] = df.index + 1
    return df
