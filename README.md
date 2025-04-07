![clayPlotter Logo](clayPlotter.png)

# 🗺️ clayPlotter: Modern Python Choropleth Mapping

Welcome to `clayPlotter`! 👋 This project is transforming the original script into a modern, installable Python package 📦 for creating beautiful choropleth maps 🎨.

Our goal is to build a robust, well-tested, and easy-to-use tool following modern development practices.

## ✨ Project Goals & Phases

We're tackling this modernization in phases:

*   🏗️ **Phase 1: Setup & Restructuring:** Laying the groundwork with proper packaging (`uv`), versioning (`Commitizen`), and a clean project structure. ✅
*   🛠️ **Phase 2: Refactoring & TDD:** Carefully rebuilding functionality using Test-Driven Development (TDD) to ensure reliability and maintainability. We're focusing on object-oriented design and manageable code modules. 🧪
*   🚀 **Phase 3: CI/CD & Finalization:** Implementing Continuous Integration and Continuous Deployment (CI/CD) using GitHub Actions to automate testing and builds. We'll also add essential documentation. ⚙️
## 🚀 Usage

Here's a minimal example of how to generate a choropleth map using `clayPlotter`:

```python
import pandas as pd
from clayPlotter import ChoroplethPlotter
import matplotlib.pyplot as plt # Assuming matplotlib is used for saving

# 1. Prepare your data (Example using dummy data)
#    Your data should have columns for location identifiers (e.g., state names)
#    and the values you want to plot.
data = pd.DataFrame({
    'State': ['California', 'Texas', 'New York', 'Florida'],
    'Value': [10, 8, 9, 7]
})

# 2. Instantiate the plotter
#    Specify the geography (e.g., 'usa_states') and the data column names
plotter = ChoroplethPlotter(
    geography_key='usa_states', # Key for built-in geography (e.g., 'usa_states', 'canada_provinces')
    data=data,
    location_col='State',      # Column in your data with location names/IDs
    value_col='Value'          # Column in your data with values to plot
)

# 3. Generate the plot
#    The plot method might take additional customization arguments
fig, ax = plotter.plot(title="My First Choropleth Map")

# 4. Save the plot (using matplotlib)
plt.savefig("my_choropleth_map.png")
plt.show() # Optional: display the plot
```

## 🔮 Future Plans

*   Publishing to PyPI for easy installation.
*   Adding more advanced documentation.
*   Exploring new features!

Stay tuned for updates! 🎉