import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key'
    
    # Caching config
    CACHE_TYPE = "FileSystemCache"
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
    CACHE_DEFAULT_TIMEOUT = 3600 # 1 hour

    # Application settings
    COLOR_SCHEME = {
        "positive": "#6ECB63",
        "neutral":  "#F8B400",
        "neutral_light": "rgba(248, 180, 0, 0.10)",
        "negative": "#EB5353",
        "score":    "#024564",
        "score_light": "#036280",
        "bg": "#ffffff",
        "grid": "rgba(220,220,220,0.3)"
    }

    PUBLISHER_WEIGHTS = {
        "reuters": 1.0, "bloomberg": 1.0, "cnbc": 1.0, "yahoo finance": 1.0,
        "wsj": 1.0, "ft": 1.0, "marketwatch": 0.9, "barrons": 0.9,
        "seeking alpha": 0.7, "motley fool": 0.7,
    }
