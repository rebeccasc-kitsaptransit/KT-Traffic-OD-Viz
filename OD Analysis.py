"""
Origin-Destination Analysis for Kitsap Transit
Analyzes Streetlight OD data to evaluate travel patterns through commercial corridors
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
import geoplot as gplt
import geoplot.crs as gcrs
from shapely.geometry import Point, LineString
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
import seaborn as sns
from matplotlib.ticker import FuncFormatter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# File paths - UPDATE THESE FOR YOUR DATA
DATA_PATHS = {
    'commercial_od': r"C:\Users\rebeccasc\Documents\Scripts\BI_commerce_TDM\2014263_BI_Commecial_OD_all_vehicles\2014263_BI_Commecial_OD_all_vehicles_od_trip_all.csv",
    'trip_purpose': r"C:\Users\rebeccasc\Documents\Scripts\BI_commerce_TDM\2014261_BI_Corridor_Volume_2025_dayparts_purpose.csv",
    'middle_filter': r"C:\Users\rebeccasc\Documents\Scripts\BI_commerce_TDM\2013907_BI_Corridor_Volume_2024_mf_all.csv"
}

# Output directory
OUTPUT_DIR = Path("./output/od_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Kitsap Transit Operating Hours
TRANSIT_HOURS = {
    'weekday': {'start': 4.5, 'end': 19.25, 'label': 'Weekday (4:30 AM - 7:15 PM)'},
    'saturday': {'start': 9.0, 'end': 18.0, 'label': 'Saturday (9:00 AM - 6:00 PM)'},
    'sunday': {'start': 9.0, 'end': 16.0, 'label': 'Sunday (9:00 AM - 4:00 PM)'}
}

# Commercial corridors (destinations/middle filters)
COMMERCIAL_CORRIDORS = [
    'HIGH_SCHOOL_RD',      # Just west of 305 intersection until Sportsman Club Road
    'SPORTSMAN_CLUB',      # From Woodward Middle School/Coppertop until just before 305
    'SR305_MID',           # Just north of High School Road until Sportsman Club Road
    'SR305_N',             # North of Sportsman Club Road, over Agate Pass, to Kingston Ferry turnoff
    'SR305_S',             # Below Winslow Way & Olympic until just south of High School Road
    'WINSLOW_WAY',         # Just west of 305 along corridor until Madison Ave
    'LYNWOOD_CENTER'       # South end commercial zone
]

# Time periods (aggregated)
TIME_PERIODS = {
    '0: All Day (12am-12am)': 'All Day',
    '1: Early AM (12am-6am)': 'Early AM',
    '2: Peak AM (6am-10am)': 'Peak AM',
    '3: Mid-Day (10am-3pm)': 'Mid-Day',
    '4: Peak PM (3pm-7pm)': 'Peak PM',
    '5: Late PM (7pm-12am)': 'Late PM'
}

TIME_PERIOD_ORDER = ['1: Early AM (12am-6am)', '2: Peak AM (6am-10am)', 
                      '3: Mid-Day (10am-3pm)', '4: Peak PM (3pm-7pm)', 
                      '5: Late PM (7pm-12am)', '0: All Day (12am-12am)']

# Day types
DAY_TYPES = [
    '0: All Days (M-Su)',
    '1: Weekday (M-Th)',
    '2: Friday (F-F)',
    '3: Saturday (Sa-Sa)',
    '4: Sunday (Su-Su)'
]

# Trip purposes
TRIP_PURPOSES = {
    'Home to Work': 'Home-Based Work',
    'Home to Other': 'Home-Based Other', 
    'Non-Home Based Trip': 'Non-Home Based'
}

# Volume column
VOLUME_COL = 'Average Daily O-D Traffic (StL Volume)'
TRIP_LENGTH_COL = 'Avg Trip Length (mi)'
TRIP_SPEED_COL = 'Avg Trip Speed (mph)'

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def comma_formatter(x, p):
    """Format numbers with commas"""
    return format(int(x), ',')

comma_fmt = FuncFormatter(comma_formatter)

def extract_hour(period_str):
    """Extract hour number from period string"""
    try:
        return int(str(period_str).split(':')[0])
    except:
        return None

def get_day_category(day_type):
    """Categorize day type for transit lookup"""
    day_str = str(day_type).lower()
    if 'weekday' in day_str or 'm-th' in day_str:
        return 'weekday'
    elif 'friday' in day_str:
        return 'weekday'  # Friday uses weekday hours
    elif 'saturday' in day_str:
        return 'saturday'
    elif 'sunday' in day_str:
        return 'sunday'
    return 'weekday'

def is_during_transit(day_part, day_category):
    """Determine if time period falls within transit hours"""
    if day_category not in TRANSIT_HOURS:
        return False
    
    # Peak periods are during service for most days
    if day_part in ['2: Peak AM (6am-10am)', '3: Mid-Day (10am-3pm)', '4: Peak PM (3pm-7pm)']:
        if day_category == 'sunday' and day_part == '2: Peak AM (6am-10am)':
            return False
        if day_category == 'saturday' and day_part == '4: Peak PM (3pm-7pm)':
            return day_part == '4: Peak PM (3pm-7pm)'  # Saturday PM is within service
        return True
    
    return False

# =============================================================================
# DATA LOADING
# =============================================================================

def load_data(file_path: str) -> pd.DataFrame:
    """Load and validate input data"""
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Successfully loaded {len(df):,} records from {Path(file_path).name}")
        return df
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        raise

# =============================================================================
# ANALYSIS 1: COMMERCIAL OD PATTERNS
# =============================================================================

def analyze_commercial_patterns(df: pd.DataFrame) -> Dict:
    """
    Analyze traffic patterns to/from commercial corridors
    """
    results = {}
    
    # Filter for commercial corridors as destinations
    commercial_df = df[df['Destination Zone Name'].isin(COMMERCIAL_CORRIDORS)].copy()
    
    # Add derived columns
    commercial_df['Day_Category'] = commercial_df['Day Type'].apply(get_day_category)
    commercial_df['During_Transit'] = commercial_df.apply(
        lambda row: is_during_transit(row['Day Part'], row['Day_Category']), axis=1
    )
    
    # Overall statistics
    results['total_volume'] = commercial_df[VOLUME_COL].sum()
    results['volume_by_corridor'] = commercial_df.groupby('Destination Zone Name')[VOLUME_COL].sum().sort_values(ascending=False)
    
    # Transit coverage
    during = commercial_df[commercial_df['During_Transit']][VOLUME_COL].sum()
    outside = commercial_df[~commercial_df['During_Transit']][VOLUME_COL].sum()
    results['during_transit_pct'] = (during / results['total_volume'] * 100) if results['total_volume'] > 0 else 0
    results['outside_transit_pct'] = (outside / results['total_volume'] * 100) if results['total_volume'] > 0 else 0
    
    # By time period
    results['volume_by_period'] = commercial_df.groupby('Day Part')[VOLUME_COL].sum()
    
    logger.info(f"Commercial analysis complete: {results['total_volume']:,.0f} total trips")
    return results

# =============================================================================
# ANALYSIS 2: TRIP LENGTH DISTRIBUTION
# =============================================================================

def analyze_trip_lengths(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze trip length distributions by corridor
    Identifies short trips (<4 miles) that are candidates for mode shift
    """
    # Filter for commercial corridors
    commercial_df = df[df['Destination Zone Name'].isin(COMMERCIAL_CORRIDORS)].copy()
    
    # Create length categories
    def categorize_length(length):
        if pd.isna(length):
            return 'Unknown'
        elif length < 2:
            return 'Very Short (0-2 mi)'
        elif length < 4:
            return 'Short (2-4 mi)'
        elif length < 7:
            return 'Medium (4-7 mi)'
        elif length < 15:
            return 'Long (7-15 mi)'
        else:
            return 'Very Long (15+ mi)'
    
    commercial_df['Length_Category'] = commercial_df[TRIP_LENGTH_COL].apply(categorize_length)
    
    # Calculate distribution by corridor
    length_dist = pd.crosstab(
        commercial_df['Destination Zone Name'],
        commercial_df['Length_Category'],
        values=commercial_df[VOLUME_COL],
        aggfunc='sum',
        normalize='index'
    ) * 100
    
    # Calculate short trip total (<4 miles)
    commercial_df['Is_Short_Trip'] = commercial_df[TRIP_LENGTH_COL] < 4
    short_by_corridor = commercial_df.groupby('Destination Zone Name').apply(
        lambda x: (x[x['Is_Short_Trip']][VOLUME_COL].sum() / x[VOLUME_COL].sum() * 100)
        if x[VOLUME_COL].sum() > 0 else 0
    )
    
    logger.info("Trip length analysis complete")
    return length_dist, short_by_corridor

