import os
import time
import re
from collections import Counter
import matplotlib.pyplot as plt
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from textblob import TextBlob
from pyvirtualdisplay import Display
import chromedriver_autoinstaller


from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller

def download_data(username, password):
    import glob
    import time

    # File path to the downloaded data
    download_folder = os.path.expanduser("~/Downloads")
    file_name = "30_Day_Maintenance_Metrics.xlsx"
    file_path = os.path.join(download_folder, file_name)

    # Ensure the previous file is deleted before downloading
    existing_files = glob.glob(os.path.join(download_folder, "30_Day_Maintenance_Metrics*.xlsx"))
    for f in existing_files:
        try:
            os.remove(f)
            print(f"Deleted existing file: {f}")
        except OSError as e:
            print(f"Error deleting file {f}: {e}")

    # Automatically install the correct version of chromedriver
    chromedriver_autoinstaller.install()

    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument("--no-sandbox")  # Required for some environments
    chrome_options.add_argument("--disable-dev-shm-usage")  # Handle large data
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-infobars")  # Disable "Chrome is being controlled" message

    # Set up the Selenium driver
    driver = webdriver.Chrome(options=chrome_options)

    progress = 0
    try:
        # Automate login and navigation
        ## Step 1: Open the login page
        driver.get("https://app.propertyware.com/pw/logoff.do?ts=1731519557913")
        time.sleep(1)
        progress += 20
        yield progress, "Opened login page."
        ## Step 2: Enter login credentials
        driver.find_element(By.ID, "loginEmail").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, ".button.login-button").click()
        time.sleep(1)
        progress += 20
        yield progress, "Entered login credentials."
        ## Step 3: Select account and navigate to reports
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "switchAccountSelect"))
        ).click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//option[text()='Open House Atlanta Property Management LLC']"))
        ).click()

        driver.find_element(By.XPATH, "//a[@href='/pw/reporting/reports.do']").click()
        joshua_reports = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[@a='Joshua Reports']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", joshua_reports)
        joshua_reports.click()
        time.sleep(1)
        progress += 30
        yield progress, "Navigated to reports."
        ## Step 4: Download report
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='30 Day Maintenance Metrics']"))
        ).click()
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//img[@alt='View Report']"))
        ).click()

        time.sleep(10)
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Export / Print')]"))
        ).click()
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='MS Excel']"))
        ).click()

        time.sleep(10)  # Simulate download time
        progress += 30
        yield progress, "Report downloaded successfully."
    finally:
        driver.quit()



def get_sentiment(description):
    analysis = TextBlob(description)
    return analysis.sentiment.polarity

def process_data(file_path):
    # Load and preprocess data
    data = pd.read_excel(file_path, skiprows=10)
    data["Description"] = data["Description"].fillna('').astype(str).str.lower()
    data["Description"] = data["Description"].str.replace('[^\w\s]', '', regex=True)
    data["Description"] = data["Description"].str.replace('\d+', '', regex=True)

    irrelevant_words = {'need', 'one', 'working', 'work', 'issue', 'problem', 'fix',
                        'require', 'also', 'yes', 'please', 'coming', 'open'}
    stop_words = ENGLISH_STOP_WORDS.union(irrelevant_words)
    data["tokens"] = data["Description"].apply(lambda x: [word for word in x.split() if word not in stop_words])
    ## Add sentiment analysis
    data['Sentiment'] = data['Description'].apply(get_sentiment)

    ## Add priority flag based on sentiment score
    data['Priority'] = data['Sentiment'].apply(
        lambda x: 'High' if x < -0.5 else ('Medium' if x < 0 else 'Low')
    )

    ## Ensure WO# column is present (use placeholder if necessary)
    if 'WO#' not in data.columns:
        data['WO#'] = range(1, len(data) + 1)  # Assign sequential IDs if WO# is missing
    print("Data processed.")

    ## Covert Date
    def extract_vendor_name(vendor):
        vendor = str(vendor)
    # Match text after "FS-" and before the first comma, or the end of the string
        match = re.search(r'FS -([^,]+)', vendor)
        if match:
            return match.group(1).strip()  # Return the extracted name
        else:
            return vendor.strip()  # Return the original vendor if no "FS-" is found

    data["Vendors"] = data["Vendors"].apply(extract_vendor_name)
    data['Date Created'] = pd.to_datetime(data['Date Created'], errors='coerce')
    data['Date Completed'] = pd.to_datetime(data['Date Completed'], errors='coerce')

    ## Calculate the duration (in days) between 'Date Created' and 'Date Completed'
    data['Duration (days)'] = (data['Date Completed'] - data['Date Created']).dt.days
    print("Duration calculated for each work order.")
    ## Group by 'Vendors' to calculate counts and average duration
    vendor_summary = data.groupby('Vendors').agg(
        WO_Count=('WO#', 'count'),
        Avg_Duration=('Duration (days)', 'mean')
    ).reset_index()

    vendor_summary['Avg_Duration'] = vendor_summary['Avg_Duration'].round(1)  # Round to 1 decimals
    vendor_summary = vendor_summary.sort_values(by='Avg_Duration', ascending=False).reset_index(drop=True)
    print("Vendor summary table created and sorted by Avg_Duration.")
    return data, vendor_summary

