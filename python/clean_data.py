"""
=============================================================================
  Freight Manufacturing Parts Project — Data Cleaning Pipeline
=============================================================================
  Author  : Sumanth
  Project : Freight Manufacturing Parts Dashboard
  Purpose : Clean all 7 raw CSV tables and prepare for Power BI ingestion

  Flow:
    Suppliers → Orders → Inventory → Production Components → Production
                    ↓
              Parts (master reference linking everything)
              Finished Products (what we build)

  Tables cleaned:
    1. suppliers            — who we buy from
    2. parts                — raw components we buy
    3. finished_products    — what we manufacture
    4. orders               — purchase orders placed to suppliers
    5. inventory            — weekly stock snapshots per warehouse
    6. production           — finished product build runs
    7. production_components— which parts were consumed per build run
=============================================================================
"""

import pandas as pd
import numpy as np
import os

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
RAW_PATH   = "../data/raw/"
CLEAN_PATH = "../data/cleaned/"
os.makedirs(CLEAN_PATH, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def load(filename):
    df = pd.read_csv(RAW_PATH + filename)
    print(f"\n{'─'*60}")
    print(f"  LOADED : {filename}")
    print(f"  Shape  : {df.shape[0]:,} rows x {df.shape[1]} columns")
    return df

def audit(df, label):
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    print(f"  [{label}]")
    print(f"    Nulls      : {nulls.to_dict() if len(nulls) else 'None'}")
    print(f"    Duplicates : {df.duplicated().sum()}")

def save(df, filename):
    df.to_csv(CLEAN_PATH + filename, index=False)
    print(f"  SAVED  : {filename}  ({df.shape[0]:,} rows x {df.shape[1]} cols)")

def clean_columns(df):
    """Standardize all column names to lowercase with underscores."""
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

def strip_strings(df):
    """Strip leading/trailing whitespace from all string columns.
    Why: spaces in category names silently break Power BI slicer grouping."""
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df

def add_date_parts(df, date_col):
    """Add year, month, quarter, month_name columns from a date column.
    Why: Power BI time intelligence needs these for slicers and DAX filters."""
    df["year"]       = df[date_col].dt.year
    df["month"]      = df[date_col].dt.month
    df["month_name"] = df[date_col].dt.strftime("%b")   # Jan, Feb...
    df["quarter"]    = df[date_col].dt.quarter
    return df


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 1: SUPPLIERS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CLEANING: SUPPLIERS")
print("="*60)

suppliers = load("suppliers.csv")
audit(suppliers, "RAW")

suppliers = clean_columns(suppliers)
suppliers = strip_strings(suppliers)

# Convert active column to proper boolean
# Why: "True"/"False" strings don't work as boolean filters in Power BI
suppliers["active"] = suppliers["active"].map({"True": True, "False": False, True: True, False: False})

# Ensure numeric columns are correct dtype
suppliers["lead_time_days"] = pd.to_numeric(suppliers["lead_time_days"], errors="coerce").fillna(7).astype(int)
suppliers["rating"]         = pd.to_numeric(suppliers["rating"],         errors="coerce")

# Add supplier tier based on rating
# Why: Useful for grouping in Power BI without writing DAX IF chains
def supplier_tier(rating):
    if pd.isna(rating):   return "Unrated"
    elif rating >= 4.5:   return "Preferred"
    elif rating >= 4.0:   return "Approved"
    elif rating >= 3.5:   return "Conditional"
    else:                 return "At Risk"

suppliers["supplier_tier"] = suppliers["rating"].apply(supplier_tier)

audit(suppliers, "CLEANED")
save(suppliers, "suppliers_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 2: PARTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CLEANING: PARTS")
print("="*60)

parts = load("parts.csv")
audit(parts, "RAW")

parts = clean_columns(parts)
parts = strip_strings(parts)

# Fill missing category with "Unknown"
# Why: dropping rows from a master reference table breaks all relationships
parts["category"] = parts["category"].replace("None", np.nan).fillna("Unknown")

# Fill missing unit_cost with category median
# Why: median is more robust than mean for skewed price distributions
parts["unit_cost"] = parts.groupby("category")["unit_cost"].transform(
    lambda x: x.fillna(x.median())
)

# Ensure correct numeric dtypes
parts["unit_cost"]      = pd.to_numeric(parts["unit_cost"],      errors="coerce")
parts["weight_kg"]      = pd.to_numeric(parts["weight_kg"],      errors="coerce")
parts["reorder_point"]  = pd.to_numeric(parts["reorder_point"],  errors="coerce").fillna(50).astype(int)
parts["lead_time_days"] = pd.to_numeric(parts["lead_time_days"], errors="coerce").fillna(7).astype(int)

# Add cost_tier — avoids complex IF logic in DAX for grouping
def cost_tier(cost):
    if pd.isna(cost):  return "Unknown"
    elif cost < 100:   return "Low (<$100)"
    elif cost < 300:   return "Medium ($100-$300)"
    elif cost < 600:   return "High ($300-$600)"
    else:              return "Premium (>$600)"

parts["cost_tier"] = parts["unit_cost"].apply(cost_tier)

audit(parts, "CLEANED")
save(parts, "parts_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 3: FINISHED PRODUCTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CLEANING: FINISHED PRODUCTS")
print("="*60)

fp = load("finished_products.csv")
audit(fp, "RAW")

fp = clean_columns(fp)
fp = strip_strings(fp)

# Ensure correct numeric dtypes
fp["unit_price"] = pd.to_numeric(fp["unit_price"], errors="coerce")
fp["weight_kg"]  = pd.to_numeric(fp["weight_kg"],  errors="coerce")

audit(fp, "CLEANED")
save(fp, "finished_products_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 4: ORDERS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CLEANING: ORDERS")
print("="*60)

orders = load("orders.csv")
audit(orders, "RAW")

orders = clean_columns(orders)
orders = strip_strings(orders)

# Parse order_date as datetime
# Why: string dates don't support time intelligence in Power BI
orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")

# Drop rows with no date — unusable for trend analysis
before = len(orders)
orders.dropna(subset=["order_date"], inplace=True)
print(f"  Dropped {before - len(orders):,} rows: null order_date")

# Remove duplicate order IDs
before = len(orders)
orders.drop_duplicates(subset=["order_id"], inplace=True)
print(f"  Dropped {before - len(orders):,} rows: duplicate order_id")

# Fix negative total_order_value — recalculate from qty x unit_cost
# Why: negative values are data entry errors; source truth is qty * unit_cost
orders.loc[orders["total_order_value"] < 0, "total_order_value"] = np.nan
orders["total_order_value"] = orders["total_order_value"].fillna(
    orders["qty_ordered"] * orders["unit_cost"]
).round(2)

# Cap qty_received at qty_ordered — can't receive more than was ordered
orders["qty_received"] = orders[["qty_ordered", "qty_received"]].min(axis=1)

# Standardize status values
orders["status"] = orders["status"].str.strip().str.title()

# Add date parts for Power BI slicers
orders = add_date_parts(orders, "order_date")

# Key KPIs at row level — will be aggregated in DAX using SUMX
orders["fill_rate_pct"] = round(
    orders["qty_received"] / orders["qty_ordered"].replace(0, np.nan) * 100, 2
).fillna(0)

# Boolean flags for easy CALCULATE filtering in DAX
orders["is_fulfilled"]     = orders["status"].isin(["Delivered"])
orders["is_problem_order"] = orders["status"].isin(["Backordered", "Cancelled"])

audit(orders, "CLEANED")
save(orders, "orders_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 5: INVENTORY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CLEANING: INVENTORY")
print("="*60)

inv = load("inventory.csv")
audit(inv, "RAW")

inv = clean_columns(inv)
inv = strip_strings(inv)

# Parse snapshot_date
inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"], errors="coerce")

before = len(inv)
inv.dropna(subset=["snapshot_date"], inplace=True)
print(f"  Dropped {before - len(inv):,} rows: null snapshot_date")

# Fix negative stock levels — data entry error, set to 0
inv.loc[inv["stock_level"] < 0, "stock_level"] = 0

# Recalculate derived columns from corrected source values
inv["below_reorder"]   = inv["stock_level"] < inv["reorder_point"]
inv["inventory_value"] = (inv["stock_level"] * inv["unit_cost"]).round(2)

# Add date parts
inv = add_date_parts(inv, "snapshot_date")

# Stock status — useful Power BI slicer dimension
def stock_status(row):
    if row["stock_level"] == 0:                            return "Out of Stock"
    elif row["stock_level"] < row["reorder_point"]:        return "Below Reorder Point"
    elif row["stock_level"] < row["reorder_point"] * 1.5: return "Low Stock"
    else:                                                   return "Adequate"

inv["stock_status"] = inv.apply(stock_status, axis=1)

audit(inv, "CLEANED")
save(inv, "inventory_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 6: PRODUCTION
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CLEANING: PRODUCTION")
print("="*60)

prod = load("production.csv")
audit(prod, "RAW")

prod = clean_columns(prod)
prod = strip_strings(prod)

# Parse production_date
prod["production_date"] = pd.to_datetime(prod["production_date"], errors="coerce")

before = len(prod)
prod.dropna(subset=["production_date"], inplace=True)
print(f"  Dropped {before - len(prod):,} rows: null production_date")

# Remove duplicates
before = len(prod)
prod.drop_duplicates(subset=["production_id"], inplace=True)
print(f"  Dropped {before - len(prod):,} rows: duplicate production_id")

# Fix invalid qty_produced
# Domain rule: a single finished product run is between 1 and 100 units
before = len(prod)
prod = prod[(prod["qty_produced"] > 0) & (prod["qty_produced"] <= 100)]
print(f"  Dropped {before - len(prod):,} rows: invalid qty_produced")

# Standardize text columns
prod["shift"]  = prod["shift"].str.strip().str.title()
prod["status"] = prod["status"].str.strip().str.title()

# Add date parts
prod = add_date_parts(prod, "production_date")

# Add day of week — useful for shift/weekday analysis in Power BI
prod["day_of_week"]  = prod["production_date"].dt.day_name()
prod["week_number"]  = prod["production_date"].dt.isocalendar().week.astype(int)

audit(prod, "CLEANED")
save(prod, "production_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# TABLE 7: PRODUCTION COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CLEANING: PRODUCTION COMPONENTS")
print("="*60)

pc = load("production_components.csv")
audit(pc, "RAW")

pc = clean_columns(pc)

# Remove rows with null part_id or production_id — orphaned records
before = len(pc)
pc.dropna(subset=["production_id", "part_id"], inplace=True)
print(f"  Dropped {before - len(pc):,} rows: null production_id or part_id")

# Remove duplicates
before = len(pc)
pc.drop_duplicates(subset=["component_id"], inplace=True)
print(f"  Dropped {before - len(pc):,} rows: duplicate component_id")

# Fix invalid qty_consumed
pc["qty_consumed"] = pd.to_numeric(pc["qty_consumed"], errors="coerce")
pc.loc[pc["qty_consumed"] <= 0, "qty_consumed"] = np.nan
pc["qty_consumed"] = pc["qty_consumed"].fillna(1).astype(int)

# Add component_cost by joining with parts
# Why: enables "Total Raw Material Cost per Production Run" DAX measure
parts_clean = pd.read_csv(CLEAN_PATH + "parts_clean.csv")[["part_id", "unit_cost", "category"]]
pc = pc.merge(parts_clean, on="part_id", how="left")
pc["component_cost"] = (pc["qty_consumed"] * pc["unit_cost"]).round(2)

audit(pc, "CLEANED")
save(pc, "production_components_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  PIPELINE COMPLETE — FINAL SUMMARY")
print("="*60)

files = [
    "suppliers_clean.csv",
    "parts_clean.csv",
    "finished_products_clean.csv",
    "orders_clean.csv",
    "inventory_clean.csv",
    "production_clean.csv",
    "production_components_clean.csv",
]

total = 0
for fname in files:
    df = pd.read_csv(CLEAN_PATH + fname)
    total += len(df)
    nulls = df.isnull().sum().sum()
    print(f"  {fname:<40} {len(df):>8,} rows | {len(df.columns):>2} cols | nulls: {nulls}")

print(f"\n  Grand total rows : {total:,}")
print(f"  Output folder    : {CLEAN_PATH}")
print("\n  Next → Load cleaned CSVs into Power BI Desktop → Build Star Schema")
print("="*60)
