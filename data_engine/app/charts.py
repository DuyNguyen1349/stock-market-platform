# app/charts.py
import matplotlib
matplotlib.use('Agg')  # non-GUI backend
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io, base64
from datetime import datetime  
from collections import Counter
import seaborn as sns
from app.config import Config
_COLOR_SCHEME = Config.COLOR_SCHEME
def _ensure_publisher_col(df: pd.DataFrame) -> pd.DataFrame:
    """Bảo đảm có cột 'publisher'. Ưu tiên bóc từ tiêu đề '... - Reuters',
    nếu không có thì dùng cột 'source' (domain rút gọn)."""
    if "publisher" in df.columns:
        return df
    df = df.copy()

    def _extract_pub(title: str, source: str) -> str:
        title = title or ""
        source = (source or "").strip().lower()
        # bắt mẫu ' - Publisher' ở CUỐI tiêu đề
        m = re.search(r"\s[-–—]\s*([A-Za-z .&]+)$", title)
        if m:
            name = m.group(1).strip().lower()
            # chuẩn hoá một vài tên hay gặp
            name = name.replace(" finance", "")
            mapping = {
                "yahoo": "yahoo finance",
                "wsj": "wall street journal",
                "seeking alpha": "seeking alpha",
                "investor's business daily": "investors business daily",
            }
            return mapping.get(name, name)
        # fallback: domain đã rút gọn
        return {
            "yahoo": "yahoo finance",
            "wsj": "wall street journal",
        }.get(source, source or "unknown")

    pubs = []
    # dùng itertuples để nhanh & an toàn khi thiếu cột
    for row in df.itertuples(index=False):
        title = getattr(row, "title", "")
        source = getattr(row, "source", "")
        pubs.append(_extract_pub(title, source))
    df["publisher"] = pubs
    return df
# ==== Plotly Global Style ====

_BASE_FONT = {"family": "Inter, system-ui, -apple-system, Segoe UI, Arial", "size": 12}

PLOTLY_CONFIG = {
    "responsive": True,
    "displayModeBar": True,
    "displaylogo": False,
    "scrollZoom": True,
    "modeBarButtonsToAdd": [
        "zoom2d","pan2d","select2d","lasso2d",
        "zoomIn2d","zoomOut2d","autoScale2d","resetScale2d","toImage"
    ],
}


# ==== GỌI HÀM NGẮN GỌN TRONG CÁC CHART ====


def _to_html(fig):
    """Render chart để clone trực tiếp qua modal"""
    fig.update_layout(
        autosize=True,
        margin=dict(l=40, r=20, t=60, b=40),
        font=dict(family="Inter, Arial, sans-serif", size=12),
        paper_bgcolor="white",
        plot_bgcolor="white"
    )
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,   # dùng script Plotly global ở <head>
        config={
            "responsive": True,
            "displaylogo": False,
            "displayModeBar": True,
            "scrollZoom": True
        }
    )

