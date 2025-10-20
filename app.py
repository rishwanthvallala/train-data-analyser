import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
from flask import Flask, request, render_template, redirect, url_for
import time
import plotly.graph_objects as go

# --- Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    start_time = time.time()
    filename = os.path.basename(file_path)
    print(f"[{start_time:.2f}] --- Starting file processing for: {filename} ---")

    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(file_path, header=None, low_memory=False)
        else:
            df = pd.read_excel(file_path, header=None, usecols='A:D')
    except Exception as e:
        return {'error': f"Error reading file. It might be corrupted or in an unexpected format. Details: {e}"}

    t_after_read = time.time()
    print(f"[{t_after_read:.2f}] File read into pandas DataFrame. Time taken: {t_after_read - start_time:.2f}s")

    start_row = find_data_start_row(df)
    
    if start_row == -1:
        return {'error': "Could not find a valid data start row (with a date) in the file."}

    df = df.iloc[start_row:].reset_index(drop=True)
    data_df = df.copy()
    data_df.columns = ['DATE', 'TIME', 'DISTANCE', 'SPEED']
    
    for col in ['DISTANCE', 'SPEED']:
        data_df[col] = pd.to_numeric(data_df[col], errors='coerce')

    data_df.dropna(subset=['DATE', 'TIME', 'DISTANCE', 'SPEED'], inplace=True)
    if data_df.empty:
        return {'error': "No valid data rows found after cleaning."}

    data_df['DATETIME'] = pd.to_datetime(data_df['DATE'].astype(str) + ' ' + data_df['TIME'].astype(str), dayfirst=True)
    data_df['CUMULATIVE_DISTANCE'] = data_df['DISTANCE'].cumsum() / 1000
    
    t_after_clean = time.time()
    print(f"[{t_after_clean:.2f}] Data cleaning and prep complete. Time taken: {t_after_clean - t_after_read:.2f}s")

    # --- Metrics and Analysis ---
    stop_analysis_results = []
    stop_events = data_df[(data_df['SPEED'] == 0) & (data_df['SPEED'].shift(1) > 0)]
    points_before_stop = []
    deceleration_data_frames = [] 

    for index, stop_row in stop_events.iterrows():
        stop_dist = stop_row['CUMULATIVE_DISTANCE']; stop_time = stop_row['DATETIME']
        stop_time_str = stop_time.strftime('%H:%M:%S')
        stop_analysis_results.append(f"Stop detected at {stop_dist:.2f} km (Time: {stop_time_str}).")
        
        target_dist_1km_before = stop_dist - 1.0 
        pre_stop_data = data_df.loc[:index].copy() 
        start_index = (pre_stop_data['CUMULATIVE_DISTANCE'] - target_dist_1km_before).abs().idxmin()
        
        decel_segment = data_df.loc[start_index:index].copy()
        if not decel_segment.empty:
            decel_segment['RELATIVE_DISTANCE'] = decel_segment['CUMULATIVE_DISTANCE'] - decel_segment['CUMULATIVE_DISTANCE'].min()
            decel_segment['STOP_TIME'] = stop_time_str
            deceleration_data_frames.append(decel_segment)
        
        for meters_before in [1, 10, 50, 100]:
            target_dist = stop_dist - (meters_before / 1000.0)
            if target_dist > 0:
                closest_idx = (pre_stop_data['CUMULATIVE_DISTANCE'] - target_dist).abs().idxmin()
                speed = pre_stop_data.loc[closest_idx, 'SPEED']; dist = pre_stop_data.loc[closest_idx, 'CUMULATIVE_DISTANCE']; time_before = pre_stop_data.loc[closest_idx, 'DATETIME']
                stop_analysis_results.append(f"  - Speed ~{meters_before}m before: {speed} Kmph (at {dist:.2f} km, Time: {time_before.strftime('%H:%M:%S')})")
                points_before_stop.append((dist, speed))

    t_after_analysis = time.time()
    print(f"[{t_after_analysis:.2f}] Stop/Metric analysis complete. Time taken: {t_after_analysis - t_after_clean:.2f}s")
    
    total_distance = data_df['CUMULATIVE_DISTANCE'].iloc[-1]; max_speed = data_df['SPEED'].max()
    max_speed_idx = data_df['SPEED'].idxmax()
    dist_at_max_speed = data_df.loc[max_speed_idx, 'CUMULATIVE_DISTANCE']; time_at_max_speed = data_df.loc[max_speed_idx, 'DATETIME']

    metrics = {
        'total_distance': f"{total_distance:.2f} km", 'max_speed': f"{max_speed} Kmph",
        'max_speed_details': f"(at {dist_at_max_speed:.2f} km, time {time_at_max_speed.strftime('%H:%M:%S')})"
    }

    # --- Data Downsampling for Plotting ---
    plot_df = data_df.set_index('DATETIME')
    plot_df = plot_df.resample('10S').mean(numeric_only=True).reset_index()
    plot_df.dropna(inplace=True)
    t_after_resample = time.time()
    print(f"[{t_after_resample:.2f}] Data resampled for plotting. Time taken: {t_after_resample - t_after_analysis:.2f}s")

    # --- Generate Interactive Plots with Plotly ---
    fig_time_speed = px.line(plot_df, x='DATETIME', y='SPEED', title="Speed vs. Time (Resampled to 10s intervals)", labels={'DATETIME': 'Time', 'SPEED': 'Speed (Kmph)'})
    graph1_html = pio.to_html(fig_time_speed, full_html=False)
    t_after_graph1 = time.time()
    print(f"[{t_after_graph1:.2f}] Graph 1 generated. Time taken: {t_after_graph1 - t_after_resample:.2f}s")
    
    fig_dist_speed = px.line(data_df, x='CUMULATIVE_DISTANCE', y='SPEED', title="Speed vs. Cumulative Distance", labels={'CUMULATIVE_DISTANCE': 'Cumulative Distance (Km)', 'SPEED': 'Speed (Kmph)'})
    if points_before_stop:
        dists, speeds = zip(*points_before_stop)
        fig_dist_speed.add_scatter(x=dists, y=speeds, mode='markers', marker=dict(color='red', size=8), name='Speed Before Stop')
    graph2_html = pio.to_html(fig_dist_speed, full_html=False)
    t_after_graph2 = time.time()
    print(f"[{t_after_graph2:.2f}] Graph 2 generated. Time taken: {t_after_graph2 - t_after_graph1:.2f}s")
    
    # --- Plot 3: Deceleration Profile ---
    decel_plot_html = ""
    if deceleration_data_frames:
        fig_decel = go.Figure()
        
        for df_segment in deceleration_data_frames:
            fig_decel.add_trace(go.Scatter(
                x=df_segment['RELATIVE_DISTANCE'] * 1000,
                y=df_segment['SPEED'],
                mode='lines',
                name=f"Stop at {df_segment['STOP_TIME'].iloc[0]}"
            ))

        # --- THIS IS THE UPDATED SECTION ---
        fig_decel.update_layout(
            title="Deceleration Profile (1000m Before Stop)",
            xaxis_title="Distance Before Stop (meters)",
            yaxis_title="Speed (Kmph)",
            legend_title="Stop Time",
            #xaxis=dict(autorange='reversed') # This line reverses the x-axis
        )
        decel_plot_html = pio.to_html(fig_decel, full_html=False)

    t_after_decel_plot = time.time()
    print(f"[{t_after_decel_plot:.2f}] Graph 3 (Decel Profile) generated. Time taken: {t_after_decel_plot - t_after_graph2:.2f}s")

    total_time = time.time() - start_time
    print(f"[{time.time():.2f}] --- Finished file processing. Total time: {total_time:.2f}s ---")

    return {
        'metrics': metrics, 'stop_analysis': stop_analysis_results,
        'graph1_html': graph1_html, 'graph2_html': graph2_html,
        'decel_plot_html': decel_plot_html 
    }

# --- Flask Routes (Unchanged) ---
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files: return redirect(request.url)
        file = request.files['file']
        if file.filename == '': return redirect(request.url)
        if file and allowed_file(file.filename):
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            results = process_file(filepath)
            return render_template('index.html', results=results, filename=filename)
    return render_template('index.html', results=None)

if __name__ == '__main__':
    app.run(debug=True)