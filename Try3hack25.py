from ipywidgets import FileUpload
import io
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import pandas as pd


uploader = FileUpload(accept='.csv,.xlsx', multiple=True)
display(uploader)
# After uploading files via the widget, run the next cell to load them:
def load_uploaded(uploader):
    dfs = []
    for name, fileinfo in uploader.value.items():
        content = fileinfo['content']
        if name.endswith('.csv'):
            dfs.append(pd.read_csv(io.BytesIO(content)))
        else:
            dfs.append(pd.read_excel(io.BytesIO(content)))
    return pd.concat(dfs, ignore_index=True)

# Example: after user uploads, run:
# df = load_uploaded(uploader)

root = tk.Tk()
root.withdraw()
file_paths = filedialog.askopenfilenames(
    title="Select spreadsheet files",
    filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
)
file_paths = list(file_paths)
print("Selected:", file_paths)

# Load into DataFrame
dfs = []
for p in file_paths:
    if p.lower().endswith('.csv'):
        dfs.append(pd.read_csv(p))
    else:
        dfs.append(pd.read_excel(p))
df = pd.concat(dfs, ignore_index=True)


paths = input("Enter spreadsheet file paths separated by commas: ").split(",")
paths = [p.strip() for p in paths if p.strip()]
dfs = []
for p in paths:
    if p.lower().endswith('.csv'):
        dfs.append(pd.read_csv(p))
    else:
        dfs.append(pd.read_excel(p))
df = pd.concat(dfs, ignore_index=True)
print(f"Loaded {len(df)} rows from {len(paths)} files")
