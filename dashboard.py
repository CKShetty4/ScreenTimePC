import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh



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

    if st.sidebar.checkbox("Show raw data"):
        st.write(filtered_df)

    st.title("📈 Productivity Dashboard")
    st.subheader(f"Summary for {selected_date}")

    summary = filtered_df.groupby('category')['duration'].sum().sort_values(ascending=False)
    st.bar_chart(summary)

    fig, ax = plt.subplots()
    ax.pie(summary, labels=summary.index, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig)

    st.subheader("🔍 Application Usage")
    app_summary = filtered_df.groupby('app_name')['duration'].sum().sort_values(ascending=False).head(10)
    st.bar_chart(app_summary)

    st.subheader("🖥️ Top Window Titles")
    title_summary = filtered_df.groupby('window_title')['duration'].sum().sort_values(ascending=False).head(10)
    st.dataframe(title_summary)

    if st.sidebar.button("Export as CSV"):
        filename = f"activity_{selected_date}.csv"
        filtered_df.to_csv(filename, index=False)
        st.success(f"Exported as {filename}")


if __name__ == "__main__":
    main()
