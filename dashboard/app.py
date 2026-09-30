"""
Dashboard K4-L3B Day 13 — Monitoring & LLMOps
Hiển thị dạng lưới 2x3 (2 hàng, 3 cột) bao quát đủ 6 panel:
Hàng 1: Latency | Traffic | Errors & Retrieval Success
Hàng 2: Cost | Tokens | Quality Proxy
Chạy: streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

LOG_PATH = Path("data/logs.jsonl")
TIME_RANGE_MINUTES = 60
REFRESH_SECONDS = 30

st.set_page_config(
    page_title="K4-L3B Day 13 Monitoring & LLMOps",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    h3 {
        margin-bottom: 0.2rem !important;
        font-size: 1.1rem !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.25rem !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("📊 K4-L3B Day 13 — Monitoring & LLMOps Dashboard")
with head_col2:
    st.caption(f"🕒 Last 60 min | Source: `data/logs.jsonl`")

# Auto-refresh
st.markdown(
    f"""<meta http-equiv="refresh" content="{REFRESH_SECONDS}">""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=REFRESH_SECONDS)
def load_logs() -> pd.DataFrame:
    if not LOG_PATH.exists():
        return pd.DataFrame()
    rows = []
    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    now = datetime.now(tz=timezone.utc)
    cutoff = now - pd.Timedelta(minutes=TIME_RANGE_MINUTES)
    df = df[df["ts"] >= cutoff].copy()
    df["minute"] = df["ts"].dt.floor("min")
    return df


df = load_logs()

if df.empty:
    st.warning("⚠️ Không có dữ liệu trong data/logs.jsonl. Hãy gửi request hoặc chạy load_test.py.")
    st.stop()

df_resp = df[df["event"] == "response_sent"].copy()
if not df_resp.empty:
    df_resp["latency_ms"] = pd.to_numeric(df_resp.get("latency_ms", pd.Series(dtype=float)), errors="coerce")
    df_resp["ttft_ms"] = pd.to_numeric(df_resp.get("ttft_ms", pd.Series(dtype=float)), errors="coerce")
    df_resp["cost_usd"] = pd.to_numeric(df_resp.get("cost_usd", pd.Series(dtype=float)), errors="coerce")
    df_resp["tokens_in"] = pd.to_numeric(df_resp.get("tokens_in", pd.Series(dtype=float)), errors="coerce")
    df_resp["tokens_out"] = pd.to_numeric(df_resp.get("tokens_out", pd.Series(dtype=float)), errors="coerce")
    df_resp["quality_score"] = pd.to_numeric(df_resp.get("quality_score", pd.Series(dtype=float)), errors="coerce")

df_req = df[df["event"] == "request_received"].copy()
df_fail = df[df["event"] == "request_failed"].copy()

# ==============================================================================
# HÀNG 1: Panel 1 (Latency) | Panel 2 (Traffic) | Panel 3 (Errors & Retrieval)
# ==============================================================================
r1_c1, r1_c2, r1_c3 = st.columns(3)

# ----------------- Panel 1: Latency -----------------
with r1_c1:
    st.markdown("### 📈 Panel 1 — Latency (ms)")
    LATENCY_THRESHOLD_MS = 3000
    if not df_resp.empty and df_resp["latency_ms"].notna().any():
        p50 = df_resp["latency_ms"].quantile(0.50)
        p95 = df_resp["latency_ms"].quantile(0.95)
        p99 = df_resp["latency_ms"].quantile(0.99)
        ttft = df_resp["ttft_ms"].quantile(0.95) if df_resp["ttft_ms"].notna().any() else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("P50", f"{p50:.0f}ms")
        m2.metric("P95", f"{p95:.0f}ms", delta="≤3000ms" if p95 <= 3000 else "VIOLATION", delta_color="inverse")
        m3.metric("P99", f"{p99:.0f}ms")
        m4.metric("TTFT", f"{ttft:.0f}ms")

        lat_by_min = (
            df_resp.groupby("minute")["latency_ms"]
            .agg(p50=lambda x: x.quantile(0.50), p95=lambda x: x.quantile(0.95), p99=lambda x: x.quantile(0.99))
            .reset_index()
        )
        lat_melted = lat_by_min.melt(id_vars="minute", var_name="percentile", value_name="latency_ms")

        base_lat = alt.Chart(lat_melted).mark_line(point=True).encode(
            x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M")),
            y=alt.Y("latency_ms:Q", title="ms"),
            color=alt.Color("percentile:N", legend=alt.Legend(orient="top", title=None)),
            tooltip=["minute:T", "percentile:N", "latency_ms:Q"],
        )
        thresh_lat = alt.Chart(pd.DataFrame({"y": [LATENCY_THRESHOLD_MS]})).mark_rule(
            color="red", strokeDash=[6, 4]
        ).encode(y=alt.Y("y:Q"))

        st.altair_chart((base_lat + thresh_lat).properties(height=200), use_container_width=True)
    else:
        st.info("Chưa có dữ liệu response.")