# (1) Line per headline
def chart_line_per_headline(df: pd.DataFrame, ticker: str):
    sub = df[df["ticker"] == ticker].copy()
    if sub.empty:
        return None

    sub = sub.sort_values("ts", ascending=True).reset_index(drop=True)
    sub["id"] = range(1, len(sub) + 1)
    mu = sub["compound"].mean()
    sigma = sub["compound"].std(ddof=0) if len(sub) > 1 else 0

    fig = go.Figure()

    # --- ±1σ band (vàng rất nhạt, dùng neutral_light) ---
    upper, lower = mu + sigma, mu - sigma
    fig.add_trace(go.Scatter(
        x=sub["id"], y=[upper]*len(sub),
        mode="lines", line=dict(width=0),
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=sub["id"], y=[lower]*len(sub),
        mode="lines", line=dict(width=0),
        fill="tonexty",
        fillcolor=_COLOR_SCHEME["neutral_light"],
        name="±1σ band",
        showlegend=True
    ))

    # --- Line chính (teal nhạt hơn so với score) ---
    fig.add_trace(go.Scatter(
        x=sub["id"], y=sub["compound"],
        mode="lines",
        name="Trend line",
        line=dict(color=_COLOR_SCHEME["score_light"], width=2.8)
    ))

    # --- Markers (RdYlGn để phản ánh sentiment) ---
    fig.add_trace(go.Scatter(
        x=sub["id"], y=sub["compound"],
        mode="markers",
        name="News Sentiment",
        marker=dict(
            size=9,
            color=sub["compound"],
            colorscale="RdYlGn",
            cmin=-1, cmax=1,
            showscale=True,
            colorbar=dict(title="Compound<br>score"),
            opacity=0.95
        ),
        hovertemplate=(
            "News #%{x}<br>"
            "Score: %{y:.2f}<br>"
            "Time: %{customdata[0]}<br>"
            "<b>%{customdata[1]}</b><extra></extra>"
        ),
        customdata=np.stack([
            sub["ts"].astype(str),
            sub["title"].fillna("")
        ], axis=-1)
    ))

    # --- Đường tham chiếu (neutral & avg) ---
    fig.add_hline(
        y=0,
        line=dict(color=_COLOR_SCHEME["neutral"], dash="dash", width=2),
        annotation_text="Neutral",
        annotation_position="bottom right"
    )
    fig.add_hline(
        y=mu,
        line=dict(color=_COLOR_SCHEME["positive"], dash="dot", width=2),
        annotation_text=f"Avg {mu:.2f}",
        annotation_position="top right"
    )

    # --- Layout tổng thể ---
    fig.update_layout(
        title=dict(
            text=f"Sentiment Analysis of {ticker} News Headlines (VADER)",
            font=dict(size=15, color=_COLOR_SCHEME["score"]),
            x=0.5, xanchor="center"
        ),
        xaxis=dict(
            title="News Number (Chronological Order)",
            title_font=dict(size=12),
            tickfont=dict(size=12),
            automargin=True,
            showgrid=True,
            gridcolor=_COLOR_SCHEME["grid"]
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=_COLOR_SCHEME["grid"]
        ),
        height=460,
        margin=dict(l=50, r=40, t=60, b=50),
        font=dict(family="Inter, Arial, sans-serif", size=12, color="#111827"),
        paper_bgcolor=_COLOR_SCHEME["bg"],
        plot_bgcolor=_COLOR_SCHEME["bg"],
        showlegend=False
    )

    return _to_html(fig)
# (2) Sentiment Breadth

