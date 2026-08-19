import pandas as pd
import os

def process_handicaps():
    if not os.path.exists('manual_entries.csv'):
        print("No manual entries found.")
        return

    # Just read the file and run the math
    df = pd.read_csv('manual_entries.csv')
    df = df.sort_values('Segment Time (s)').drop_duplicates('Name').reset_index(drop=True)
    
    # [Insert your handicap calculation logic here]
    
    df.to_csv("bulimba_roadies_latest.csv", index=False)
    print("Processed manual entries only.")

if __name__ == "__main__":
    process_handicaps()