# ----------------- Panel 2: Traffic -----------------
with r1_c2:
    st.markdown("### 🚦 Panel 2 — Traffic (req/min)")
    TRAFFIC_THRESHOLD = 1
    if not df_req.empty:
        traffic = df_req.groupby("minute").size().reset_index(name="count")
        t_col1, t_col2 = st.columns(2)
        t_col1.metric("Total Requests", len(df_req))
        t_col2.metric("Peak req/min", traffic["count"].max() if not traffic.empty else 0)

        base_traf = alt.Chart(traffic).mark_bar(color="#3498DB").encode(
            x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M")),
            y=alt.Y("count:Q", title="Req/min"),
            tooltip=["minute:T", "count:Q"],
        )
        thresh_traf = alt.Chart(pd.DataFrame({"y": [TRAFFIC_THRESHOLD]})).mark_rule(
            color="orange", strokeDash=[6, 4]
        ).encode(y=alt.Y("y:Q"))

        st.altair_chart((base_traf + thresh_traf).properties(height=200), use_container_width=True)
    else:
        st.info("Chưa có dữ liệu request.")

# ----------------- Panel 3: Errors & Retrieval -----------------
with r1_c3:
    st.markdown("### 🔴 Panel 3 — Errors & Retrieval (%)")
    ERROR_THRESHOLD = 2.0
    RET_THRESHOLD = 90.0

    total_req = max(len(df_req), 1)
    failed_cnt = len(df_fail)
    err_rate = (failed_cnt / total_req) * 100

    # Retrieval success
    if "tool_success" in df.columns:
        df_tool = df[df["tool_success"].notna()]
        ret_rate = (df_tool["tool_success"] == True).mean() * 100 if not df_tool.empty else 100.0
    else:
        ret_rate = 100.0

    e_col1, e_col2, e_col3 = st.columns(3)
    e_col1.metric("Error Rate", f"{err_rate:.1f}%", delta="≤2%" if err_rate <= 2.0 else "ALERT", delta_color="inverse")
    e_col2.metric("Failed", failed_cnt)
    e_col3.metric("Retrieval Success", f"{ret_rate:.1f}%", delta="≥90%" if ret_rate >= 90.0 else "ALERT")

    # Error rate timeline
    if not df_req.empty:
        err_by_min = df_req.groupby("minute").size().reset_index(name="total")
        if not df_fail.empty and "minute" in df_fail.columns:
            f_min = df_fail.groupby("minute").size().reset_index(name="failed")
            err_by_min = err_by_min.merge(f_min, on="minute", how="left").fillna(0)
        else:
            err_by_min["failed"] = 0
        err_by_min["error_pct"] = err_by_min["failed"] / err_by_min["total"] * 100

        base_err = alt.Chart(err_by_min).mark_line(point=True, color="#E74C3C").encode(
            x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M")),
            y=alt.Y("error_pct:Q", title="Error %", scale=alt.Scale(domain=[0, max(5, err_by_min["error_pct"].max() + 1)])),
            tooltip=["minute:T", "error_pct:Q"],
        )
        thresh_err = alt.Chart(pd.DataFrame({"y": [ERROR_THRESHOLD]})).mark_rule(
            color="red", strokeDash=[6, 4]
        ).encode(y=alt.Y("y:Q"))

        st.altair_chart((base_err + thresh_err).properties(height=200), use_container_width=True)
    else:
        st.info("Chưa có dữ liệu lỗi.")