def chart_sentiment_breadth(df: pd.DataFrame, ticker: str):
    sub = df[df["ticker"] == ticker].copy()
    if sub.empty:
        return None

    sub["ts"] = pd.to_datetime(sub["ts"], errors="coerce")
    sub = sub.dropna(subset=["ts", "compound"])
    sub["date"] = sub["ts"].dt.date

    sub["pos"] = (sub["compound"] > 0.05).astype(int)
    sub["neg"] = (sub["compound"] < -0.05).astype(int)

    g = (sub.groupby("date")
            .agg(total=("compound","size"),
                 pos=("pos","sum"),
                 neg=("neg","sum"))
            .reset_index())
    if g.empty or (g["total"] == 0).all():
        return None

    g["pos_pct"] = g["pos"] / g["total"] * 100
    g["neg_pct"] = g["neg"] / g["total"] * 100
    g["breadth"] = g["pos_pct"] - g["neg_pct"]

    # chuẩn bị area fill: dương (xanh), âm (đỏ)
    pos_y = np.where(g["breadth"] > 0, g["breadth"], 0)
    neg_y = np.where(g["breadth"] < 0, g["breadth"], 0)

    fig = go.Figure()

    # Area dương (xanh lá nhạt)
    fig.add_trace(go.Scatter(
        x=g["date"], y=pos_y,
        mode="lines", line=dict(width=0),
        fill="tozeroy",
        fillcolor="rgba(110,203,99,0.15)",  # _COLOR_SCHEME["positive"] nhạt
        hoverinfo="skip",
        showlegend=False
    ))
    # Area âm (đỏ nhạt)
    fig.add_trace(go.Scatter(
        x=g["date"], y=neg_y,
        mode="lines", line=dict(width=0),
        fill="tozeroy",
        fillcolor="rgba(235,83,83,0.15)",  # _COLOR_SCHEME["negative"] nhạt
        hoverinfo="skip",
        showlegend=False
    ))

    # Line chính: dùng score nhưng nhạt hơn (fallback về score nếu không có score_light)
    score_line_color = _COLOR_SCHEME.get("score_light", _COLOR_SCHEME["score"])
    fig.add_trace(go.Scatter(
        x=g["date"], y=g["breadth"],
        mode="lines",
        line=dict(color=score_line_color, width=2.6),
        name="Sentiment Breadth"
    ))

    # Markers màu theo breadth với dải RdYlGn (giống biểu đồ 1)
    fig.add_trace(go.Scatter(
        x=g["date"], y=g["breadth"],
        mode="markers",
        marker=dict(
            size=6,
            color=g["breadth"],
            colorscale="RdYlGn",
            cmin=-100, cmax=100,
            showscale=False,
            opacity=0.9
        ),
        hovertemplate="Date: %{x}<br>Breadth: %{y:+.1f}%<extra></extra>",
        name="",
        showlegend=False
    ))

    # Đường Neutral = 0 (vàng pastel)
    fig.add_hline(
        y=0,
        line=dict(color=_COLOR_SCHEME["neutral"], dash="dot"),
        annotation_text="Neutral",
        annotation_position="top right"
    )

    fig.update_layout(
        title=dict(
            text=f"Sentiment Breadth (Positive % − Negative %) — {ticker}",
            font=dict(size=15, color=_COLOR_SCHEME["score"]),
            x=0.5, xanchor="center"
        ),
        xaxis=dict(
            title="Date",
            type="category",
            tickfont=dict(size=12),
            title_font=dict(size=12),
            showgrid=True, gridcolor=_COLOR_SCHEME["grid"]
        ),
        yaxis=dict(
            title="Breadth (%)",
            ticksuffix="%",
            showgrid=True, gridcolor=_COLOR_SCHEME["grid"]
        ),
        height=540,
        margin=dict(l=50, r=40, t=60, b=50),
        paper_bgcolor=_COLOR_SCHEME["bg"],
        plot_bgcolor=_COLOR_SCHEME["bg"],
        font=dict(family="Inter, Arial, sans-serif", size=12, color="#111827"),
        showlegend=False
    )

    return _to_html(fig)



def chart_daily_stacked(df: pd.DataFrame, ticker: str):
    sub = df[df["ticker"] == ticker].copy()
    if sub.empty:
        return None

    sub["date"] = pd.to_datetime(sub["ts"]).dt.date
    sub["neg"] = (sub["compound"] < -0.05).astype(int)
    sub["neu"] = ((sub["compound"] >= -0.05) & (sub["compound"] <= 0.05)).astype(int)
    sub["pos"] = (sub["compound"] > 0.05).astype(int)

    g = sub.groupby("date")[["neg","neu","pos"]].sum().reset_index().sort_values("date")
    g["avg_score"] = sub.groupby("date")["compound"].mean().values

    fig = go.Figure()

    # Stacked bars
    fig.add_bar(x=g["date"], y=g["neg"], name="Negative", marker_color=_COLOR_SCHEME["negative"])
    fig.add_bar(x=g["date"], y=g["neu"], name="Neutral",  marker_color=_COLOR_SCHEME["neutral"])
    fig.add_bar(x=g["date"], y=g["pos"], name="Positive", marker_color=_COLOR_SCHEME["positive"])

    # Sentiment score line
    fig.add_scatter(
        x=g["date"], y=g["avg_score"], name="Sentiment score",
        mode="lines+markers",
        line=dict(color=_COLOR_SCHEME["score"], width=2.5),
        marker=dict(size=7, color=_COLOR_SCHEME["score"], line=dict(width=1, color="white")),
        yaxis="y2"
    )

    # Dual y-axis (bar left, line right)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Date", type="category"),
        yaxis=dict(title="News Count"),
        yaxis2=dict(title="Avg Sentiment", overlaying="y", side="right", range=[-1, 1]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=520,
        margin=dict(l=50, r=50, t=60, b=60),
        template="plotly_white",
        paper_bgcolor=_COLOR_SCHEME["bg"],
        plot_bgcolor=_COLOR_SCHEME["bg"],
        font=dict(family="Inter, system-ui", size=13, color="#111827")
    )

    return _to_html(fig)



