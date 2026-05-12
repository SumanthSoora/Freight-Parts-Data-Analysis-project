# 🏭 Freight Manufacturing Parts Project

A full end-to-end data analytics project built around a **freight rail manufacturing** operation. The goal is simple — take raw messy data, clean it properly using Python, and build Power BI dashboards with deep DAX analysis.

This project covers the full **ETL pipeline**: Extract → Transform → Load.

---

## 📦 The Business Story

We are a freight rail manufacturer. Here's how our operation flows:

```
Suppliers
    ↓  sell raw parts to us
Orders  ──────────────────────────────→  Parts (master reference)
    ↓  parts received into warehouses
Inventory  (parts stored across 4 warehouses)
    ↓  parts consumed during manufacturing
Production Components  (Bill of Materials — what parts built what)
    ↓  finished products roll out
Production  (Locomotive Brake Assemblies, Freight Engine Units etc.)
    ↓
Finished Products  (10 product types)
```

---

## 🗂️ Project Structure

```
Freight Manufacturing Parts Project/
├── data/
│   ├── raw/                                      ← original source files (never modified)
│   │   ├── finished_products.csv
│   │   ├── inventory.csv
│   │   ├── orders.csv
│   │   ├── parts.csv
│   │   ├── production_components.csv
│   │   ├── production.csv
│   │   └── suppliers.csv
│   └── cleaned/                                  ← Python-processed, analysis-ready files
│       ├── finished_products_clean.csv
│       ├── inventory_clean.csv
│       ├── orders_clean.csv
│       ├── parts_clean.csv
│       ├── production_clean.csv
│       ├── production_components_clean.csv
│       └── suppliers_clean.csv
├── Power bi Files/
│   ├── Frieght Parts Analysis Power Bi Dashboard Screen Shots/
│   │   ├── Procurement Overview Dashboard.png
│   │   └── Inventory Analysis Dashboard.png
│   └── Frieght Dasboard.pbix                     ← Power BI report file
├── python/
│   └── clean_data.py                             ← full ETL cleaning pipeline
├── .gitignore
└── README.md
```

---

## 📸 Dashboard Preview

### Procurement Overview

![Procurement Overview](Power%20bi%20Files/Frieght%20Parts%20Analysis%20Power%20Bi%20Dashboard%20Screen%20Shots/Procurement%20Overview%20Dashboard.png)

### Inventory Analysis

![Inventory Analysis](Power%20bi%20Files/Frieght%20Parts%20Analysis%20Power%20Bi%20Dashboard%20Screen%20Shots/Inventory%20Analysis%20Dashboard.png)

_More dashboard pages coming soon — Production Overview, Parts Analysis_

---

## 📊 Dataset Overview

| Table                   | Rows   | What it represents                                         |
| ----------------------- | ------ | ---------------------------------------------------------- |
| `suppliers`             | 30     | Companies we buy raw parts from                            |
| `parts`                 | 311    | Master catalog of all raw components                       |
| `finished_products`     | 10     | Products we manufacture (Brake Assembly, Engine Unit etc.) |
| `orders`                | 20,000 | Purchase orders placed to suppliers                        |
| `inventory`             | 12,560 | Weekly stock snapshots across 4 warehouses                 |
| `production`            | 15,000 | Finished product build runs                                |
| `production_components` | 67,451 | Bill of Materials — parts consumed per build run           |

**Total: 115,362 rows across 7 tables | Date range: Jan 2022 – Dec 2024**

---

## 🐍 ETL Pipeline — [`python/clean_data.py`](python/clean_data.py)

The cleaning script processes all 7 raw tables and outputs clean CSVs ready for Power BI.

```bash
cd python
python clean_data.py
```

### Extract

- Loaded all 7 CSV files using `pd.read_csv()`
- Audited each table for nulls, duplicates, and data type issues before touching anything

### Transform

| Operation                       | Function Used                             | Why                                                                                                                 |
| ------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Standardize column names        | `str.strip().str.lower().str.replace()`   | Spaces and caps in column names break Power BI silently                                                             |
| Strip whitespace from values    | `select_dtypes("object")` + `str.strip()` | `"Engine Components "` and `"Engine Components"` look the same but Power BI treats them as two different categories |
| Convert text to numbers         | `pd.to_numeric(errors="coerce")`          | CSV files load everything as text by default — you can't do math on text                                            |
| Convert text to dates           | `pd.to_datetime(errors="coerce")`         | String dates don't support time intelligence in Power BI                                                            |
| Fill missing values             | `.fillna()`                               | Nulls in key columns break relationships and aggregations                                                           |
| Fix negative values             | `.loc[condition, column] = value`         | Negative order values and stock levels are data entry errors                                                        |
| Cap received qty at ordered qty | `.min(axis=1)`                            | Can't receive more than you ordered — business logic enforcement                                                    |
| Safe division                   | `.replace(0, np.nan)`                     | Prevents division by zero when calculating fill rate %                                                              |
| Convert boolean strings         | `.map({"True": True, "False": False})`    | CSV booleans load as strings — Power BI needs actual True/False                                                     |
| Add date parts                  | `.dt.year` `.dt.month` `.dt.quarter`      | Enables year/quarter/month slicers in Power BI without DAX                                                          |
| Add derived columns             | `.apply(custom_function)`                 | Cost tier, supplier tier, stock status — avoids complex IF logic in DAX                                             |
| Recalculate derived columns     | Direct math between columns               | Never trust pre-calculated columns in raw data — always recalculate from source                                     |
| Remove duplicates               | `.drop_duplicates()`                      | Duplicate IDs cause double-counting in aggregations                                                                 |

### Load

- All cleaned tables exported to [`data/cleaned/`](data/cleaned/) using `to_csv(index=False)`
- Zero nulls across all 7 tables after cleaning

---

## 🧮 DAX Measures Built

| Concept           | Measure                 | Description                                  |
| ----------------- | ----------------------- | -------------------------------------------- |
| Basic Aggregation | `Total Orders`          | COUNT of all order records                   |
| Basic Aggregation | `Total Order Value`     | SUM of all order values                      |
| Basic Aggregation | `Total Parts Ordered`   | SUM of qty ordered                           |
| CALCULATE         | `Delivered Orders`      | Orders filtered to Delivered status only     |
| DIVIDE            | `Delivery Rate %`       | Safe division of delivered vs total orders   |
| DIVIDE            | `Avg Fill Rate %`       | qty received / qty ordered                   |
| TOTALYTD          | `Orders YTD`            | Cumulative orders from Jan 1 of current year |
| DATEADD           | `Orders Previous Month` | Orders shifted back 1 month                  |
| DATEADD           | `Orders MoM Change %`   | Month over month % change in orders          |
| SUMX              | `Total Component Cost`  | Row-by-row qty × unit_cost aggregation       |
| VAR / RETURN      | `Order Value Analysis`  | Multi-variable measure showing total and avg |
| RANKX             | `Parts Order Rank`      | Ranks parts by total orders descending       |
| RELATED           | `Part Category`         | Pulls category from parts table into orders  |

---

## 🛠️ Tech Stack

- **Python** — pandas, numpy
- **Jupyter Notebook** — exploratory analysis and learning
- **Power BI Desktop** — data model, DAX measures, dashboards

---

## 👤 Author

**Sumanth** — Data Analyst  
Erie, PA | [LinkedIn](https://www.linkedin.com/in/soora44/) | [Portfolio](https://github.com/SumanthSoora)
