"""
news.py — Kafka Producer + PySpark Pipeline cho News Ingestion
==============================================================
Kiến trúc:
  1. fetch_*()         → Thu thập tin thô từ Finviz / Google RSS
  2. _spark_clean()    → Làm sạch bằng PySpark DataFrame pipeline
  3. _produce_to_kafka() → Đẩy từng bản ghi lên Kafka topic (dùng kafka-python)
  4. fetch_news_multi() → Public API (giữ nguyên interface cũ):
       - Nếu Kafka có thể kết nối  → produce & consume qua topic
       - Fallback tự động          → trả về kết quả locally nếu Kafka offline

Ghi chú thư viện Kafka:
  - Dùng kafka-python (pure Python, hoạt động trên Windows)
  - Trên EC2 Linux: cũng hoạt động tốt, hoặc có thể dùng confluent-kafka
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta, date
from typing import Any
from urllib.parse import urlparse, quote

import requests
import feedparser

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Kafka config (khớp với EC2 instance của nhóm)
# ─────────────────────────────────────────────
KAFKA_BOOTSTRAP = "3.24.16.55:9092"   # EC2 public IP  ← thay nếu đổi
KAFKA_TOPIC_RAW = "financial_news_raw"
KAFKA_TOPIC_CLEAN = "financial_news_clean"
KAFKA_TIMEOUT_MS = 5_000              # 5 s để phát hiện offline nhanh

# ─────────────────────────────────────────────
# Trusted sources
# ─────────────────────────────────────────────
DEFAULT_TRUSTED_PUBLISHERS: set[str] = {
    "reuters", "bloomberg", "wsj", "ft", "cnbc", "marketwatch",
    "barrons", "ap", "theeconomist", "yahoofinance",
    "investorsbusinessdaily", "forbes", "financialtimes",
    "bbc", "cnn", "businessinsider",
}


# ═══════════════════════════════════════════════════════════════════
#  SECTION 1 — Helper utilities (giữ nguyên logic cũ)
# ═══════════════════════════════════════════════════════════════════

def _source_from_url(href: str) -> str:
    try:
        netloc = urlparse(href).netloc.lower().replace("www.", "")
        parts = [p for p in netloc.split(".") if p]
        if not parts:
            return "source"
        if len(parts) >= 3 and parts[-2] in {"co", "com"}:
            core = parts[-3]
        else:
            core = parts[-2] if len(parts) >= 2 else parts[0]
        if "yahoo" in parts:
            return "yahoo"
        return re.sub(r"[^a-z]", "", core)
    except Exception:
        return "source"


def _normalize_publisher(source_slug: str | None, title: str | None = None) -> str:
    s = (source_slug or "").strip().lower()
    if title and " - " in title:
        tail = title.rsplit(" - ", 1)[-1].strip().lower()
        tail = re.sub(r"[^a-z]", "", tail)
        if tail:
            s = tail
    s = re.sub(r"[^a-z]", "", s)
    aliases = {
        "thewallstreetjournal": "wsj", "wallstreetjournal": "wsj",
        "financialtimes": "ft", "ft": "ft",
        "yahoofinance": "yahoofinance", "yahoo": "yahoofinance",
        "apnews": "ap", "associatedpress": "ap",
        "reuters": "reuters", "bloomberg": "bloomberg",
        "cnbc": "cnbc", "marketwatch": "marketwatch",
        "barrons": "barrons", "economist": "theeconomist",
        "theeconomist": "theeconomist",
        "investorsbusinessdaily": "investorsbusinessdaily",
        "forbes": "forbes", "bbc": "bbc",
        "cnn": "cnn", "businessinsider": "businessinsider",
    }
    return aliases.get(s, s or "source")


def _norm_title(title: str) -> str:
    t = (title or "").strip().casefold()
    if " - " in t:
        t = t.rsplit(" - ", 1)[0]
    t = re.sub(r"\(.*?\)|\[.*?\]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _parse_finviz_time(raw: str, now: datetime | None = None) -> datetime | None:
    now = now or datetime.now()
    s = raw.strip().replace("\xa0", " ")
    for fmt in ("%b-%d-%y %H:%M", "%b-%d-%y %I:%M%p", "%b-%d-%y %I:%M %p"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    for label, offset in [("today", 0), ("yesterday", -1)]:
        if s.lower().startswith(label):
            tail = s[len(label):].strip()
            for f in ("%I:%M%p", "%H:%M"):
                try:
                    t = datetime.strptime(tail, f).time()
                    day = now + timedelta(days=offset)
                    return datetime(day.year, day.month, day.day, t.hour, t.minute)
                except Exception:
                    continue
    return None


def _in_range(ts: datetime, start_date: date | None, end_date: date | None) -> bool:
    d = ts.date()
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True


def _is_trusted(publisher: str | None, trusted_publishers: set[str] | None) -> bool:
    if not trusted_publishers:
        return True
    p = re.sub(r"[^a-z]", "", (publisher or "").strip().lower())
    return p in trusted_publishers


# ═══════════════════════════════════════════════════════════════════
#  SECTION 2 — Raw scrapers (Finviz + Google RSS)
# ═══════════════════════════════════════════════════════════════════

def fetch_finviz_news_one(
    ticker: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 120,
    timeout: int = 20,
    trusted_only: bool = True,
    trusted_publishers: set[str] | None = DEFAULT_TRUSTED_PUBLISHERS,
) -> list[dict]:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return []

    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        html = requests.get(url, headers=headers, timeout=timeout).text
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find(id="news-table") or soup.select_one("table.fullview-news-outer")
    if not table:
        return []

    out: list[dict] = []
    now = datetime.now()
    for tr in table.find_all("tr"):
        a = tr.find("a")
        if not a:
            continue
        href = a.get("href")
        title = a.get_text(strip=True)
        tcell = tr.find("td", class_="nn-date") or tr.find("td")
        if not tcell:
            continue
        ts = _parse_finviz_time(tcell.get_text(" ", strip=True), now)
        if ts is None or not _in_range(ts, start_date, end_date):
            continue
        src = _source_from_url(href)
        publisher = _normalize_publisher(src, title)
        if trusted_only and not _is_trusted(publisher, trusted_publishers):
            continue
        out.append({
            "ticker": ticker.upper(), "ts": ts,
            "date": ts.date(), "time": ts.strftime("%H:%M"),
            "title": title, "url": href,
            "source": src, "publisher": publisher,
        })
        if len(out) >= limit:
            break
    out.sort(key=lambda x: x["ts"])
    return out


def _google_rss_url_raw(q: str, lang: str = "en-US", gl: str = "US") -> str:
    return (
        f"https://news.google.com/rss/search?q={quote(q)}"
        f"&hl={lang}&gl={gl}&ceid={gl}:{lang.split('-')[0]}"
    )


def _fetch_google_chunk(
    ticker: str,
    d0: date,
    d1: date,
    per_chunk_limit: int = 120,
    trusted_only: bool = True,
    trusted_publishers: set[str] | None = DEFAULT_TRUSTED_PUBLISHERS,
) -> list[dict]:
    after_str = d0.isoformat()
    before_str = d1.isoformat()
    q = f"{ticker} stock after:{after_str} before:{before_str}"
    url = _google_rss_url_raw(q)
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []

    out: list[dict] = []
    for e in feed.entries[: per_chunk_limit * 2]:
        if getattr(e, "published_parsed", None):
            ts = datetime(*e.published_parsed[:6])
        else:
            ts = datetime.utcnow()
        if not (d0 <= ts.date() < d1):
            continue
        href = getattr(e, "link", "") or ""
        title = (getattr(e, "title", "") or "").strip()
        if not title or not href:
            continue
        src = _source_from_url(href)
        publisher = _normalize_publisher(src, title)
        if trusted_only and not _is_trusted(publisher, trusted_publishers):
            continue
        out.append({
            "ticker": ticker.upper(), "ts": ts,
            "date": ts.date(), "time": ts.strftime("%H:%M"),
            "title": title, "url": href,
            "source": src, "publisher": publisher,
        })
        if len(out) >= per_chunk_limit:
            break
    out.sort(key=lambda x: x["ts"])
    return out


def fetch_google_rss_range_chunked(
    ticker: str,
    start_date: date | None,
    end_date: date | None,
    limit: int = 365,
    chunk_days: int = 7,
    trusted_only: bool = True,
    trusted_publishers: set[str] | None = DEFAULT_TRUSTED_PUBLISHERS,
) -> list[dict]:
    if start_date is None or end_date is None:
        url = _google_rss_url_raw(f"{ticker} stock when:365d")
        try:
            feed = feedparser.parse(url)
        except Exception:
            return []
        out: list[dict] = []
        for e in feed.entries[:limit * 2]:
            if getattr(e, "published_parsed", None):
                ts = datetime(*e.published_parsed[:6])
            else:
                ts = datetime.utcnow()
            href = getattr(e, "link", "") or ""
            title = (getattr(e, "title", "") or "").strip()
            if not title or not href:
                continue
            src = _source_from_url(href)
            publisher = _normalize_publisher(src, title)
            if trusted_only and not _is_trusted(publisher, trusted_publishers):
                continue
            out.append({
                "ticker": ticker.upper(), "ts": ts,
                "date": ts.date(), "time": ts.strftime("%H:%M"),
                "title": title, "url": href,
                "source": src, "publisher": publisher,
            })
            if len(out) >= limit:
                break
        out.sort(key=lambda x: x["ts"])
        return out

    rows: list[dict] = []
    d0 = start_date
    while d0 <= end_date:
        d1 = min(d0 + timedelta(days=chunk_days), end_date + timedelta(days=1))
        rows.extend(_fetch_google_chunk(ticker, d0, d1, trusted_only=trusted_only,
                                        trusted_publishers=trusted_publishers))
        d0 = d1
    seen = set()
    uniq = []
    for r in rows:
        key = (_norm_title(r.get("title", "")), (r.get("url", "") or "").split("?")[0])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    uniq.sort(key=lambda x: x["ts"])
    return uniq[:limit]


# ═══════════════════════════════════════════════════════════════════
#  SECTION 3 — PySpark cleaning pipeline
# ═══════════════════════════════════════════════════════════════════

def _spark_clean(rows: list[dict]) -> list[dict]:
    """
    Dùng PySpark DataFrame API để bóc tách & làm sạch dữ liệu tin tức:
      - Bỏ bản ghi thiếu title / url
      - Chuẩn hoá whitespace trong title
      - Loại bỏ clickbait patterns (ALL CAPS ngắn, chỉ ký tự đặc biệt…)
      - Dedup theo (ticker, norm_title, url_stem)
      - Sắp xếp theo ticker → ts
    Trả về list[dict] đã sạch (serialize-safe, datetime → str).
    """
    if not rows:
        return []

    try:
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
        from pyspark.sql.types import StringType

        spark = (
            SparkSession.builder
            .appName("NewsCleaningPipeline")
            .master("local[*]")
            # Tắt log rác của Spark
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "4")
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("ERROR")

        # PySpark không serialize datetime trực tiếp → chuyển về string
        serial_rows = []
        for r in rows:
            new = dict(r)
            if isinstance(new.get("ts"), datetime):
                new["ts"] = new["ts"].isoformat()
            if isinstance(new.get("date"), date):
                new["date"] = str(new["date"])
            serial_rows.append(new)

        df = spark.createDataFrame(serial_rows)

        # --- Bước 1: bỏ null title / url ---
        df = df.filter(
            F.col("title").isNotNull() & (F.trim(F.col("title")) != "") &
            F.col("url").isNotNull()   & (F.trim(F.col("url"))   != "")
        )

        # --- Bước 2: chuẩn hoá title ---
        # Xoá nhiều khoảng trắng liên tiếp
        df = df.withColumn("title", F.regexp_replace(F.col("title"), r"\s+", " "))
        # Xoá phần " - Publisher" ở cuối tiêu đề (để tránh nhiễu NLP)
        df = df.withColumn("title", F.regexp_replace(F.col("title"), r"\s+-\s+\w[\w\s]{0,40}$", ""))
        df = df.withColumn("title", F.trim(F.col("title")))

        # --- Bước 3: lọc clickbait / rác ---
        # Bỏ bài ngắn hơn 15 ký tự sau trim
        df = df.filter(F.length(F.col("title")) >= 15)

        # --- Bước 4: tạo khoá dedup ---
        # url_stem = URL bỏ query string
        df = df.withColumn(
            "url_stem",
            F.regexp_replace(F.col("url"), r"\?.*$", "")
        )
        # norm_title_key = title casefold, bỏ non-alpha
        df = df.withColumn(
            "norm_title_key",
            F.lower(F.regexp_replace(F.col("title"), r"[^a-zA-Z0-9\s]", ""))
        )

        # --- Bước 5: dedup theo (ticker, norm_title_key, url_stem) ---
        from pyspark.sql.window import Window
        w = Window.partitionBy("ticker", "norm_title_key", "url_stem").orderBy("ts")
        df = df.withColumn("_rn", F.row_number().over(w)).filter(F.col("_rn") == 1)

        # --- Bước 6: sắp xếp ---
        df = df.orderBy("ticker", "ts")

        # --- Thu kết quả ---
        cleaned = df.drop("url_stem", "norm_title_key", "_rn").toPandas().to_dict("records")
        spark.stop()
        log.info("[PySpark] Pipeline hoàn tất: %d/%d bản ghi giữ lại.", len(cleaned), len(rows))
        return cleaned

    except Exception as exc:
        log.warning("[PySpark] Pipeline lỗi (%s) — fallback sang Python dedup.", exc)
        # Fallback Python thuần nếu Spark không khởi được
        return _python_dedup(rows)


def _python_dedup(rows: list[dict]) -> list[dict]:
    """Fallback dedup thuần Python khi Spark không khả dụng."""
    seen: set[tuple] = set()
    out = []
    for r in rows:
        title_clean = re.sub(r"\s+", " ", (r.get("title") or "")).strip()
        url_stem = (r.get("url") or "").split("?")[0]
        key = (_norm_title(title_clean), url_stem)
        if key in seen:
            continue
        seen.add(key)
        r = dict(r)
        r["title"] = title_clean
        out.append(r)
    out.sort(key=lambda x: (x.get("ticker", ""), x.get("ts", "")))
    return out


# ═══════════════════════════════════════════════════════════════════
#  SECTION 4 — Kafka Producer / Consumer helpers
# ═══════════════════════════════════════════════════════════════════

def _kafka_available() -> bool:
    """Kiểm tra nhanh Kafka có online không (TCP connect)."""
    import socket
    host, port_str = KAFKA_BOOTSTRAP.split(":")
    port = int(port_str)
    try:
        with socket.create_connection((host, port), timeout=KAFKA_TIMEOUT_MS / 1000):
            return True
    except Exception:
        return False


def _json_serial(obj: Any) -> str:
    """JSON default serializer cho datetime / date."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _produce_to_kafka(rows: list[dict], ticker: str) -> bool:
    """
    Đẩy danh sách bản ghi tin tức lên Kafka topic RAW.
    Dùng kafka-python (pure Python, hoạt động trên Windows + EC2 Linux).
    Trả về True nếu thành công, False nếu lỗi.
    """
    try:
        from kafka import KafkaProducer
        from kafka.errors import KafkaError as KafkaLibError

        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            request_timeout_ms=KAFKA_TIMEOUT_MS,
            api_version_auto_timeout_ms=KAFKA_TIMEOUT_MS,
            value_serializer=lambda v: json.dumps(v, default=_json_serial, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
        )

        delivered = 0
        futures = []
        for row in rows:
            future = producer.send(KAFKA_TOPIC_RAW, key=ticker, value=row)
            futures.append(future)

        # Flush và kiểm tra
        producer.flush(timeout=15)
        for f in futures:
            try:
                f.get(timeout=5)
                delivered += 1
            except KafkaLibError as e:
                log.warning("[Kafka] Delivery error: %s", e)

        producer.close()
        log.info("[Kafka] Produced %d/%d messages for %s → topic '%s'",
                 delivered, len(rows), ticker, KAFKA_TOPIC_RAW)
        return delivered > 0

    except ImportError:
        log.warning("[Kafka] kafka-python chưa được cài. Bỏ qua produce.")
        return False
    except Exception as exc:
        log.warning("[Kafka] Produce lỗi: %s", exc)
        return False


