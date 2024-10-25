from flask import Flask, request, render_template, redirect, url_for
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import urllib.parse

app = Flask(__name__)

# Directory to save uploaded files
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper function to generate a line plot for stock prices
def generate_line_plot(stock_df, x_col, y_col, title, xlabel, ylabel):
    plt.figure(figsize=(10, 6))
    plt.plot(stock_df[x_col], stock_df[y_col], label=y_col, color='blue')
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid()

    # Save plot to a string buffer
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read()).decode('utf-8')
    uri = f'data:image/png;base64,{string}'
    plt.close()

    return uri

# Helper function to generate a bar plot for volume
def generate_bar_plot(stock_df):
    plt.figure(figsize=(10, 6))
    plt.bar(stock_df['Date'], stock_df['Volume'], color='orange')
    plt.title('Volume Over Time')
    plt.xlabel('Date')
    plt.ylabel('Volume')
    plt.xticks(rotation=45)
    plt.grid()

    # Save plot to a string buffer
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read()).decode('utf-8')
    uri = f'data:image/png;base64,{string}'
    plt.close()

    return uri

# Helper function to generate a histogram for closing prices
def generate_histogram(stock_df):
    plt.figure(figsize=(10, 6))
    sns.histplot(stock_df['Close'], bins=30, kde=True, color='green')
    plt.title('Closing Price Distribution')
    plt.xlabel('Closing Price')
    plt.ylabel('Frequency')
    plt.grid()

    # Save plot to a string buffer
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read()).decode('utf-8')
    uri = f'data:image/png;base64,{string}'
    plt.close()

    return uri

# Helper function to generate a moving average plot
def generate_moving_average_plot(stock_df, window=20):
    stock_df['Moving Average'] = stock_df['Close'].rolling(window=window).mean()
    
    plt.figure(figsize=(10, 6))
    plt.plot(stock_df['Date'], stock_df['Close'], label='Close Price', color='blue')
    plt.plot(stock_df['Date'], stock_df['Moving Average'], label=f'Moving Average ({window} Days)', color='orange')
    plt.title(f'Closing Price and Moving Average ({window} Days)')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()

    # Save plot to a string buffer
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read()).decode('utf-8')
    uri = f'data:image/png;base64,{string}'
    plt.close()

    return uri

# Helper function to calculate summary statistics
def calculate_summary(stock_df):
    summary = {
        'Max': stock_df[['Open', 'Close', 'High', 'Low', 'Volume']].max(),
        'Min': stock_df[['Open', 'Close', 'High', 'Low', 'Volume']].min(),
        'Sum': stock_df[['Open', 'Close', 'High', 'Low', 'Volume']].sum(),
        'Mean': stock_df[['Open', 'Close', 'High', 'Low', 'Volume']].mean()
    }
    return pd.DataFrame(summary).T  # Transpose the DataFrame for better readability

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the POST request has the file part
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        # If the user does not select a file, the browser submits an empty part without filename
        if file.filename == '':
            return redirect(request.url)

        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Process the uploaded CSV file
            try:
                stock_df = pd.read_csv(filepath)
            except Exception as e:
                return f"Error reading the CSV file: {e}"

            # Debug: Print the first few rows of the DataFrame and its columns
            print("DataFrame head:\n", stock_df.head())  # Check the contents of the DataFrame
            print("DataFrame columns:", stock_df.columns)  # Check the column names

            # Convert the Date column to datetime
            if 'Date' in stock_df.columns:
                stock_df['Date'] = pd.to_datetime(stock_df['Date'], errors='coerce')
            else:
                return "Error: 'Date' column not found in the uploaded file."

            # Check if 'Date' column was parsed correctly
            if stock_df['Date'].isnull().all():
                return "Error: 'Date' column contains invalid date formats."

            # Create the 'Year' column
            stock_df['Year'] = stock_df['Date'].dt.year

            # Check if 'Year' column was created
            if 'Year' not in stock_df.columns:
                return "Error: 'Year' column could not be created from 'Date'."

            # Generate initial plots
            line_plot_url = generate_line_plot(stock_df, 'Date', 'Close', 'Stock Closing Price Over Time', 'Date', 'Price')
            volume_plot_url = generate_bar_plot(stock_df)
            histogram_plot_url = generate_histogram(stock_df)
            moving_avg_plot_url = generate_moving_average_plot(stock_df)

            # Calculate summary statistics
            summary_df = calculate_summary(stock_df)
            summary_html = summary_df.to_html(classes='table table-striped', header="true")

            return render_template('chart.html', 
                                   line_plot_url=line_plot_url, 
                                   volume_plot_url=volume_plot_url,
                                   histogram_plot_url=histogram_plot_url,
                                   moving_avg_plot_url=moving_avg_plot_url,
                                   summary_html=summary_html,
                                   unique_years=stock_df['Year'].unique(),
                                   filename=file.filename)

@app.route('/filter/<year>/<filename>')
def filter_data(year, filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    stock_df = pd.read_csv(filepath)
    stock_df['Date'] = pd.to_datetime(stock_df['Date'], errors='coerce')

    # Filter the DataFrame for the selected year
    filtered_df = stock_df[stock_df['Date'].dt.year == int(year)]

    # Generate plots for the filtered data
    line_plot_url = generate_line_plot(filtered_df, 'Date', 'Close', 'Stock Closing Price Over Time', 'Date', 'Price')
    volume_plot_url = generate_bar_plot(filtered_df)
    histogram_plot_url = generate_histogram(filtered_df)
    moving_avg_plot_url = generate_moving_average_plot(filtered_df)

    # Calculate summary statistics for filtered data
    summary_df = calculate_summary(filtered_df)
    summary_html = summary_df.to_html(classes='table table-striped', header="true")

    return render_template('chart.html',
                           line_plot_url=line_plot_url,
                           volume_plot_url=volume_plot_url,
                           histogram_plot_url=histogram_plot_url,
                           moving_avg_plot_url=moving_avg_plot_url,
                           summary_html=summary_html,
                           unique_years=filtered_df['Year'].unique(),
                           filename=filename)

if __name__ == '__main__':
    app.run(debug=True)
