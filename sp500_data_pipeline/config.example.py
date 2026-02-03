"""
Example configuration for S&P 500 Hourly Stock Data Pipeline
Copy this to config.py and edit with your database credentials
"""

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "your_password_here",
    "port": 5432,
}

# Data fetching
LOOKBACK_DAYS = 7  # How many days back to fetch
MAX_WORKERS = 8    # Number of parallel threads for downloading
BATCH_SIZE = 50    # Ticker batch size

# Logging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