st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

# ==============================================================================
# HÀNG 2: Panel 4 (Cost) | Panel 5 (Tokens) | Panel 6 (Quality Proxy)
# ==============================================================================
r2_c1, r2_c2, r2_c3 = st.columns(3)

# ----------------- Panel 4: Cost -----------------
with r2_c1:
    st.markdown("### 💰 Panel 4 — Cost (USD)")
    COST_THRESHOLD = 2.5
    if not df_resp.empty and "cost_usd" in df_resp.columns:
        tot_cost = df_resp["cost_usd"].sum()
        c_col1, c_col2 = st.columns(2)
        c_col1.metric("Session Cost", f"${tot_cost:.4f}")
        c_col2.metric("Daily Cap", f"${COST_THRESHOLD}")

        cost_by_min = df_resp.groupby("minute")["cost_usd"].sum().reset_index()
        base_cost = alt.Chart(cost_by_min).mark_bar(color="#F39C12").encode(
            x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M")),
            y=alt.Y("cost_usd:Q", title="USD"),
            tooltip=["minute:T", alt.Tooltip("cost_usd:Q", format=".5f")],
        )
        st.altair_chart(base_cost.properties(height=200), use_container_width=True)
    else:
        st.info("Chưa có dữ liệu chi phí.")

# ----------------- Panel 5: Tokens -----------------
with r2_c2:
    st.markdown("### 🔢 Panel 5 — Tokens (In / Out)")
    TOKEN_THRESHOLD = 50000
    if not df_resp.empty and "tokens_in" in df_resp.columns and "tokens_out" in df_resp.columns:
        t_in = df_resp["tokens_in"].sum()
        t_out = df_resp["tokens_out"].sum()

        tok_col1, tok_col2, tok_col3 = st.columns(3)
        tok_col1.metric("Input", f"{t_in:.0f}")
        tok_col2.metric("Output", f"{t_out:.0f}")
        tok_col3.metric("Limit", f"{TOKEN_THRESHOLD:,}")

        tok_by_min = df_resp.groupby("minute")[["tokens_in", "tokens_out"]].sum().reset_index()
        tok_melted = tok_by_min.melt(id_vars="minute", var_name="type", value_name="tokens")

        base_tok = alt.Chart(tok_melted).mark_bar().encode(
            x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M")),
            y=alt.Y("tokens:Q", title="Tokens"),
            color=alt.Color("type:N", legend=alt.Legend(orient="top", title=None)),
            tooltip=["minute:T", "type:N", "tokens:Q"],
        )
        st.altair_chart(base_tok.properties(height=200), use_container_width=True)
    else:
        st.info("Chưa có dữ liệu tokens.")

# ----------------- Panel 6: Quality Proxy -----------------
with r2_c3:
    st.markdown("### ⭐ Panel 6 — Quality Proxy Score")
    QUALITY_THRESHOLD = 0.75
    if not df_resp.empty and "quality_score" in df_resp.columns:
        avg_qual = df_resp["quality_score"].mean()
        q_col1, q_col2 = st.columns(2)
        q_col1.metric("Avg Quality", f"{avg_qual:.2f}", delta="≥0.75" if avg_qual >= QUALITY_THRESHOLD else "LOW")
        q_col2.metric("Threshold", f"{QUALITY_THRESHOLD}")

        qual_by_min = df_resp.groupby("minute")["quality_score"].mean().reset_index()
        base_qual = alt.Chart(qual_by_min).mark_line(point=True, color="#8E44AD").encode(
            x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M")),
            y=alt.Y("quality_score:Q", title="Score (0-1)", scale=alt.Scale(domain=[0, 1])),
            tooltip=["minute:T", alt.Tooltip("quality_score:Q", format=".2f")],
        )
        thresh_qual = alt.Chart(pd.DataFrame({"y": [QUALITY_THRESHOLD]})).mark_rule(
            color="red", strokeDash=[6, 4]
        ).encode(y=alt.Y("y:Q"))

        st.altair_chart((base_qual + thresh_qual).properties(height=200), use_container_width=True)
    else:
        st.info("Chưa có dữ liệu quality.")
