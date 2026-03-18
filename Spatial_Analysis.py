"""
Spatial Analysis for Kitsap Transit
Visualizes traffic patterns, missing data zones, and corridor-level demand
Supports decision-making for expanded shuttle service on Bainbridge Island
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
from shapely.geometry import Point, LineString
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# File paths - UPDATE THESE FOR YOUR DATA
DATA_PATHS = {
    'commercial_od': r"C:\Users\rebeccasc\Documents\Scripts\BI_commerce_TDM\2014263_BI_Commecial_OD_all_vehicles\2014263_BI_Commecial_OD_all_vehicles_od_trip_all.csv",
    'trip_purpose': r"C:\Users\rebeccasc\Documents\Scripts\BI_commerce_TDM\2014261_BI_Corridor_Volume_2025_dayparts_purpose.csv"
}

# TAZ shapefile for Kitsap County - UPDATE THIS PATH
TAZ_SHAPEFILE = r"path/to/kitsap_taz_shapefile.shp"

# Output directory
OUTPUT_DIR = Path("./output/spatial_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Kitsap Transit Operating Hours
TRANSIT_HOURS = {
    'weekday': {'start': 4.5, 'end': 19.25, 'label': 'Weekday (4:30 AM - 7:15 PM)'},
    'saturday': {'start': 9.0, 'end': 18.0, 'label': 'Saturday (9:00 AM - 6:00 PM)'},
    'sunday': {'start': 9.0, 'end': 16.0, 'label': 'Sunday (9:00 AM - 4:00 PM)'}
}

# Commercial corridors (for spatial reference)
COMMERCIAL_CORRIDORS = [
    'HIGH_SCHOOL_RD',      # Just west of 305 intersection until Sportsman Club Road
    'SPORTSMAN_CLUB',      # From Woodward Middle School/Coppertop until just before 305
    'SR305_MID',           # Just north of High School Road until Sportsman Club Road
    'SR305_N',             # North of Sportsman Club Road, over Agate Pass, to Kingston Ferry turnoff
    'SR305_S',             # Below Winslow Way & Olympic until just south of High School Road
    'WINSLOW_WAY',         # Just west of 305 along corridor until Madison Ave
    'LYNWOOD_CENTER'       # South end commercial zone
]

# Time periods
PEAK_HOURS = ['7am ', '8am ', '9am ', '4pm ', '5pm ', '6pm ']
TIME_PERIODS = {
    '0: All Day (12am-12am)': 'All Day',
    '1: Early AM (12am-6am)': 'Early AM',
    '2: Peak AM (6am-10am)': 'Peak AM',
    '3: Mid-Day (10am-3pm)': 'Mid-Day',
    '4: Peak PM (3pm-7pm)': 'Peak PM',
    '5: Late PM (7pm-12am)': 'Late PM'
}

# Volume column
VOLUME_COL = 'Average Daily O-D Traffic (StL Volume)'

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_hour(period_str):
    """Extract hour number from period string"""
    try:
        return int(str(period_str).split(':')[0])
    except:
        return None

def get_time_label(period_str):
    """Convert time period code to readable label"""
    return TIME_PERIODS.get(period_str, period_str)

# =============================================================================
# DATA LOADING AND PREPARATION
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

def prepare_od_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare OD data for spatial analysis
    Filters for weekday, removes all-day aggregate, adds time column
    """
    # Filter for weekday
    df = df[df['Day Type'] == '1: Weekday (M-Th)'].copy()
    
    # Keep only relevant columns
    df = df[['Origin Zone ID', 'Destination Zone ID', 'Day Part', VOLUME_COL]]
    
    # Remove all-day aggregate
    df = df[df['Day Part'] != '0: All Day (12am-12am)']
    
    # Extract time label
    df['time'] = df['Day Part'].astype(str).str[4:8]
    df = df.drop('Day Part', axis=1)
    
    # Rename columns
    df.rename(columns={
        'Origin Zone ID': 'Orig',
        'Destination Zone ID': 'Dest'
    }, inplace=True)
    
    logger.info(f"Prepared {len(df):,} records for spatial analysis")
    return df

def load_taz_shapefile(shapefile_path: str) -> gpd.GeoDataFrame:
    """Load TAZ shapefile"""
    try:
        taz = gpd.read_file(shapefile_path)
        logger.info(f"Loaded TAZ shapefile with {len(taz)} zones")
        return taz
    except Exception as e:
        logger.error(f"Failed to load TAZ shapefile: {e}")
        raise

# =============================================================================
# SPATIAL ANALYSIS FUNCTIONS
# =============================================================================

