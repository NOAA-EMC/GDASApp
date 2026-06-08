# SocaDiagB: Standalone Parametric Background Error Estimation Tool

This standalone application estimates the **variance of unbalanced variables** for ocean and sea-ice components in GDAS, using a **variance partitioning method** combined with a **vertical exponential decay model**.

The application requires only the background state and mesh geometry to produce a flow-dependent variance estimate that is **ensemble-free**, localized, and tunable via a YAML configuration file.

---

## Formulation

### Overview

The application computes:

$$
\sigma_D^2(x, y, z) = \sigma_\text{dyn}^2(x, y, z) + \sigma_\text{static}^2(x, y, z)
$$

where:
- $\sigma_D^2$: total background error variance at horizontal location $x$ and vertical level $z$
- $\sigma_\text{dyn}^2$: flow-dependent variance computed from local stencils of the background
- $\sigma_\text{static}^2$: static background error, modulated vertically

---
### Step 1: Iterative Local Variance Estimation

To estimate the flow-dependent component of the background error variance, the application computes local statistical moments using a **fixed-radius neighborhood** combined with **iterative smoothing**.

#### Neighborhood Definition

At each node `i` and vertical level `z`, a local neighborhood `N(i, z)` is defined as a set of grid point indices:
- The central node and its **immediate horizontal neighbors** (1-ring stencil) obtained via mesh connectivity
- Vertical levels that fall within a configurable **depth bin** around the current depth, scaled by the local layer thickness

This neighborhood remains fixed throughout the calculation. Instead of expanding it, the application **repeatedly smooths the moments** to implicitly extend the spatial support.

**Why iterative smoothing?** The iterative approach offers several advantages over explicitly expanding the neighborhood radius:
1. **Memory efficiency**: Only the immediate neighbors need to be stored and accessed, rather than maintaining large multi-ring stencils
2. **Numerical stability**: The Chan et al. (1983) variance algorithm is numerically stable when applied iteratively over local neighborhoods
3. **Tunable spatial scale**: Each iteration implicitly extends the spatial influence by approximately one grid spacing, allowing the effective correlation length scale to be tuned through the choice of `K`, though the exact relationship depends on grid geometry
4. **Computational efficiency**: The cost scales linearly with the number of iterations rather than quadratically with the support radius
5. **Mesh adaptivity**: Works naturally on unstructured grids where multi-ring connectivity becomes complex

#### Iterative Smoothing

Let `x_b(i, z)` be the background field value at node `i` and level `z`.

The algorithm initializes two fields:
- $sum_1(i, z) = x_b(i, z)$
- $sum_2(i, z) = x_b(i, z)^2$

It then performs `K` iterations of smoothing:

1. At each iteration:
   - Apply halo exchange to ensure updated neighbor values are available
   - At each node and level, compute the mean of $sum_1$ and $sum_2$ across neighbor indices in $N(i, z)$
   - Store the smoothed result back in-place

2. After `K` iterations, the local mean and second moment are approximated as:

$$
\mu_K(i, z) = \frac{1}{n(i,z)} \sum_{j \in N(i,z)} \text{sum}_1(j, z)
$$

$$
E_K[x_b^2](i, z) = \frac{1}{n(i,z)} \sum_{j \in N(i,z)} \text{sum}_2(j, z)
$$

where $n(i,z)$ is the number of grid points in the neighborhood $N(i,z)$.

3. The dynamic background error variance is then estimated as:

$$
\sigma_{dyn}^2(i, z) = E_K[x_b^2](i, z) - \mu_K(i, z)^2
$$

This process produces a spatially smoothed estimate of the variance at each node and depth level, incorporating progressively more distant influence through the iterative application of local averaging — without explicitly expanding the neighborhood.

---

### Step 2: Vertical Exponential Decay

To impose vertical correlation structure, we apply a **Gaspari-Cohn shaped decay** to the dynamic variance using a depth-dependent e-folding scale:

$$
\sigma_\text{dyn}(x, z) \leftarrow \sigma_\text{dyn}(x, z) \cdot r_\text{dyn}(x, z)
$$

where:

