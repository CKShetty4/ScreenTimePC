import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

def ensure_table_exists():
    conn = sqlite3.connect('activity_log.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            window_title TEXT,
            start_time TEXT,
            end_time TEXT,
            duration REAL,
            category TEXT
        )
    """)
    conn.commit()
    conn.close()

# Call at the start
ensure_table_exists()

def load_data():
    conn = sqlite3.connect('activity_log.db')
    df = pd.read_sql_query("SELECT * FROM activity_log", conn)
    conn.close()
    return df

def categorize(row):
    title = (row['window_title'] or "").lower()
    app = (row['app_name'] or "").lower()

    if "shorts" in title or "anime" in title or "hainime" in title:
        return "Distraction"
    elif "youtube" in title or "netflix" in title:
        return "Entertainment"
    elif "vs code" in title or "code.exe" in app or "editor" in title:
        return "Productive"
    elif "chatgpt" in title or "course" in title or "udemy" in title or "learn" in title:
        return "Learning"
    else:
        return row.get("category", "Uncategorized")

def seconds_to_hms(seconds):
    return str(timedelta(seconds=int(seconds)))

# Refresh every 10 seconds
count = st_autorefresh(interval=10_000, key="datarefresh")

def main():
    st.sidebar.title("Filters")
    selected_date = st.sidebar.date_input("Select Date", datetime.now().date())

    df = load_data()
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'], errors='coerce')
    df = df.sort_values(by='start_time')
    df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0)
    df['category'] = df.apply(categorize, axis=1)
    df['date'] = df['start_time'].dt.date

    filtered_df = df[df['date'] == selected_date]

    # Add human-readable duration column
    filtered_df['duration_hms'] = filtered_df['duration'].apply(seconds_to_hms)

    if st.sidebar.checkbox("Show raw data"):
        st.write(filtered_df)

    st.title("📈 Productivity Dashboard")
    st.subheader(f"Summary for {selected_date}")

    summary = filtered_df.groupby('category')['duration'].sum().sort_values(ascending=False)

    # Show bar chart with numeric duration (seconds)
    st.bar_chart(summary)

    # Show human-readable summary table
    st.write("Duration by Category (HH:MM:SS):")
    summary_hms = summary.apply(seconds_to_hms)
    st.dataframe(summary_hms)

    # Pie chart with numeric values
    fig, ax = plt.subplots()
    ax.pie(summary, labels=summary.index, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig)

    st.subheader("🔍 Application Usage")
    app_summary = filtered_df.groupby('app_name')['duration'].sum().sort_values(ascending=False).head(10)
    st.bar_chart(app_summary)
    st.write("App Usage Durations (HH:MM:SS):")
    app_summary_hms = app_summary.apply(seconds_to_hms)
    st.dataframe(app_summary_hms)

    st.subheader("🖥️ Top Window Titles")
    title_summary = filtered_df.groupby('window_title')['duration'].sum().sort_values(ascending=False).head(10)
    st.dataframe(title_summary)

    if st.sidebar.button("Export as CSV"):
        filename = f"activity_{selected_date}.csv"
        filtered_df.to_csv(filename, index=False)
        st.success(f"Exported as {filename}")

if __name__ == "__main__":
    main()