# (3) chart_source_weighted_bar

WEIGHTS = Config.PUBLISHER_WEIGHTS

def chart_source_weighted_bar(df: pd.DataFrame, ticker: str):
    sub = df[df["ticker"] == ticker].copy()
    if sub.empty:
        return None

    sub = _ensure_publisher_col(sub)
    sub["publisher"] = sub["publisher"].fillna("unknown").str.lower()
    sub["w"] = sub["publisher"].map(WEIGHTS).fillna(0.5)  # default 0.5
    sub["w_score"] = sub["compound"] * sub["w"]

    agg = (sub.groupby("publisher", as_index=False)
             .agg(weighted_mean=("w_score","mean"),
                  n=("w","size"))
             .sort_values("weighted_mean", ascending=False))
    if agg.empty:
        return None

    # dùng dải màu giống biểu đồ 1: RdYlGn (-1 -> +1)
    fig = px.bar(
        agg,
        x="publisher", y="weighted_mean",
        color="weighted_mean",
        color_continuous_scale="RdYlGn",
        range_color=(-1, 1),
        hover_data={"n": True, "publisher": False, "weighted_mean": ":.2f"},
        template="plotly_white",
        labels={"publisher": "", "weighted_mean": "Weighted mean (w × compound)"},
    )

    n = len(agg)
    fig.update_traces(
        marker_line_color="white", marker_line_width=0.6,
        customdata=np.stack([agg["n"]], axis=-1),
        hovertemplate="Source: %{x}<br>Weighted mean: %{y:.2f}<br>Count: %{customdata[0]}<extra></extra>"
    )

    fig.update_layout(
        title=dict(
            text=f"Source-weighted Sentiment — {ticker}",
            font=dict(size=15, color=_COLOR_SCHEME["score"]),
            x=0.5, xanchor="center"
        ),
        height=520,
        margin=dict(l=50, r=40, t=60, b=80),
        showlegend=False,
        paper_bgcolor=_COLOR_SCHEME["bg"],
        plot_bgcolor=_COLOR_SCHEME["bg"],
        bargap=0.25,
        coloraxis_colorbar=dict(title="score")  # hiện colorbar như chart 1
    )
    fig.update_xaxes(
        type="category", tickangle=-30, automargin=True,
        range=[-0.5, n-0.5],
        showgrid=True, gridcolor=_COLOR_SCHEME["grid"]
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=_COLOR_SCHEME["grid"],
        zeroline=True, zerolinecolor=_COLOR_SCHEME["grid"]
    )

    return _to_html(fig)


