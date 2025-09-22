# Train Data Analyser

This is a web application for analyzing train journey data from Excel or CSV files. The application is hosted at: <https://railway.pythonanywhere.com/>

## Functionality

- **File Upload**: Accepts `.xlsx`, `.xls`, and `.csv` files containing train data.
- **Data Processing**:
  - Automatically identifies the start of the data in the uploaded file.
  - Cleans the data by handling numeric conversions and removing invalid rows.
  - Calculates cumulative distance traveled in kilometers.
- **Metric Calculation**:
  - Determines the total distance of the journey.
  - Finds the maximum speed reached and the time and location it occurred.
- **Stop Analysis**:
  - Detects all instances where the train comes to a complete stop.
  - For each stop, it reports the speed at approximately 50 and 100 meters prior to the stop.
- **Data Visualization**:
  - Generates an interactive plot of Speed vs. Time. The data is resampled to 10-second intervals for better visualization.
  - Creates an interactive plot of Speed vs. Cumulative Distance, which also marks the specific points where pre-stop speed was measured.

## How to Use

1. Navigate to the application URL.
2. Click the button to select a file from your local machine.
3. Click the "Upload & Analyze" button.
4. The application will process the file and display the analysis, including key metrics and interactive graphs.

## Project Structure

```bash
train-data-analyser/
|-- app.py              # Main Flask application file.
|-- requirements.txt    # Package dependencies file.
|-- uploads/            # Directory where uploaded files are temporarily stored.
`-- templates/
    `-- index.html      # The HTML template for the user interface.
```

## Dependencies

- **Flask**: The web framework used to build the application.
- **pandas**: Used for data manipulation and analysis.
- **openpyxl**: Required by pandas to read Excel files.
- **plotly**: Used for generating interactive charts and graphs.