# =============================================================================
# ANALYSIS 3: MISSING DATA PATTERNS
# =============================================================================

def analyze_missing_patterns(df: pd.DataFrame, total_zones: int = 1104) -> Dict:
    """
    Analyze missing OD pair patterns
    Adapted from original code for Kitsap context
    """
    results = {}
    
    # Calculate missing rate by hour
    all_possible_pairs = total_zones * total_zones
    hourly_counts = df.groupby('time').size()
    hourly_possible = pd.Series(all_possible_pairs, index=hourly_counts.index)
    results['hourly_missing_rate'] = 1 - (hourly_counts / hourly_possible)
    
    # Identify important OD pairs (high volume)
    pair_volume = df.groupby(['Orig', 'Dest'])[VOLUME_COL].mean().reset_index()
    threshold = pair_volume[VOLUME_COL].quantile(0.9)  # Top 10% by volume
    important_pairs = pair_volume[pair_volume[VOLUME_COL] >= threshold]
    
    results['important_pairs_count'] = len(important_pairs)
    results['important_pairs_pct'] = len(important_pairs) / all_possible_pairs * 100
    
    # Missing rate for important pairs
    important_data = df.merge(important_pairs[['Orig', 'Dest']], on=['Orig', 'Dest'], how='inner')
    hourly_coverage = important_data.groupby('time').size()
    results['important_hourly_missing'] = 1 - (hourly_coverage / (len(important_pairs) * 24))
    
    logger.info(f"Missing data analysis complete: {results['important_pairs_count']} important pairs identified")
    return results

# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def plot_volume_heatmap(df: pd.DataFrame, corridor: str, output_path: Path):
    """Create volume heatmap for a specific corridor"""
    corridor_data = df[df['Destination Zone Name'] == corridor]
    
    if len(corridor_data) == 0:
        logger.warning(f"No data for corridor: {corridor}")
        return
    
    # Create pivot table
    pivot = corridor_data.pivot_table(
        values=VOLUME_COL,
        index='Day Part',
        columns='Day Type',
        aggfunc='sum',
        fill_value=0
    )
    
    # Reorder
    pivot = pivot.reindex([p for p in TIME_PERIOD_ORDER if p in pivot.index])
    pivot = pivot[[c for c in DAY_TYPES if c in pivot.columns]]
    
    if len(pivot) == 0:
        return
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd', 
                linewidths=0.5, ax=ax, cbar_kws={'label': 'Volume'})
    
    # Format labels
    ax.set_yticklabels([TIME_PERIODS.get(p.get_text(), p.get_text()) for p in ax.get_yticklabels()])
    ax.set_title(f'Traffic Volume - {corridor}\nTotal: {corridor_data[VOLUME_COL].sum():,.0f}', fontsize=14)
    ax.set_xlabel('Day Type')
    ax.set_ylabel('Time Period')
    
    plt.tight_layout()
    plt.savefig(output_path / f'volume_heatmap_{corridor}.png', dpi=300, bbox_inches='tight')
    plt.close()

def plot_missing_rate_distribution(missing_rates: pd.Series, output_path: Path):
    """Plot missing rate by hour"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x_pos = np.arange(len(missing_rates.index))
    ax.bar(x_pos, missing_rates.values, align='center', alpha=0.7, color='steelblue')
    
    ax.set_title("Missing OD Pair Rate by Hour", fontsize=16)
    ax.set_xlabel('Hour', fontsize=12)
    ax.set_ylabel('Missing Rate', fontsize=12)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(missing_rates.index, rotation=45)
    ax.set_ylim(0, 1)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path / 'missing_rate_by_hour.png', dpi=300, bbox_inches='tight')
    plt.close()

def plot_corridor_comparison(volume_by_corridor: pd.Series, output_path: Path):
    """Plot comparison of volumes across corridors"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    volume_by_corridor.sort_values().plot(kind='barh', ax=ax, color='steelblue', alpha=0.8)
    
    ax.set_title('Traffic Volume by Commercial Corridor', fontsize=16)
    ax.set_xlabel('Volume', fontsize=12)
    ax.set_ylabel('Corridor', fontsize=12)
    ax.xaxis.set_major_formatter(comma_fmt)
    ax.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, v in enumerate(volume_by_corridor.sort_values().values):
        ax.text(v + 100, i, f'{v:,.0f}', va='center')
    
    plt.tight_layout()
    plt.savefig(output_path / 'corridor_volume_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function"""
    logger.info("Starting Kitsap Transit OD Analysis")
    
    # Load data
    df = load_data(DATA_PATHS['commercial_od'])
    
    # Add hour column for time-based analysis
    df['Hour'] = df['Day Part'].apply(extract_hour)
    
    # Run analyses
    logger.info("Running commercial pattern analysis...")
    commercial_results = analyze_commercial_patterns(df)
    
    logger.info("Running trip length analysis...")
    length_dist, short_by_corridor = analyze_trip_lengths(df)
    
    # Create visualizations
    viz_dir = OUTPUT_DIR / 'visualizations'
    viz_dir.mkdir(exist_ok=True)
    
    # Volume heatmaps for each corridor
    for corridor in COMMERCIAL_CORRIDORS:
        plot_volume_heatmap(df, corridor, viz_dir)
    
    # Corridor comparison
    plot_corridor_comparison(commercial_results['volume_by_corridor'], viz_dir)
    
    # Save results
    results_df = pd.DataFrame({
        'Metric': ['Total Volume', 'During Transit %', 'Outside Transit %'],
        'Value': [
            commercial_results['total_volume'],
            commercial_results['during_transit_pct'],
            commercial_results['outside_transit_pct']
        ]
    })
    results_df.to_csv(OUTPUT_DIR / 'summary_results.csv', index=False)
    
    # Save length distribution
    length_dist.to_csv(OUTPUT_DIR / 'trip_length_distribution.csv')
    
    # Summary report
    with open(OUTPUT_DIR / 'analysis_summary.txt', 'w') as f:
        f.write("KITSAP TRANSIT OD ANALYSIS SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total commercial corridor volume: {commercial_results['total_volume']:,.0f}\n")
        f.write(f"During transit hours: {commercial_results['during_transit_pct']:.1f}%\n")
        f.write(f"Outside transit hours: {commercial_results['outside_transit_pct']:.1f}%\n\n")
        f.write("Volume by Corridor:\n")
        for corridor, volume in commercial_results['volume_by_corridor'].items():
            f.write(f"  {corridor}: {volume:,.0f}\n")
    
    logger.info(f"Analysis complete. Results saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
