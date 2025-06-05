# `gdasapp::incrqc` — Increment Quality Control

🩹🛠️ This module provides quality control (QC) functionality to ensure that the analysis increment remains within physically meaningful bounds.


The QC process ensures:
- The final analysis state stays within user-defined physical bounds.
- The increment does not add new unstable cells to the background.
- The steric height increment remains within specified limits.

## Overview

### Functions

#### `double adjustAnalysisBounds(double xB, double dX, double minBound, double maxBound)`

Adjusts a scalar increment so that the analysis value does not exceed the defined bounds.

- **Parameters**:
  - `xB`: Background value.
  - `dX`: Proposed increment.
  - `minBound`: Minimum allowed analysis value.
  - `maxBound`: Maximum allowed analysis value.
- **Returns**: A possibly adjusted `dX` such that `xB + dX` is within bounds.

#### `void qcIncrement(const soca::State& xb, soca::Increment& dx, const eckit::Configuration& config, const soca::Geometry& geom)`

Main routine that performs in-place quality control on the increment `dx`.

- **Parameters**:
  - `xb`: Background ocean state.
  - `dx`: Increment to be quality-controlled. Modified in place.
  - `config`: Configuration with QC parameters and bounds.
  - `geom`: Geometry providing spatial metadata.

## Key Features

### 1. **Water Column Stability**

This check ensures that the increment does not introduce **new static instabilities** into the water column.

#### Method

The check operates iteratively (with a user-defined number of iterations), and for each grid point (node) it:

1. **Computes density** using the UNESCO 1983 equation of state for both the background and the analysis (i.e., `background + increment`) at every vertical level.
2. **Calculates vertical density gradients** (∂ρ/∂z) for both background and analysis.
3. **Identifies instability conditions**:
   - The analysis introduces a static instability (∂ρ/∂z < 0) where the background was stable (∂ρ/∂z ≥ 0).
   - The analysis increases the level of instability already present in the background.
4. **Applies a local correction** by scaling down temperature and salinity increments at affected levels based on the ratio of the analysis gradient to a user-defined minimum stable density gradient (`min stable density gradient`). The correction factor is clamped between 0.1 and 1.0.
5. **Smooths corrected values** using neighboring points to reduce grid noise and introduce local consistency.

#### Notes

- Corrections are only applied at **non-ghost ocean nodes** (where bathymetry is positive and layer thickness is non-zero).
- Neighbor information is used to perform **localized smoothing** of the corrected increments for both temperature and salinity.
- This procedure is intended to maintain hydrostatic stability and avoid introducing artificial density inversions that can degrade the forecast.

### 2. **Steric Height Limit**

This check constrains the **sea surface height (SSH) increment** derived from temperature and salinity changes to remain within physically meaningful limits.

#### Method

For each node, the check:

1. **Evaluates the SSH increment** derived from temperature and salinity profiles.
2. **Checks if the absolute SSH increment exceeds** a configured maximum (`increment max.steric`).
3. If the threshold is exceeded:
   - **Computes a rescaling factor** based on the ratio of the maximum allowed SSH increment to the current value.
   - **Scales down the temperature and salinity increments** by this factor to reduce their effect on SSH.
4. **Recomputes the steric height increment** using the rescaled temperature and salinity profiles.
5. **Updates the SSH increment** to match the recomputed steric height.

#### Notes

- Layer thickness is used as a vertical integration weight in computing steric height.
- The routine supports optional debugging output, including:
  - Original and rescaled SSH increment
  - Computed steric height using 3 alternative formulations
- This constraint ensures the increment does not introduce unrealistically large SSH adjustments that could degrade ocean model balance or lead to unrealistic surface gravity waves.

### 3. **Hard Bounds Enforcement**

- Brute-force check to make sure analysis values of temperature and salinity remain within defined minimum and maximum values.
- Adjusts the increment field accordingly.

## Required Configuration Parameters

The `eckit::Configuration` object must include:

```yaml
state bounds:
  sea_water_potential_temperature: [min_temp, max_temp]
  sea_water_salinity: [min_salt, max_salt]

increment max:
  steric: 0.5  # Maximum allowed steric height increment [m]

increment stability iterations: 5
min stable density gradient: 1e-4
steric increment:
  linear variable changes:
  - linear variable change name: BalanceSOCA
```