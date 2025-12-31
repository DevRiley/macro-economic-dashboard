# 🌍 Automated Global Macroeconomic Dashboard

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Power BI](https://img.shields.io/badge/PowerBI-Dashboard-yellow.svg)
![Status](https://img.shields.io/badge/Data-Daily%20Updated-green.svg)

## 📖 Project Overview
This project is an end-to-end data pipeline designed to monitor global macroeconomic health, Fed policy stance, and market risk indicators. 

It automates the ETL process using **Python**, performs financial modeling (e.g., **Taylor Rule**, **Output Gap**, **Liquidity Spreads**), and visualizes the insights in an interactive **Power BI** dashboard.

## 🚀 Key Features
* **Automated Data Pipeline**: Fetches data from **FRED** and **Yahoo Finance** daily via GitHub Actions.
* **Advanced Financial Modeling**:
    * **Taylor Rule**: Calculates the theoretical fed funds rate to assess policy tightness.
    * **Recession Signals**: Monitors Sahm Rule and Yield Curve Inversion (10Y-2Y).
    * **Liquidity & Risk**: Tracks Real Rates, M2 Money Supply, and Copper/Gold ratios.
* **Interactive Visualization**: A 4-page Power BI report providing a holistic view of the economy.

## 📊 Dashboard Preview
*(Please place your screenshots in an 'images' folder or update the paths below)*

| Fed Policy Gap | Market Risk Monitor |
|:---:|:---:|
| ![Fed Policy](dashboard/screenshots/fed_policy.png) | ![Risk Monitor](dashboard/screenshots/risk_monitor.png) |

> **Note**: You can download the `.pbix` file from the `dashboard/` folder to explore the interactive view.

## 🛠️ Tech Stack
* **Language**: Python 3.9
* **Libraries**: `pandas`, `yfinance`, `fredapi`, `numpy`
* **Visualization**: Microsoft Power BI
* **Automation**: GitHub Actions (Cron Job)

## 📂 Project Structure
```text
├── .github/workflows/   # CI/CD Automation scripts
├── data/                # Generated CSV files (Updated daily)
├── src/                 # Python ETL source code
├── dashboard/           # Power BI (.pbix) files
└── requirements.txt     # Python dependencies
```

## ⚙️ How It Works (Automation)
The project utilizes GitHub Actions to run the ETL script every day at 00:00 UTC.

Extract: Pull raw data from FRED API & Yahoo Finance.

Transform: Calculate YoY growth, real rates, and output gaps.

Load: Save processed data to data/*.csv.

Push: Commit the new data back to this repository automatically.

## 📝 License
This project is open-source and available under the MIT License.
