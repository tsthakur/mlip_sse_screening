# mlip_sse_screening

Scripts to run LAMMPS molecular dynamics simulations to screen solid-state
electrolyte candidates using a fine-tuned machin learning interatomic potential (MLIP) (`mixed_kpoints_lora_v3.pt`).

## Contents

- [lammps_input_generator.py](lammps_input_generator.py) — `LammpsInputGenerator` class that produces LAMMPS input and data files from a pymatgen `Structure`. Auto-detects the next run index by scanning the output directory for existing `*.restart*` files.
- [in.template](in.template) — LAMMPS input template for the first run. NVT equilibration from 300 K to the target temperature followed by a production run at constant temperature; writes `restart1` / `restart2`.
- [in.template_restart](in.template_restart) — LAMMPS input template for  runs. Reads from `restart{2N}` and writes `restart{2N+1}` / `restart{2N+2}`.
- [lammpstraj_join.sh](lammpstraj_join.sh) — concatenates two trajectory segments (`<formula>__<f1>.lammpstrj` + `<formula>__<f2>.lammpstrj`), stripping the overlapping timesteps. Operates on a given directory or on every `batch_??` directory by default.

## Usage

```python
from lammps_input_generator import LammpsInputGenerator

gen = LammpsInputGenerator(
    structure=structure,      # pymatgen Structure
    output_dir='./lammps_runs',
    temperature=500.0,
)
gen.generate()                # auto-detects run index from restart files
```

```bash
./lammpstraj_join.sh 0 1              # join across all batch_?? dirs
./lammpstraj_join.sh 0 1 run_dir/     # join in a specific directory
```
