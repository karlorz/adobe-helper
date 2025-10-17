"""
API URL constants for Futunn
"""

# Base URLs
BASE_URL = "https://www.futunn.com"

# API Endpoints
GET_STOCK_LIST = BASE_URL + "/quote-api/quote-v2/get-stock-list"
GET_INDEX_QUOTE = BASE_URL + "/quote-api/quote-v2/get-index-quote"
GET_INDEX_SPARK_DATA = BASE_URL + "/quote-api/quote-v2/get-index-spark-data"

# Page URLs (for token acquisition)
STOCK_LIST_PAGE = BASE_URL + "/quote/us/stock-list/all-us-stocks/top-turnover"