# (4) Distribution histogram
def chart_distribution_hist(df: pd.DataFrame, ticker: str):
    sub = df[df["ticker"] == ticker]["compound"].dropna()
    if sub.empty:
        return None

    mu = float(sub.mean())

    # Histogram cơ bản
    fig = px.histogram(
        sub,
        nbins=15,
        template="plotly_white",
        color_discrete_sequence=[_COLOR_SCHEME["negative"]],  # chỉ 1 màu: tone đỏ mềm
        opacity=0.85
    )

    # Thêm đường trung bình (avg line)
    fig.add_vline(
        x=mu,
        line_dash="dash",
        line_color=_COLOR_SCHEME["score"],  # line teal để nổi bật
        annotation_text=f"Avg {mu:.2f}",
        annotation_position="top right"
    )

    # Layout & style tổng thể
    fig.update_traces(
        hovertemplate="Count: %{y}<extra></extra>",
        marker_line_color="white",
        marker_line_width=0.5
    )

    fig.update_xaxes(
        title="Sentiment Polarity",
        showgrid=True,
        gridcolor=_COLOR_SCHEME["grid"]
    )
    fig.update_yaxes(
        title="Frequency",
        showgrid=True,
        gridcolor=_COLOR_SCHEME["grid"]
    )

    fig.update_layout(
        title=dict(
            text=f"Distribution of Sentiment Scores — {ticker}",
            font=dict(size=15, color=_COLOR_SCHEME["score"]),
            x=0.5, xanchor="center"
        ),
        height=400,
        margin=dict(l=50, r=40, t=60, b=50),
        font=dict(family="Inter, Arial, sans-serif", size=13, color="#111827"),
        paper_bgcolor=_COLOR_SCHEME["bg"],
        plot_bgcolor=_COLOR_SCHEME["bg"],
        showlegend=False
    )

    return _to_html(fig)

# (5) Pie composition
def chart_pie_composition(df: pd.DataFrame, ticker: str):
    s = df[df["ticker"] == ticker]["compound"].dropna()
    if s.empty:
        return None

    neg = int((s < -0.05).sum())
    neu = int(((s >= -0.05) & (s <= 0.05)).sum())
    pos = int((s > 0.05).sum())

    pie_df = pd.DataFrame({
        "label": ["Negative", "Neutral", "Positive"],
        "value": [neg, neu, pos]
    })

    fig = px.pie(
        pie_df,
        names="label",
        values="value",
        hole=0.35,  # donut nhẹ
        template="plotly_white",
        color="label",
        color_discrete_map={
            "Negative": _COLOR_SCHEME["negative"],
            "Neutral":  _COLOR_SCHEME["neutral"],
            "Positive": _COLOR_SCHEME["positive"]
        }
    )

    fig.update_traces(
        textinfo="label+percent",
        textfont=dict(size=12, color="#111827"),
        pull=[0.02, 0.02, 0.02],
        hovertemplate="%{label}: %{percent:.1%}<extra></extra>"
    )

    fig.update_layout(
        title=dict(
            text=f"Sentiment Composition — {ticker}",
            font=dict(size=15, color=_COLOR_SCHEME["score"]),
            x=0.5, xanchor="center"
        ),
        height=420,
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=False,
        paper_bgcolor=_COLOR_SCHEME["bg"],
        plot_bgcolor=_COLOR_SCHEME["bg"]
    )

    return _to_html(fig)

# --- WORD CLOUD (Matplotlib) ---
_STOP_BASIC = {
  "the","and","or","to","for","of","by","with","on","in","at",
  "a","an","is","are","from","as","be","vs","today","latest"
}
def _cut_pub(t): t = t or ""; return t.rsplit(" - ",1)[0] if " - " in t else t

def _normalize_tokens(titles):
    import re
    from collections import Counter

    # 1️⃣ Ghép và lọc ký tự đặc biệt
    text = re.sub(r"[^\w\s']", " ", " ".join(titles))

    # 2️⃣ Tách từ thô
    raw_tokens = text.split()

    # 3️⃣ Làm sạch & lọc stopwords
    tokens = []
    for w in raw_tokens:
        if not w or len(w) <= 2 or w.isdigit():
            continue
        wl = w.lower()
        if wl in _STOP_BASIC: 
            continue
        if w.endswith("'s") or w.endswith("'S"):
            w = w[:-2]
            wl = wl[:-2]
        tokens.append((wl, w))   # (chữ thường để đếm, bản gốc để hiển thị)

    if not tokens:
        return []

    # 4️⃣ Đếm theo chữ thường (gộp "apple" và "Apple")
    counts = Counter([wl for wl, _ in tokens])

    # 5️⃣ Lấy phiên bản hiển thị: chọn dạng gốc xuất hiện nhiều nhất (viết hoa nếu có)
    rep_map = {}
    for wl, _ in tokens:
        if wl not in rep_map:
            # lấy ví dụ đầu tiên có chữ in hoa nếu có
            cands = [orig for low, orig in tokens if low == wl]
            rep = next((c for c in cands if any(ch.isupper() for ch in c)), cands[0])
            rep_map[wl] = rep

    # 6️⃣ Trả về dict: { "Apple": tần suất }
    merged = {rep_map[k]: v for k, v in counts.items()}
    return merged



