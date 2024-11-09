import os
import pygal
import requests
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

# Flask app initialization
app = Flask(__name__)

# Set API KEY for Alpha Vantage
API_KEY = "C8FBEU84P5X4N5F1"
STATICFOLD = os.path.join(os.getcwd(), 'static')

# Function to retrieve stock symbols from a CSV file
def get_stock_symbols():
    stock_symbols = []
    try:
        with open('stocks.csv', 'r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                stock_symbols.append(row[0])  # Assuming the symbol is in the first column
    except FileNotFoundError:
        print("CSV file not found.")
    return stock_symbols

# Retrieve stock data from Alpha Vantage function
def retrieve_stock_data(stock_symbol, time_function, beginning_date, ending_date):
    try:
        print(f"Retrieving data for {stock_symbol} from {beginning_date} to {ending_date}")
        start_date_input = datetime.strptime(beginning_date, "%Y-%m-%d")
        end_date_input = datetime.strptime(ending_date, "%Y-%m-%d")

        if end_date_input < start_date_input:
            raise ValueError("Start date must be before end date.")
    except ValueError as e:
        print(f"Error in date input: {e}")
        return None

    # Build URL for Alpha Vantage API
    url = f"https://www.alphavantage.co/query?function={time_function}&symbol={stock_symbol}&apikey={API_KEY}&outputsize=full&datatype=json"
    api_response = requests.get(url)

    if api_response.status_code == 200:
        stock_data = api_response.json()
        time_type = {
            "TIME_SERIES_DAILY": "Time Series (Daily)",
            "TIME_SERIES_WEEKLY": "Weekly Time Series",
            "TIME_SERIES_MONTHLY": "Monthly Time Series"
        }.get(time_function)

        if not time_type:
            print("Time function not supported.")
            return None

        time_series_data = stock_data.get(time_type, {})
        date_range_data = {date: values for date, values in time_series_data.items() if beginning_date <= date <= ending_date}

        if not date_range_data:
            print(f"No data found between {beginning_date} and {ending_date}.")
            return None

        return date_range_data
    else:
        print(f"Failed to retrieve data. HTTP Code: {api_response.status_code}")
        return None

# Function which generates the chart and saves to the static folder
def generate_chart(data, chart_type, stock_symbol):
    chart = pygal.Bar(title=f"{stock_symbol} Stock Prices") if chart_type == "1" else pygal.Line(title=f"{stock_symbol} Stock Prices")
    dates = sorted(data.keys())
    closing_prices = [float(data[date]['4. close']) for date in dates]

    chart.x_labels = dates
    chart.add(stock_symbol, closing_prices)

    chart_file = os.path.join(STATICFOLD, f"{stock_symbol}_stock_chart.svg")

    if not os.path.exists(STATICFOLD):
        os.makedirs(STATICFOLD)

    chart.render_to_file(chart_file)
    return chart_file

# Flask route for handling form submission and chart display
@app.route('/', methods=['GET', 'POST'])
def display_chart():
    if request.method == 'POST':
        stock_symbol = request.form['stock_symbol']
        chart_type = request.form['chart_type']
        time_series_option = request.form['time_series_option']
        beginning_date = request.form['beginning_date']
        ending_date = request.form['ending_date']

        time_series_map = {
            "1": "TIME_SERIES_DAILY",
            "2": "TIME_SERIES_WEEKLY",
            "3": "TIME_SERIES_MONTHLY"
        }

        time_function = time_series_map.get(time_series_option)

        if not time_function:
            return "Invalid time series option."

        stock_data = retrieve_stock_data(stock_symbol, time_function, beginning_date, ending_date)
        if stock_data:
            chart_path = generate_chart(stock_data, chart_type, stock_symbol)
            chart_url = url_for('static', filename=os.path.basename(chart_path))
            return render_template('index.html', chart_data=chart_url, symbols=get_stock_symbols())
        else:
            return render_template('index.html', errors=["No data available for the given stock symbol and date range."])

    # GET request: Show form with stock symbols
    return render_template('index.html', symbols=get_stock_symbols())

if __name__ == "__main__":
    app.run(host="0.0.0.0")