$$
r_\text{dyn}(x, z) = \text{GC99}\left( \frac{z}{L_\text{dyn}(x)} \right)
$$

with:

- $\text{GC99}(r)$: Gaspari-Cohn taper function
- $L_\text{dyn}(x) = \min\left( \frac{h(x)}{\text{minRatio}}, L_{\text{efold, dyn}} \right) / 0.316$
- $h(x)$: local bathymetry

The same is done for the static component:

$$
\sigma_\text{static}(x, z) = \sigma_\text{static,0} \cdot r_\text{static}(x, z)
$$

and the total unbalanced background error variance is:

$$
\sigma_D^2(x, z) = \sigma_\text{dyn}^2(x, z) + \sigma_\text{static}^2(x, z)
$$

---

## Inputs

- `background`: background state file (IODA-style, must contain cell thickness and physical variables)
- `geometry`: input mesh/geometry configuration
- `output geometry` (optional): where to interpolate the resulting B
- `background error`: output path for storing the final B fields
- Configuration parameters:
  - `stencil growth iterations`: number of halo stencil expansions
  - `vertical bin size`: controls vertical stencil extent
  - `rescale static`, `rescale dynamic`: multiplicative factors for tuning
  - `vertical e-folding scale static/dynamic`: base vertical decay length
  - `min efold depth ratio`: floor on depth/e-folding ratio
  - `static sig B.sigT`, `.sigS`, `.sigSic`: default static stddev for each variable

---

## Output

- NetCDF file containing $\sigma_B(x, z)$ for all variables listed in the config, interpolated to the output geometry if provided.

---

## Example Usage

```yaml
date: 2025-06-01T00:00:00Z

variables:
  name: [sea_water_potential_temperature, sea_water_salinity, sea_ice_area_fraction, sea_water_cell_thickness]

geometry:
  geom_grid_file: soca_gridspec.nc
  mom6_input_nml: input.nml
  fields metadata: fields_metadata.yaml

background:
  read_from_file: 1
  basename: ./
  ocn_filename: ocean.bkg.nc
  ice_filename: ice.bkg.nc
  date: 2025-06-01T03:00:00Z
  file: background_state.nc

background error:
  datadir: ./
  date: 2025-06-01T00:00:00Z'
  exp: bkgerr_parametric
  type: incr

stencil growth iterations: 2
vertical bin size: 1.0
vertical e-folding scale static: 300.0
vertical e-folding scale dynamic: 300.0
min efold depth ratio: 3.0
rescale static: 1.0
rescale dynamic: 1.0
static sig B.sigT: 0.5
static sig B.sigS: 0.1
static sig B.sigSic: 0.01
```
## 📚 References

- Keppenne, C. L., Rienecker, M. M., Kovach, R. M., & Vernieres, G. (2013).
  *Ensemble Data Assimilation without Ensembles: Methodology and Application to Ocean Data Assimilation*.
  NASA Technical Memorandum NASA/TM-2013-104606.
  [https://ntrs.nasa.gov/api/citations/20140011280/downloads/20140011280.pdf](https://ntrs.nasa.gov/api/citations/20140011280/downloads/20140011280.pdf)

- Chan, T. F., Golub, G. H., & LeVeque, R. J. (1983).
  *Algorithms for computing the sample variance: Analysis and recommendations*.
  The American Statistician, **37**(3), 242–247.
  https://doi.org/10.1080/00031305.1983.10483115

- Gaspari, G., & Cohn, S. E. (1999).
  *Construction of correlation functions in two and three dimensions*.
  Quarterly Journal of the Royal Meteorological Society, **125**(554), 723–757.
  https://doi.org/10.1002/qj.49712555417

> ⚙️ The iterative local variance estimation method used in this application was inspired by the SAFE/FAST methodology introduced in Keppenne et al. (2013). While our approach differs in implementation — using fixed stencils and iterative smoothing rather than time-lagged regression — the underlying idea of extracting flow-dependent error structure from a single model trajectory directly traces back to their work. The iterative averaging algorithm for computing variance follows the principles described in Chan et al. (1983), where repeated local averaging over fixed neighborhoods provides a numerically stable approach to spatial variance estimation without requiring explicit storage of all neighboring values.