from matplotlib import cm, colors as mcolors
from collections import Counter

from wordcloud import WordCloud
from collections import Counter
import io, base64, matplotlib.pyplot as plt

def chart_wordcloud(df, ticker):
    sub = df[df["ticker"] == ticker]
    if sub.empty:
        return None

    titles = [_cut_pub(x) for x in sub["title"].fillna("").tolist()]
    toks = _normalize_tokens(titles)
    if not toks:
        return None

    freq_dict = toks 

    # 🎨 chỉ cần colormap = "YlOrBr" hoặc "cividis", "autumn", "Wistia"...
    wc = WordCloud(
        width=1000,
        height=700,
        background_color="white",
        stopwords=_STOP_BASIC,
        prefer_horizontal=0.95,
        max_words=200,
        random_state=42,
        collocations=False,
        colormap="Blues",   # <── vàng-nâu dịu, đọc rõ
        scale=2,
        relative_scaling=0.25
    ).generate_from_frequencies(freq_dict)

    plt.figure(figsize=(9,7), dpi=160)
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.title(f"Word Cloud for {ticker}", fontsize=15)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.2)
    plt.close(); buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def chart_wordcount(df, ticker):
    sub = df[df["ticker"] == ticker]
    if sub.empty:
        return None

    titles = [_cut_pub(x) for x in sub["title"].fillna("").tolist()]
    toks = _normalize_tokens(titles)
    if not toks:
        return None

    from collections import Counter
    import pandas as pd, plotly.express as px

    top_k = 20
    word_df = (
        pd.DataFrame(Counter(toks).most_common(top_k), columns=["word", "count"])
        .sort_values("count", ascending=True)
    )

    # Dải màu xanh lam đậm–nhạt (đúng 1 tone blue)
    one_blue_scale = [
        [0.0, "rgba(37, 99, 235, 0.15)"],   # rất nhạt
        [0.5, "rgba(37, 99, 235, 0.55)"],   # trung bình
        [1.0, "rgba(37, 99, 235, 1.00)"],   # đậm
    ]

    fig = px.bar(
        word_df,
        x="count",
        y="word",
        orientation="h",
        text="count",
        color="count",
        color_continuous_scale="Blues",
        range_color=(word_df["count"].min(), word_df["count"].max()),
        labels={"count": "Count", "word": "Word"},
        template="plotly_white"
    )

    fig.update_traces(
        hovertemplate="Word: %{y}<br>Count: %{x}<extra></extra>",
        textposition="outside",
        cliponaxis=False,
        marker_line_color="white",
        marker_line_width=0.6
    )

    fig.update_layout(
        title=dict(
            text=f"Top {top_k} Most Frequent Words in {ticker} Headlines",
            font=dict(size=15, color=_COLOR_SCHEME["score"]),
            x=0.5,
            xanchor="center"
        ),
        height=520,
        margin=dict(l=110, r=40, t=60, b=50),
        bargap=0.18,
        coloraxis_showscale=False,
        paper_bgcolor=_COLOR_SCHEME["bg"],
        plot_bgcolor=_COLOR_SCHEME["bg"],
        font=dict(family="Inter, Arial, sans-serif", size=12, color="#111827")
    )

    fig.update_yaxes(title="", showgrid=False, categoryorder="total ascending")
    fig.update_xaxes(title="Count", showgrid=True, gridcolor=_COLOR_SCHEME["grid"], zeroline=False)

    return _to_html(fig)
