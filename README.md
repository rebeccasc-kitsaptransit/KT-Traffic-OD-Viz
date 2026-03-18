# Kitsap Transit OD Analysis

Origin-Destination Matrix Descriptive Data Analysis for Kitsap Transit commercial corridor evaluation.

## Analysis Components

- **Number of OD pairs** (OD_Analysis.py)
- **Missing Rate Analysis** (OD_Analysis.py)
- **Temporal Patterns** (OD_Analysis.py)
- **Spatial Patterns** (Spatial_Analysis.py)

---

## 1. Number of OD Pairs

<img width="529" alt="image" src="https://user-images.githubusercontent.com/46463367/167270115-20ef901b-0648-4c61-8067-f49173fa0f2d.png">

*Caption: Distribution of OD pairs across commercial corridors*

---

## 2. Missing Rate Analysis

**Important OD pairs missing rate**

Important links defined as hourly average traffic > 5 vehicles:
- Represents 0.7% of total number of pairs
- Average missing rate from 8AM-5PM is 30%

![image](https://user-images.githubusercontent.com/46463367/167270245-b829e231-6d37-4412-9d98-4d5ce51aa5ff.png)

*Caption: Missing rate distribution for important OD pairs*

**Spatial visualization of missing rates**

OD pairs with missing rate greater than 0.6 visualized on map (line width represents missing rate).

<img width="227" alt="image" src="https://user-images.githubusercontent.com/46463367/167270263-ea58a398-36a4-4a4d-a953-a21f92d3f493.png">

*Caption: Spatial distribution of high-missing-rate OD pairs*

**Key finding**: Longer OD pairs tend to have higher missing rates.

---

## 3. Temporal Patterns

**School Season Departure Time Distribution**

![image](https://user-images.githubusercontent.com/46463367/167270131-6439d627-8c69-4ee3-90e4-22c802241734.png)

*Caption: Hourly distribution of trips during school season*

---

## 4. Spatial Patterns During School Season

**Destination zones peak-hour volume**

<img width="499" alt="image" src="https://user-images.githubusercontent.com/46463367/167270294-8d6bce2d-9fd0-4789-9f4a-55fbb0d68fa1.png">

*Caption: Peak-hour traffic volumes by destination zone*

**Peak-hour vs Off-peak Volume Comparison**

<img width="485" alt="image" src="https://user-images.githubusercontent.com/46463367/167270321-acbbf7e7-bea0-4470-8ccb-31714e1d7b9e.png">

*Caption: Comparison of peak-hour and off-peak volumes (green = zero-traffic zones)*

**Observations**:
- Some zones do not generate or attract trips during certain time slots (shown in green)
- Zero-traffic zones are more prevalent during off-peak hours

---

## Missing Values Distribution

<img width="317" alt="image" src="https://user-images.githubusercontent.com/46463367/167270342-26a80555-643c-40ad-b6a3-267173cef40c.png">

*Caption: Spatial distribution of missing values*

**Key finding**: Missing values are concentrated in north, southeast, and southwest mountain areas. This pattern suggests STL OD data accurately represents true values and can be used as input for transit planning analysis.

---

## Files in this Repository

| File | Description |
|------|-------------|
| `OD_Analysis.py` | OD pair counting, missing rate analysis, temporal pattern analysis |
| `Spatial_Analysis.py` | Spatial visualization of OD patterns, zone-level aggregation |
| `KITSAP_D_COMM.ipynb` | Destination = Commercial analysis |
| `KT_O_COMM.ipynb` | Origin = Commercial analysis |
| `KT_OMD_MiddleFilter.ipynb` | Pass-through analysis via commercial corridors |
| `KT_OD_TripPurpose_AGGR.ipynb` | Trip purpose analysis (aggregated time periods) |
| `KT_OD_TripPurpose_detailed.ipynb` | Trip purpose analysis (hourly data) |
| `KT_SEASONAL_VOLUME.ipynb` | Summer vs off-season volume comparison |
| `MODE_SHARE.ipynb` | Mode share analysis (auto, pedestrian, bike) |
| `OD_HEATMAP.ipynb` | O-D pair heatmap visualization |

---

## Requirements

- Python 3.11.11
- pandas 2.2.3
- numpy
- matplotlib
- seaborn
- geopandas
- contextily
- geoplot
- shapely
- jupyter
