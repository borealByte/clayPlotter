<p align="center"><img src="clayPlotter.png" alt="clayPlotter Logo" width="25%"/></p>


# 🗺️ clayPlotter: Modern Python Choropleth Mapping

Welcome to `clayPlotter`! 👋 This project is a modern, installable Python package 📦 for creating beautiful choropleth maps 🎨. It efficiently downloads geospatial data once and caches it for future use, making it easy to generate maps for different regions.

## ✨ How it Works

`clayPlotter` uses a robust data loading mechanism to download geospatial data for various regions. The data is cached locally, so subsequent runs are much faster. The package is designed to be easy to use, with a simple API for generating choropleth maps.

## 🚀 Usage

Here's a minimal example of how to generate a choropleth map using `clayPlotter`:

### USA Example (State Admission Year)
```python
import pandas as pd
from clayPlotter import ChoroplethPlotter
import matplotlib.pyplot as plt

# Prepare your data (Full USA States Admission Data)
admission_data = {
    'Alabama': 1819, 'Alaska': 1959, 'Arizona': 1912, 'Arkansas': 1836, 'California': 1850,
    'Colorado': 1876, 'Connecticut': 1788, 'Delaware': 1787, 'Florida': 1845, 'Georgia': 1788,
    'Hawaii': 1959, 'Idaho': 1890, 'Illinois': 1818, 'Indiana': 1816, 'Iowa': 1846,
    'Kansas': 1861, 'Kentucky': 1792, 'Louisiana': 1812, 'Maine': 1820, 'Maryland': 1788,
    'Massachusetts': 1788, 'Michigan': 1837, 'Minnesota': 1858, 'Mississippi': 1817,
    'Missouri': 1821, 'Montana': 1889, 'Nebraska': 1867, 'Nevada': 1864, 'New Hampshire': 1788,
    'New Jersey': 1787, 'New Mexico': 1912, 'New York': 1788, 'North Carolina': 1789,
    'North Dakota': 1889, 'Ohio': 1803, 'Oklahoma': 1907, 'Oregon': 1859, 'Pennsylvania': 1787,
    'Rhode Island': 1790, 'South Carolina': 1788, 'South Dakota': 1889, 'Tennessee': 1796,
    'Texas': 1845, 'Utah': 1896, 'Vermont': 1791, 'Virginia': 1788, 'Washington': 1889,
    'West Virginia': 1863, 'Wisconsin': 1848, 'Wyoming': 1890
}
location_col_usa = 'State'
value_col_usa = 'Admission Year'
data = pd.DataFrame(list(admission_data.items()), columns=[location_col_usa, value_col_usa])

# Instantiate the plotter
plotter = ChoroplethPlotter(
    geography_key='usa_states',
    data=data,
    location_col=location_col_usa,
    value_col=value_col_usa
)

# Generate the plot
fig, ax = plotter.plot(title="USA State Admission Year")

# Save the plot
plt.savefig("notebooks/my_choropleth_map_usa.png") # Ensure path matches notebook output
plt.show()
```

![USA Choropleth Map](notebooks/my_choropleth_map_usa.png)

### Canada Example (Province/Territory Confederation Year)
```python
import pandas as pd
from clayPlotter import ChoroplethPlotter
import matplotlib.pyplot as plt

# Prepare your data (Full Canada Confederation Data)
confederation_data = {
    'Ontario': 1867, 'Québec': 1867, 'Nova Scotia': 1867, 'New Brunswick': 1867,
    'Manitoba': 1870, 'British Columbia': 1871, 'Prince Edward Island': 1873,
    'Saskatchewan': 1905, 'Alberta': 1905, 'Newfoundland and Labrador': 1949,
    'Yukon': 1898, 'Northwest Territories': 1870, 'Nunavut': 1999
}
location_col_can = 'Province/Territory'
value_col_can = 'Confederation Year'
data = pd.DataFrame(list(confederation_data.items()), columns=[location_col_can, value_col_can])

# Instantiate the plotter
plotter = ChoroplethPlotter(
    geography_key='canada_provinces',
    data=data,
    location_col=location_col_can,
    value_col=value_col_can
)

# Generate the plot
fig, ax = plotter.plot(title="Canadian Province/Territory Confederation Year")

# Save the plot
plt.savefig("notebooks/my_choropleth_map_canada.png") # Ensure path matches notebook output
plt.show()
```

![Canada Choropleth Map](notebooks/my_choropleth_map_canada.png)

