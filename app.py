import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
from flask import Flask, request, render_template, redirect, url_for

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def find_data_start_row(df):
    for i, row in df.iterrows():
        try:
            pd.to_datetime(row.iloc[0], dayfirst=True)
            return i
        except (ValueError, TypeError):
            continue
    return -1

# --- Core Data Processing Logic ---
def process_file(file_path):
    """
    Takes a file path, performs all analysis, and returns the results in a dictionary.
    """
    df = pd.read_excel(file_path, header=None)
    start_row = find_data_start_row(df)
    
    if start_row == -1:
        return {'error': "Could not find a valid data start row (with a date) in the file."}

    df = df.iloc[start_row:].reset_index(drop=True)

    data_df = df.iloc[:, :4]
    data_df.columns = ['DATE', 'TIME', 'DISTANCE', 'SPEED']
    
    for col in ['DISTANCE', 'SPEED']:
        data_df[col] = pd.to_numeric(data_df[col], errors='coerce')

    data_df.dropna(subset=['DATE', 'TIME', 'DISTANCE', 'SPEED'], inplace=True)
    if data_df.empty:
        return {'error': "No valid data rows found after cleaning."}

    data_df['DATETIME'] = pd.to_datetime(data_df['DATE'].astype(str) + ' ' + data_df['TIME'].astype(str), dayfirst=True)
    data_df['CUMULATIVE_DISTANCE'] = data_df['DISTANCE'].cumsum() / 1000  # Convert to KM

    # --- Metrics and Analysis ---
    stop_analysis_results = []
    stop_events = data_df[(data_df['SPEED'] == 0) & (data_df['SPEED'].shift(1) > 0)]
    points_before_stop = []

    for index, stop_row in stop_events.iterrows():
        stop_dist = stop_row['CUMULATIVE_DISTANCE']
        stop_analysis_results.append(f"Stop detected at {stop_dist:.2f} km.")
        
        pre_stop_data = data_df.loc[:index]
        for meters_before in [50, 100]:
            target_dist = stop_dist - (meters_before / 1000.0)
            if target_dist > 0:
                closest_idx = (pre_stop_data['CUMULATIVE_DISTANCE'] - target_dist).abs().idxmin()
                speed = pre_stop_data.loc[closest_idx, 'SPEED']
                dist = pre_stop_data.loc[closest_idx, 'CUMULATIVE_DISTANCE']
                stop_analysis_results.append(f"  - Speed ~{meters_before}m before: {speed} Kmph (at {dist:.2f} km)")
                points_before_stop.append((dist, speed))

    total_distance = data_df['CUMULATIVE_DISTANCE'].iloc[-1]
    max_speed = data_df['SPEED'].max()
    max_speed_idx = data_df['SPEED'].idxmax()
    dist_at_max_speed = data_df.loc[max_speed_idx, 'CUMULATIVE_DISTANCE']
    time_at_max_speed = data_df.loc[max_speed_idx, 'DATETIME']

    metrics = {
        'total_distance': f"{total_distance:.2f} km",
        'max_speed': f"{max_speed} Kmph",
        'max_speed_details': f"(at {dist_at_max_speed:.2f} km, time {time_at_max_speed.strftime('%H:%M:%S')})"
    }

    # --- Generate Interactive Plots with Plotly ---
    fig_time_speed = px.line(data_df, x='DATETIME', y='SPEED', title="Speed vs. Time", labels={'DATETIME': 'Time', 'SPEED': 'Speed (Kmph)'})
    fig_dist_speed = px.line(data_df, x='CUMULATIVE_DISTANCE', y='SPEED', title="Speed vs. Cumulative Distance", labels={'CUMULATIVE_DISTANCE': 'Cumulative Distance (Km)', 'SPEED': 'Speed (Kmph)'})

    # Add red dots to the distance-speed graph
    if points_before_stop:
        dists, speeds = zip(*points_before_stop)
        fig_dist_speed.add_scatter(x=dists, y=speeds, mode='markers', marker=dict(color='red', size=8), name='Speed Before Stop')

    # Convert plots to HTML
    graph1_html = pio.to_html(fig_time_speed, full_html=False)
    graph2_html = pio.to_html(fig_dist_speed, full_html=False)

    return {
        'metrics': metrics,
        'stop_analysis': stop_analysis_results,
        'graph1_html': graph1_html,
        'graph2_html': graph2_html
    }

# --- Flask Routes ---
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            # Process the file and get results
            results = process_file(filepath)
            
            # Render the page again, this time with the results
            return render_template('index.html', results=results, filename=file.filename)

    # For a GET request, just show the upload page
    return render_template('index.html', results=None)

if __name__ == '__main__':
    app.run(debug=True)
