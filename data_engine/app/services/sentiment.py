import pandas as pd
from textblob import TextBlob
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

_nltk_ready = False
_vader = None

def _init():
    global _nltk_ready, _vader
    if not _nltk_ready:
        nltk.download('vader_lexicon', quiet=True)
        _vader = SentimentIntensityAnalyzer()
        _nltk_ready = True

def score_sentiment(rows: list[dict]) -> pd.DataFrame:
    _init()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    if "title" not in df.columns:
        for alt in ("headline", "headlines", "text", "name"):
            if alt in df.columns:
                df["title"] = df[alt]
                break
        else:
            df["title"] = ""

    # Ép str để tránh lỗi khi có None/float
    df["title"] = df["title"].astype(str)

    # Tối ưu: Dùng list comprehension thay cho df.apply(pd.Series)
    titles = df["title"].tolist()
    
    vader_scores = [_vader.polarity_scores(t) for t in titles]
    v_df = pd.DataFrame(vader_scores)
    
    # TextBlob có thể chậm, nhưng dùng list comprehension sẽ nhanh hơn apply xíu
    tb_scores = [TextBlob(t).sentiment for t in titles]
    tb_df = pd.DataFrame([(s.polarity, s.subjectivity) for s in tb_scores], columns=["tb_polarity", "tb_subjectivity"])

    out = pd.concat([df.reset_index(drop=True), v_df, tb_df], axis=1)

    if "ts" in out.columns:
        out["ts"] = pd.to_datetime(out["ts"], errors="coerce")
        out["date"] = out["ts"].dt.date
    else:
        out["date"] = pd.NaT

    return out