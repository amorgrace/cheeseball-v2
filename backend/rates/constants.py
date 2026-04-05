ASSET_SEED_DATA = [
    {"code": "BTC", "name": "Bitcoin", "binance_symbol": "BTCUSDT", "fallback_market_rate": "150000000", "sort_order": 10},
    {"code": "ETH", "name": "Ethereum", "binance_symbol": "ETHUSDT", "fallback_market_rate": "5000000", "sort_order": 20},
    {"code": "USDT", "name": "Tether", "binance_symbol": "USDTUSDT", "fallback_market_rate": "1600", "sort_order": 30},
    {"code": "BNB", "name": "BNB", "binance_symbol": "BNBUSDT", "fallback_market_rate": "900000", "sort_order": 40},
    {"code": "SOL", "name": "Solana", "binance_symbol": "SOLUSDT", "fallback_market_rate": "240000", "sort_order": 50},
    {"code": "XRP", "name": "XRP", "binance_symbol": "XRPUSDT", "fallback_market_rate": "3500", "sort_order": 60},
    {"code": "TRX", "name": "TRON", "binance_symbol": "TRXUSDT", "fallback_market_rate": "220", "sort_order": 70},
    {"code": "LTC", "name": "Litecoin", "binance_symbol": "LTCUSDT", "fallback_market_rate": "140000", "sort_order": 80},
    {"code": "DOGE", "name": "Dogecoin", "binance_symbol": "DOGEUSDT", "fallback_market_rate": "280", "sort_order": 90},
    {"code": "BCH", "name": "Bitcoin Cash", "binance_symbol": "BCHUSDT", "fallback_market_rate": "800000", "sort_order": 100},
    {"code": "ADA", "name": "Cardano", "binance_symbol": "ADAUSDT", "fallback_market_rate": "1200", "sort_order": 110},
    {"code": "MATIC", "name": "Polygon", "binance_symbol": "MATICUSDT", "fallback_market_rate": "700", "sort_order": 120},
    {"code": "DOT", "name": "Polkadot", "binance_symbol": "DOTUSDT", "fallback_market_rate": "9000", "sort_order": 130},
    {"code": "LINK", "name": "Chainlink", "binance_symbol": "LINKUSDT", "fallback_market_rate": "25000", "sort_order": 140},
    {"code": "AVAX", "name": "Avalanche", "binance_symbol": "AVAXUSDT", "fallback_market_rate": "60000", "sort_order": 150},
    {"code": "UNI", "name": "Uniswap", "binance_symbol": "UNIUSDT", "fallback_market_rate": "12000", "sort_order": 160},
    {"code": "XLM", "name": "Stellar", "binance_symbol": "XLMUSDT", "fallback_market_rate": "700", "sort_order": 170},
    {"code": "ATOM", "name": "Cosmos", "binance_symbol": "ATOMUSDT", "fallback_market_rate": "8000", "sort_order": 180},
    {"code": "ETC", "name": "Ethereum Classic", "binance_symbol": "ETCUSDT", "fallback_market_rate": "50000", "sort_order": 190},
    {"code": "TON", "name": "Toncoin", "binance_symbol": "TONUSDT", "fallback_market_rate": "7500", "sort_order": 200},
]

SUPPORTED_ASSET_CODES = {asset["code"] for asset in ASSET_SEED_DATA}
ASSET_SEED_BY_CODE = {asset["code"]: asset for asset in ASSET_SEED_DATA}
