## Simple Observation Space Statistics
A quick way to generate o-b stats and compare experiments
```
python gdassoca_obsstats.py --exps .../COMROOT/cp1 .../COMROOT/cp2 --inst '*' --dirout cp1vscp2
```
The above will generate time series of o-b RMSEs, Bias, and obs count for multiple regions. It will also generate an HTML document to facilitate viewing figures.

---

## How to generate the EVA and State space figures

#### Create a scratch place to run `run_vrfy.py`. This script will generate a bunch of sbatch scripts and logs.
```
mkdir /somewhere/scratch
cd /somewhere/scratch
ln -s /path/to/run_vrfy.py .   # to be sorted out properly in the future
cp /path/to/vrfy_config.yaml .
module use ...
module load EVA/....
```
---
#### Edit `vrfy_config.yaml`
It's actually read as a jinja template to render `pslot` if necessary. Anything that is a templated variable in `vrfy_jobcard.sh.j2` can be added to the yaml below.
```yaml
pslot: "nomlb"
start_pdy: '20210701'
end_pdy: '20210701'
cycs: ["00", "06", "12", "18"]
run: "gdas"
homegdas: "/work2/noaa/da/gvernier/runs/mlb/GDASApp"
base_exp_path: "/work2/noaa/da/gvernier/runs/mlb/{{ pslot }}/COMROOT/{{ pslot }}"
plot_ensemble_b: "OFF"
plot_parametric_b: "OFF"
plot_background: "OFF"
plot_increment: "ON"
plot_analysis: "OFF"
eva_plots: "ON"
qos: "batch"
hpc: "hercules"
eva_module: "EVA/orion"
```

---
#### Run the application
```python run_vrfy.py vrfy_config.yaml```
This will generate and submit the job cards for all the **cycles** defined by `cycs`, from `start_pdy` to `end_pdy`.

