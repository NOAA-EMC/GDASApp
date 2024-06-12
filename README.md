# GDASApp
Global Data Assimilation System Application

The one app to rule them all

## Notes to developers

1 - As a developer, you will have to build the GDASApp againt the `dev/gdasapp` branch of the `global-workflow`

```bash
git clone --recursive --jobs 8 --branch dev/gdasapp https://github.com/NOAA-EMC/global-workflow.git
```

2 - For the most part (boundaries of that terminology is stil TBD), changes to the `global-workflow` related to the `GDASApp` developement will be issed in the `dev/gdasapp` branch.


[![Orion](https://github.com/NOAA-EMC/GDASApp/actions/workflows/orion.yaml/badge.svg)](https://github.com/NOAA-EMC/GDASApp/actions/workflows/orion.yaml)
[![Hera](https://github.com/NOAA-EMC/GDASApp/actions/workflows/hera.yaml/badge.svg)](https://github.com/NOAA-EMC/GDASApp/actions/workflows/hera.yaml)

[![Unit Tests on GitHub CI](https://github.com/NOAA-EMC/GDASApp/actions/workflows/unittests.yaml/badge.svg)](https://github.com/NOAA-EMC/GDASApp/actions/workflows/unittests.yaml)
[![Coding Norms](https://github.com/NOAA-EMC/GDASApp/actions/workflows/norms.yaml/badge.svg)](https://github.com/NOAA-EMC/GDASApp/actions/workflows/norms.yaml)
