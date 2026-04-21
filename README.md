# Screening solid-state electrolytes with a fine-tuned MLIP

Scripts to run LAMMPS molecular dynamics simulations to screen solid-state
electrolyte candidates using a fine-tuned machin learning interatomic potential (MLIP) (`mixed_kpoints_lora_v3.pt`).

## Contents

- [lammps_input_generator.py](lammps_input_generator.py) - `LammpsInputGenerator` class that produces LAMMPS input and data files from a pymatgen `Structure`. Auto-detects the next run index by scanning the output directory for existing `*.restart*` files.
- [in.template](in.template) - LAMMPS input template for the first run. NVT equilibration from 300 K to the target temperature followed by a production run at constant temperature; writes `restart1` / `restart2`.
- [in.template_restart](in.template_restart) - LAMMPS input template for  runs. Reads from `restart{2N}` and writes `restart{2N+1}` / `restart{2N+2}`.
- [lammpstraj_join.sh](lammpstraj_join.sh) - concatenates two trajectory segments (`<formula>__<f1>.lammpstrj` + `<formula>__<f2>.lammpstrj`), stripping the overlapping timesteps. Operates on a given directory or on every `batch_??` directory by default.
- [options.yaml](options.yaml) - input file for fine-tuning PET-MAD with metatrain.
- [mixed_kpoints_lora_v3.ckpt](mixed_kpoints_lora_v3.ckpt) - Fine-tuned model used in the screening provided for reference

## Installation

Either follow the official installation instructions from
  - metatrain: https://docs.metatensor.org/metatrain/latest/installation.html
  - PET-MAD: https://github.com/lab-cosmo/upet/blob/main/docs/README_OLD.md

Or refer to the following instructions for a minimum install to train and run MD simulations:

```
conda create -n metatensor python==3.12 -c conda-forge
conda activate metatensor
conda install jupyter "numpy<2" "scipy<1.14" ase matplotlib pymatgen -c conda-forge
pip install "torch==2.7.1" --index-url https://download.pytorch.org/whl/cu126
pip install "metatrain==2025.10"
pip install "pet-mad>=1.2.0"
conda install -c metatensor -c conda-forge "lammps-metatomic=*=*nompi*"
conda install mkl -c conda-forge
mtt export https://huggingface.co/lab-cosmo/pet-mad/resolve/v1.0.2/models/pet-mad-v1.0.2.ckpt
mtt export mixed_kpoints_lora_v3.ckpt
```
## Usage

For training, first prepare the .xyz files by mixing our training data
with a small part of MAD dataset.

For MD simulations:

```python
from lammps_input_generator import LammpsInputGenerator

gen = LammpsInputGenerator(
    structure=structure,      # pymatgen Structure
    output_dir='./lammps_runs',
    temperature=500.0,
)
gen.generate()                # auto-detects run index from restart files
```

To join the trajectories: 

```bash
./lammpstraj_join.sh 0 1              # join across all batch_?? dirs
./lammpstraj_join.sh 0 1 run_dir/     # join in a specific directory
```