def generate_visualization(data):
    import seaborn as sns
    # Generate visualization
    ## Count for single
    all_words = [word for tokens in data["tokens"] for word in tokens]
    word_freq = Counter(all_words)
    top_words = word_freq.most_common(20)

    words, freqs = zip(*top_words)
    plt.figure(figsize=(10, 6))
    plt.bar(words, freqs)
    plt.xlabel('Words')
    plt.ylabel('Frequency')
    plt.title('Top 20 Most Frequent Words in WO Description')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("top_words_plot.png")  # Save plot
    print("Visualization saved as '~Summary/top_words_plot.png'.")

    ## Sentiment Distribution
    plt.figure(figsize=(10, 6))
    try:
        data['Sentiment'].hist(bins=20, color='skyblue')
        plt.title('Sentiment Distribution Across Work Orders')
        plt.xlabel('Sentiment Score')
        plt.ylabel('Number of Work Orders')
        plt.tight_layout()
        plt.savefig("sentiment_distribution.png")
        print("Saved 'sentiment_distribution.png'")
    except Exception as e:
        print(f"Error generating Sentiment Distribution: {e}")

    ## Stacked Bar Chart for Priority Distribution
    plt.figure(figsize=(10, 6))
    priority_counts = data['Priority'].value_counts()
    sns.barplot(x=priority_counts.index, y=priority_counts.values, palette='coolwarm')
    plt.title('Work Order Priority Distribution')
    plt.xlabel('Priority')
    plt.ylabel('Number of Work Orders')
    plt.tight_layout()
    plt.savefig("priority_distribution.png")
    print("Priority distribution saved as 'priority_distribution.png'.")

# Example usage:
download_folder = os.path.expanduser("~/Downloads")
file_name = "30_Day_Maintenance_Metrics.xlsx"
file_path = os.path.join(download_folder, file_name)

if __name__ == "__main__":
    import os
    username = os.environ.get("PW_USERNAME")
    password = os.environ.get("PW_PASSWORD")
    if not username or not password:
        raise SystemExit("Set PW_USERNAME and PW_PASSWORD environment variables first.")
    if os.path.exists(file_path):
        data = process_data(file_path)
        generate_visualization(data)
    else:
        print(f"File not found: {file_path}")

import streamlit as st
import os
import pandas as pd
from main_script import download_data, process_data, generate_visualization

def main():
    st.title("Maintenance Report Visualization")
    st.write("Click the button below to download the latest data and generate the visualization.")

    if st.button("Refresh Data and Plot"):
        with st.spinner("Downloading and processing data..."):
            # Run the download, process, and visualization pipeline
            username = st.text_input("Username", type="default")
            password = st.text_input("Password", type="password")
            download_data(username, password)

            download_folder = os.path.expanduser("~/Downloads")
            file_name = "30_Day_Maintenance_Metrics.xlsx"
            file_path = os.path.join(download_folder, file_name)

            if os.path.exists(file_path):
                data = process_data(file_path)
                generate_visualization(data)
                st.success("Visualization updated!")
                st.image("top_words_plot.png")
            else:
                st.error("File not found. Ensure the data was downloaded.")

if __name__ == "__main__":
    main()
