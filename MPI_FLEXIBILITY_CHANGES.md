# MPI Flexibility Changes for gdas_fv3jedi_calc_scf_to_ioda.cc

## Overview

This document describes the changes made to `gdas_fv3jedi_calc_scf_to_ioda.cc` to remove the hardcoded limitation of exactly 6 MPI tasks and enable flexible MPI parallelization for high-resolution model configurations.

## Problem

Previously, the code enforced `comm_.size() == 6`, assuming a 1:1 mapping between MPI processes and FV3 cube sphere tiles. This limited scalability for high-resolution models requiring more than 6 MPI tasks.

## Solution

### Key Changes

1. **Removed MPI Size Restriction**
   ```cpp
   // OLD: Hard failure if not exactly 6 tasks
   if (comm_.size() != 6) {
     throw eckit::BadValue("MPI rank size must be 6", Here());
   }
   
   // NEW: Supports any number of MPI tasks
   // Note: This code now supports any number of MPI tasks
   // The FV3 cube sphere has 6 tiles, but tasks can be distributed across tiles
   ```

2. **Local Data Structures**
   ```cpp
   // OLD: Allocate arrays for all 6 tiles on every process
   this->scfIMS.resize(6, std::vector<std::vector<float>>(...));
   
   // NEW: Each process allocates only its local portion
   this->scfIMS.resize(1, std::vector<std::vector<float>>(...));
   ```

3. **Proper Index Conversion**
   ```cpp
   // OLD: Used global indices directly (caused bounds errors)
   this->scfIMS[tilenum][fv3_j][fv3_i] = value;
   
   // NEW: Convert global to local indices
   size_t local_i = fv3_i - (indices[0] - 1);
   size_t local_j = fv3_j - (indices[2] - 1);
   this->scfIMS[0][local_j][local_i] = value;
   ```

4. **Atlas-Based MPI Communication**
   ```cpp
   // OLD: Manual MPI gathering with hardcoded assumptions
   std::vector<float> snd_global(ngrid * 6, 9999.0f);
   std::vector<int> counts(6, ngrid);
   oops::mpi::world().gatherv(snd_mytile, snd_global, counts, gdispls, 0);
   
   // NEW: Use atlas field gathering (handles any MPI distribution)
   atlas::Field sndLocal = fs.createField<float>(atlas::option::name("snd_ims"));
   atlas::Field sndGlobal = fs.createField<float>(...::global());
   fs_new.gather(local_fields, global_fields);
   ```

### MPI Distribution Examples

#### Before (6 tasks only):
```
Rank 0 → Tile 1    Rank 1 → Tile 2    Rank 2 → Tile 3
Rank 3 → Tile 4    Rank 4 → Tile 5    Rank 5 → Tile 6
```

#### After (flexible):
```
6 tasks:   Rank 0→Tile 1, Rank 1→Tile 2, ..., Rank 5→Tile 6
12 tasks:  Ranks 0-1→Tile 1, Ranks 2-3→Tile 2, ..., Ranks 10-11→Tile 6  
24 tasks:  Ranks 0-3→Tile 1, Ranks 4-7→Tile 2, ..., Ranks 20-23→Tile 6
```

## Benefits

- **Scalability**: Supports any number of MPI tasks (6, 12, 24, 48, etc.)
- **Performance**: Better parallelization for high-resolution configurations
- **Robustness**: Leverages proven atlas MPI infrastructure
- **Compatibility**: Maintains backward compatibility with existing 6-task workflows

## Testing

Core logic validated with unit tests covering:
- Local/global index conversion correctness
- Data structure sizing changes
- Tile mapping logic

## Usage

No changes required for users. The tool now automatically adapts to any MPI configuration provided by the FV3-JEDI geometry system.

Example configurations that now work:
```bash
# Previous limitation (still works)
mpirun -n 6 gdas_fv3jedi_scf_to_ioda.x config.yaml

# New capabilities  
mpirun -n 12 gdas_fv3jedi_scf_to_ioda.x config.yaml   # 2 tasks per tile
mpirun -n 24 gdas_fv3jedi_scf_to_ioda.x config.yaml   # 4 tasks per tile
mpirun -n 48 gdas_fv3jedi_scf_to_ioda.x config.yaml   # 8 tasks per tile
```