def analyze_spatial_coverage(df: pd.DataFrame, taz: gpd.GeoDataFrame) -> Dict:
    """
    Analyze spatial coverage patterns by origin and destination
    Identifies zones with missing data for transit planning
    """
    results = {}
    
    # Get unique zone IDs from TAZ
    taz_ids = set(taz['id'].unique()) if 'id' in taz.columns else set(range(1, len(taz) + 1))
    
    # Origin coverage
    orig_present = set(df['Orig'].unique())
    results['orig_missing'] = taz_ids - orig_present
    results['orig_missing_count'] = len(results['orig_missing'])
    results['orig_coverage_pct'] = (len(orig_present) / len(taz_ids)) * 100
    
    # Destination coverage
    dest_present = set(df['Dest'].unique())
    results['dest_missing'] = taz_ids - dest_present
    results['dest_missing_count'] = len(results['dest_missing'])
    results['dest_coverage_pct'] = (len(dest_present) / len(taz_ids)) * 100
    
    logger.info(f"Origin coverage: {results['orig_coverage_pct']:.1f}%")
    logger.info(f"Destination coverage: {results['dest_coverage_pct']:.1f}%")
    
    return results

def aggregate_by_zone(df: pd.DataFrame, by_col: str, time_filter: Optional[str] = None) -> pd.Series:
    """
    Aggregate OD volume by origin or destination zone
    Optional time filter for peak hour analysis
    """
    if time_filter:
        filtered = df[df['time'] == time_filter]
    else:
        filtered = df
    
    return filtered.groupby(by_col)[VOLUME_COL].sum()

# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def plot_zone_coverage(taz: gpd.GeoDataFrame, 
                       present_zones: set, 
                       missing_zones: set,
                       title: str,
                       output_path: Path,
                       filename: str):
    """
    Plot TAZ map highlighting present vs missing zones
    """
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    
    # Create coverage indicator
    taz['coverage'] = 'Present'
    if 'id' in taz.columns:
        taz.loc[~taz['id'].isin(present_zones), 'coverage'] = 'Missing'
    else:
        # If no ID column, assume zones are indexed
        taz['coverage'] = 'Present'
        missing_mask = taz.index.isin(list(missing_zones))
        taz.loc[missing_mask, 'coverage'] = 'Missing'
    
    # Plot
    taz.plot(ax=ax, column='coverage', 
             color={'Present': 'lightblue', 'Missing': 'lightcoral'},
             edgecolor='gray', linewidth=0.2, legend=True)
    
    ax.set_title(title, fontsize=16)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.grid(linestyle='dotted', color='gray', alpha=0.5)
    
    # Add legend manually
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='lightblue', label=f'Present ({len(present_zones)})'),
        Patch(facecolor='lightcoral', label=f'Missing ({len(missing_zones)})')
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    
    plt.tight_layout()
    plt.savefig(output_path / filename, dpi=300, bbox_inches='tight')
    plt.close()

def plot_volume_by_zone(taz: gpd.GeoDataFrame,
                        zone_volumes: pd.Series,
                        title: str,
                        output_path: Path,
                        filename: str,
                        vmax: Optional[float] = None):
    """
    Plot TAZ map with volume-weighted coloring
    """
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    
    # Merge volumes with TAZ
    volume_df = pd.DataFrame({'id': zone_volumes.index, 'volume': zone_volumes.values})
    
    if 'id' in taz.columns:
        taz_merged = taz.merge(volume_df, on='id', how='left')
    else:
        taz_merged = taz.copy()
        taz_merged['volume'] = 0
        for idx, vol in zone_volumes.items():
            if idx <= len(taz_merged):
                taz_merged.loc[idx-1, 'volume'] = vol
    
    # Plot missing zones in gray
    taz_merged[taz_merged['volume'].isna()].plot(ax=ax, color='gray', edgecolor='gray', linewidth=0.2)
    
    # Plot zones with data
    taz_merged[taz_merged['volume'].notna()].plot(
        ax=ax, column='volume', cmap='YlOrRd', 
        edgecolor='gray', linewidth=0.2, legend=True,
        vmin=0, vmax=vmax
    )
    
    ax.set_title(title, fontsize=16)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.grid(linestyle='dotted', color='gray', alpha=0.5)
    
    # Add note about missing zones
    missing_count = taz_merged['volume'].isna().sum()
    if missing_count > 0:
        ax.text(0.02, 0.02, f'Gray zones: {missing_count} with no data',
                transform=ax.transAxes, fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_path / filename, dpi=300, bbox_inches='tight')
    plt.close()