def _consume_from_kafka(ticker: str, expected: int, timeout_sec: int = 15) -> list[dict]:
    """
    Consume tin tức từ Kafka topic RAW cho ticker cụ thể.
    Dùng kafka-python. Trả về list[dict] hoặc [] nếu lỗi.
    """
    try:
        from kafka import KafkaConsumer
        from kafka import TopicPartition

        consumer = KafkaConsumer(
            KAFKA_TOPIC_RAW,
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            group_id=f"news_consumer_{ticker}_{int(time.time())}",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            consumer_timeout_ms=timeout_sec * 1000,
            request_timeout_ms=KAFKA_TIMEOUT_MS + 5000,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )

        collected: list[dict] = []
        deadline = time.time() + timeout_sec

        for msg in consumer:
            if time.time() > deadline or len(collected) >= expected:
                break
            try:
                row = msg.value
                if isinstance(row, dict) and row.get("ticker", "").upper() == ticker.upper():
                    collected.append(row)
            except Exception:
                continue

        consumer.close()
        log.info("[Kafka] Consumed %d messages for %s", len(collected), ticker)
        return collected

    except ImportError:
        log.warning("[Kafka] kafka-python chưa được cài. Bỏ qua consume.")
        return []
    except Exception as exc:
        log.warning("[Kafka] Consume lỗi: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════
#  SECTION 5 — Public API  (interface giữ nguyên cho routes/main.py)
# ═══════════════════════════════════════════════════════════════════

def fetch_news_multi(
    tickers: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 150,
    use_finviz: bool = False,
    chunk_google: bool = True,
    trusted_only: bool = True,
    trusted_publishers: set[str] | None = DEFAULT_TRUSTED_PUBLISHERS,
    pause_sec: float = 0.1,
) -> list[dict]:
    """
    Hàm Public — giữ nguyên signature để không cần đổi code caller.

    Luồng mới:
      [Scrape raw news]
          ↓
      [PySpark clean pipeline]
          ↓
      [Kafka produce → consume]  ← nếu Kafka online
          hoặc                   ← nếu offline → dùng kết quả Spark trực tiếp
      [Return list[dict]]
    """
    kafka_online = _kafka_available()
    if kafka_online:
        log.info("[Kafka] Broker %s ONLINE — sẽ stream qua Kafka.", KAFKA_BOOTSTRAP)
    else:
        log.warning("[Kafka] Broker %s OFFLINE — chạy local pipeline (Spark only).", KAFKA_BOOTSTRAP)

    final_rows: list[dict] = []

    for t in tickers:
        t = t.upper()
        batch: list[dict] = []

        # ── 1. Thu thập tin thô ──
        if use_finviz:
            try:
                batch.extend(fetch_finviz_news_one(
                    t, start_date, end_date, limit=min(120, limit),
                    trusted_only=trusted_only, trusted_publishers=trusted_publishers,
                ))
            except Exception as exc:
                log.warning("[Finviz] Lỗi: %s", exc)

        try:
            if chunk_google:
                batch.extend(fetch_google_rss_range_chunked(
                    t, start_date, end_date, limit=min(365, limit),
                    trusted_only=trusted_only, trusted_publishers=trusted_publishers,
                ))
            else:
                # simple fetch
                url = _google_rss_url_raw(f"{t} stock when:365d")
                feed = feedparser.parse(url)
                for e in feed.entries[:limit * 2]:
                    if getattr(e, "published_parsed", None):
                        ts = datetime(*e.published_parsed[:6])
                    else:
                        ts = datetime.utcnow()
                    href = getattr(e, "link", "") or ""
                    title = (getattr(e, "title", "") or "").strip()
                    if not title or not href:
                        continue
                    src = _source_from_url(href)
                    publisher = _normalize_publisher(src, title)
                    if trusted_only and not _is_trusted(publisher, trusted_publishers):
                        continue
                    batch.append({
                        "ticker": t, "ts": ts, "date": ts.date(),
                        "time": ts.strftime("%H:%M"),
                        "title": title, "url": href,
                        "source": src, "publisher": publisher,
                    })
        except Exception as exc:
            log.warning("[GoogleRSS] Lỗi: %s", exc)

        if not batch:
            continue

        # ── 2. PySpark cleaning pipeline ──
        cleaned = _spark_clean(batch)

        if kafka_online:
            # ── 3a. Kafka: produce → consume ──
            ok = _produce_to_kafka(cleaned, t)
            if ok:
                consumed = _consume_from_kafka(t, expected=len(cleaned))
                if consumed:
                    # Restore datetime objects từ ISO string
                    for row in consumed:
                        if isinstance(row.get("ts"), str):
                            try:
                                row["ts"] = datetime.fromisoformat(row["ts"])
                            except Exception:
                                row["ts"] = datetime.utcnow()
                        if isinstance(row.get("date"), str):
                            try:
                                row["date"] = date.fromisoformat(row["date"])
                            except Exception:
                                row["date"] = date.today()
                    final_rows.extend(consumed[:limit])
                    log.info("[Pipeline] %s: %d bản ghi qua Kafka.", t, len(consumed[:limit]))
                    if pause_sec:
                        time.sleep(pause_sec)
                    continue
            # Nếu produce/consume thất bại → dùng kết quả Spark
        
        # ── 3b. Local fallback (Spark result) ──
        for row in cleaned:
            if isinstance(row.get("ts"), str):
                try:
                    row["ts"] = datetime.fromisoformat(row["ts"])
                except Exception:
                    row["ts"] = datetime.utcnow()
            if isinstance(row.get("date"), str):
                try:
                    row["date"] = date.fromisoformat(row["date"])
                except Exception:
                    row["date"] = date.today()

        final_rows.extend(cleaned[:limit])
        log.info("[Pipeline] %s: %d bản ghi (local Spark).", t, len(cleaned[:limit]))

        if pause_sec:
            time.sleep(pause_sec)

    final_rows.sort(key=lambda x: (x.get("ticker", ""), x.get("ts", datetime.min)))
    return final_rows
