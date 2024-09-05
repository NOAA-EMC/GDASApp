# GDASApp
Global Data Assimilation System Application

The one app to rule them all

## Notes to developers

1 - As a developer, you will have to build the GDASApp againt the up to date `develop` branch of the `global-workflow`

```bash
git clone --recursive --jobs 8 https://github.com/NOAA-EMC/global-workflow.git
```

2 - To trigger the "fast" GDASApp tests: add the label **`{machine}-GW-RT`**

3 - To trigger all the GDASApp tests, including the tier-2 testing (subset of the global-workflow ci): add the labels **`{machine}-GW-RT`** and **`{machine}-GW-RT-tier2`**

4 - If your feature development involves changes to the `global-workflow` and the `GDASApp`, you will have to issue a PR in each repository. The `GDASApp` PR will have to have the same name in order for the `GDASApp` CI to build and run the correct branches.

5 - If your work is contained within the `global-workflow` only, you will have to submit a dummy PR in the `GDASApp` with the same branch name.
To submit a dummy PR, just create a branch with an empty commit:
```
git commit --allow-empty -m "Dummy commit to trigger PR"
```


[![Orion](https://github.com/NOAA-EMC/GDASApp/actions/workflows/orion.yaml/badge.svg)](https://github.com/NOAA-EMC/GDASApp/actions/workflows/orion.yaml)
[![Hera](https://github.com/NOAA-EMC/GDASApp/actions/workflows/hera.yaml/badge.svg)](https://github.com/NOAA-EMC/GDASApp/actions/workflows/hera.yaml)

[![Unit Tests on GitHub CI](https://github.com/NOAA-EMC/GDASApp/actions/workflows/unittests.yaml/badge.svg)](https://github.com/NOAA-EMC/GDASApp/actions/workflows/unittests.yaml)
[![Coding Norms](https://github.com/NOAA-EMC/GDASApp/actions/workflows/norms.yaml/badge.svg)](https://github.com/NOAA-EMC/GDASApp/actions/workflows/norms.yaml)