def plot_peak_hour_comparison(df: pd.DataFrame, 
                              taz: gpd.GeoDataFrame,
                              output_path: Path):
    """
    Create series of maps comparing peak hour origin volumes
    """
    for hour in PEAK_HOURS:
        # Aggregate by origin
        orig_volumes = aggregate_by_zone(df, 'Orig', time_filter=hour)
        
        if len(orig_volumes) == 0:
            continue
        
        # Determine vmax for consistent scaling
        vmax = orig_volumes.quantile(0.95)  # Use 95th percentile to avoid outliers
        
        plot_volume_by_zone(
            taz, orig_volumes,
            title=f"Origin Volumes - {hour.strip()}",
            output_path=output_path,
            filename=f"origin_volumes_{hour.strip().replace(' ', '_')}.png",
            vmax=vmax
        )
        
        logger.info(f"Created map for {hour.strip()}")

def plot_corridor_demand(df: pd.DataFrame,
                         taz: gpd.GeoDataFrame,
                         output_path: Path):
    """
    Identify and visualize high-demand OD pairs
    """
    # Calculate average volume by OD pair
    pair_volume = df.groupby(['Orig', 'Dest'])[VOLUME_COL].mean().reset_index()
    pair_volume = pair_volume.sort_values(VOLUME_COL, ascending=False)
    
    # Get top OD pairs
    top_pairs = pair_volume.head(50).copy()
    
    # Get zone centroids
    if 'id' in taz.columns:
        taz = taz.set_index('id')
    
    centroids = taz.centroid
    
    # Create line geometries for top pairs
    lines = []
    for _, row in top_pairs.iterrows():
        orig = row['Orig']
        dest = row['Dest']
        
        if orig in centroids.index and dest in centroids.index:
            orig_point = centroids.loc[orig]
            dest_point = centroids.loc[dest]
            lines.append(LineString([orig_point, dest_point]))
        else:
            lines.append(None)
    
    top_pairs['geometry'] = lines
    top_pairs = top_pairs[top_pairs['geometry'].notna()]
    
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(top_pairs, geometry='geometry', crs=taz.crs)
    
    # Plot
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    
    # Base map
    taz.plot(ax=ax, color='lightgray', edgecolor='white', linewidth=0.2, alpha=0.5)
    
    # Plot desire lines
    gdf.plot(ax=ax, column=VOLUME_COL, cmap='YlOrRd', 
             linewidth=gdf[VOLUME_COL] / gdf[VOLUME_COL].max() * 3,
             alpha=0.7, legend=True)
    
    ax.set_title("Top 50 OD Pairs by Volume", fontsize=16)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.grid(linestyle='dotted', color='gray', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_path / "top_od_pairs.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Created desire line map for top {len(gdf)} OD pairs")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function"""
    logger.info("Starting Kitsap Transit Spatial Analysis")
    
    # Load data
    df = load_data(DATA_PATHS['commercial_od'])
    df = prepare_od_data(df)
    
    # Load TAZ shapefile (commented out until path is provided)
    # taz = load_taz_shapefile(TAZ_SHAPEFILE)
    
    # For now, create a placeholder message
    logger.info("TAZ shapefile path not configured - skipping spatial visualizations")
    logger.info("To enable spatial analysis, update TAZ_SHAPEFILE path")
    
    # Create output directory
    viz_dir = OUTPUT_DIR / 'spatial_visualizations'
    viz_dir.mkdir(exist_ok=True)
    
    # If TAZ shapefile is available, run spatial analysis
    if False:  # Placeholder - replace with actual condition
        # Analyze spatial coverage
        coverage = analyze_spatial_coverage(df, taz)
        
        # Plot coverage maps
        plot_zone_coverage(
            taz, 
            set(df['Orig'].unique()),
            coverage['orig_missing'],
            "Origin Zone Coverage",
            viz_dir,
            "origin_coverage.png"
        )
        
        plot_zone_coverage(
            taz,
            set(df['Dest'].unique()),
            coverage['dest_missing'],
            "Destination Zone Coverage",
            viz_dir,
            "destination_coverage.png"
        )
        
        # Plot peak hour volumes
        plot_peak_hour_comparison(df, taz, viz_dir)
        
        # Plot desire lines
        plot_corridor_demand(df, taz, viz_dir)
    
    # Generate non-spatial summary
    with open(OUTPUT_DIR / 'spatial_summary.txt', 'w') as f:
        f.write("KITSAP TRANSIT SPATIAL ANALYSIS SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total OD records: {len(df):,}\n")
        f.write(f"Unique origin zones: {df['Orig'].nunique()}\n")
        f.write(f"Unique destination zones: {df['Dest'].nunique()}\n")
        f.write(f"Time periods: {sorted(df['time'].unique())}\n\n")
        f.write("To complete spatial analysis:\n")
        f.write("1. Update TAZ_SHAPEFILE path with correct shapefile location\n")
        f.write("2. Ensure TAZ shapefile has 'id' column matching zone IDs\n")
    
    logger.info(f"Spatial analysis summary saved to {OUTPUT_DIR / 'spatial_summary.txt'}")

if __name__ == "__main__":
    main()