### China Example (Province Population Approx. 2020/21)
```python
import pandas as pd
from clayPlotter import ChoroplethPlotter
import matplotlib.pyplot as plt

# Prepare your data (China Province Population Data)
china_population_data = {
    'Beijing': 21500000, 'Tianjin': 13900000, 'Hebei': 74600000, 'Shanxi': 34900000,
    'Inner Mongolia': 24000000, 'Liaoning': 42600000, 'Jilin': 24000000, 'Heilongjiang': 31800000,
    'Shanghai': 24900000, 'Jiangsu': 84800000, 'Zhejiang': 64600000, 'Anhui': 61000000,
    'Fujian': 41500000, 'Jiangxi': 45200000, 'Shandong': 101500000, 'Henan': 99400000,
    'Hubei': 57800000, 'Hunan': 66400000, 'Guangdong': 126000000, 'Guangxi': 50100000,
    'Hainan': 10100000, 'Chongqing': 32100000, 'Sichuan': 83600000, 'Guizhou': 38500000,
    'Yunnan': 47200000, 'Tibet': 3600000, 'Shaanxi': 39500000, 'Gansu': 25000000,
    'Qinghai': 5900000, 'Ningxia': 7200000, 'Xinjiang': 25900000
}
location_col_chn = 'Province'
value_col_chn = 'Population'
data = pd.DataFrame(list(china_population_data.items()), columns=[location_col_chn, value_col_chn])

# Instantiate the plotter
# Assumes shapefile join column is 'name_en' as potentially defined in china_provinces.yaml
geo_join_col_chn = 'name_en'
plotter = ChoroplethPlotter(
    geography_key='china_provinces',
    data=data,
    location_col=location_col_chn,
    value_col=value_col_chn
)

# Generate the plot
fig, ax = plotter.plot(
    title="China Province Population (Approx. 2020/21)",
    geo_join_column=geo_join_col_chn # Specify the column in the GeoDataFrame to join on
)

# Save the plot
plt.savefig("notebooks/my_choropleth_map_china.png") # Ensure path matches notebook output
plt.show()
```

![China Choropleth Map](notebooks/my_choropleth_map_china.png)
### Brazil Example (State Population Approx. 2023)
```python
import pandas as pd
from clayPlotter import ChoroplethPlotter
import matplotlib.pyplot as plt

# Prepare your data (Approx. Brazil State Population 2023)
brazil_population_data = {
    'Acre': 930000, 'Alagoas': 3100000, 'Amapá': 880000, 'Amazonas': 3900000,
    'Bahia': 14100000, 'Ceará': 8800000, 'Distrito Federal': 2800000, 'Espírito Santo': 3800000,
    'Goiás': 7100000, 'Maranhão': 6800000, 'Mato Grosso': 3700000, 'Mato Grosso do Sul': 2800000,
    'Minas Gerais': 20500000, 'Pará': 8100000, 'Paraíba': 4000000, 'Paraná': 11400000,
    'Pernambuco': 9000000, 'Piauí': 3300000, 'Rio de Janeiro': 16100000, 'Rio Grande do Norte': 3300000,
    'Rio Grande do Sul': 10900000, 'Rondônia': 1600000, 'Roraima': 630000, 'Santa Catarina': 7600000,
    'São Paulo': 44400000, 'Sergipe': 2300000, 'Tocantins': 1600000
}
location_col_bra = 'State'
value_col_bra = 'Population'
data = pd.DataFrame(list(brazil_population_data.items()), columns=[location_col_bra, value_col_bra])

# Instantiate the plotter
# Assumes shapefile join column is 'name' as potentially defined in brazil_states.yaml
geo_join_col_bra = 'name'
plotter = ChoroplethPlotter(
    geography_key='brazil_states',
    data=data,
    location_col=location_col_bra,
    value_col=value_col_bra
)

# Generate the plot
fig, ax = plotter.plot(
    title="Brazil State Population (Approx. 2023)",
    geo_join_column=geo_join_col_bra # Specify the column in the GeoDataFrame to join on
)

# Save the plot
plt.savefig("notebooks/my_choropleth_map_brazil.png") # Ensure path matches notebook output
plt.show()
```

![Brazil Choropleth Map](notebooks/my_choropleth_map_brazil.png)



## 🔮 Future Plans

* Publishing to PyPI for easy installation.
* Adding more advanced documentation.
* Exploring new features!

Stay tuned for updates! 🎉