"""
Generate LAMMPS input files from pymatgen structures using templates.

Supports both initial runs and automated restart continuation by
scanning output directories for existing restart files.
"""

import os
import re
import glob

from pymatgen.core import Element
from pymatgen.io.lammps.data import LammpsData


class LammpsInputGenerator:
    """
    Generate LAMMPS input files for MD simulations from pymatgen structures.

    Uses template files to produce initial run inputs and restart inputs,
    with automatic run index detection from existing restart files.

    Run index convention:
        - Run 0 (initial): uses in.template, writes restart1 / restart2
        - Run N (restart): reads restart{2N}, writes restart{2N+1} / restart{2N+2}

    Parameters
    ----------
    structure : pymatgen.core.Structure
        The structure to simulate.
    output_dir : str
        Directory where LAMMPS files are written.
    template_dir : str, optional
        Directory containing in.template and in.template_restart.
        Defaults to the directory of this script.
    temperature : float, optional
        Simulation temperature in K. Defaults to 500.0.
        Timestep is set to 0.001 ps for T > 650 K, else 0.002 ps.
    simulation : int, optional
        Simulation production length in ps. Defaults to 1000 ps.
    extras : str, optional
        Suffix appended to the formula string (e.g. a supercell tag).
    """

    TIMESTEP_THRESHOLD = 650.0
    TIMESTEP_HIGH_T = 0.001
    TIMESTEP_LOW_T = 0.002

    def __init__(self, structure, output_dir, template_dir=None,
                 temperature=500.0, simulation=1000, extras=None):
        self.structure = structure
        self.output_dir = output_dir
        self.temperature = temperature
        self.simulation = simulation
        self.extras = extras

        if template_dir is None:
            template_dir = os.path.dirname(os.path.abspath(__file__))
        self.template_dir = template_dir

        self._elements = None
        self._formula = None

    @property
    def formula(self):
        """Composition string used for file naming (e.g. 'Li3ClO_700K')."""
        if self._formula is None:
            formula = self.structure.composition.iupac_formula.replace(' ', '')
            if self.extras:
                formula += self.extras
            formula = f'{formula}_{self.temperature:.0f}K'
            self._formula = formula
        return self._formula

    @property
    def elements(self):
        """Ordered list of unique element symbols, preserving site order."""
        if self._elements is None:
            seen = []
            for site in self.structure:
                sym = site.specie.symbol
                if sym not in seen:
                    seen.append(sym)
            self._elements = seen
        return self._elements

    @property
    def timestep(self):
        """Timestep in ps, chosen by temperature."""
        if self.temperature > self.TIMESTEP_THRESHOLD:
            return self.TIMESTEP_HIGH_T
        return self.TIMESTEP_LOW_T

    def detect_run_index(self):
        """
        Determine the next run index by scanning for restart files.

        Looks for files matching ``{formula}.restart*`` in ``output_dir``
        and returns the next run index based on the highest-numbered
        restart file found.

        Returns
        -------
        int
            0 if no restart files exist, otherwise (highest + 1) // 2.
        """
        pattern = os.path.join(self.output_dir, f'{self.formula}.restart*')
        restart_files = glob.glob(pattern)

        if not restart_files:
            return 0

        numbers = []
        for path in restart_files:
            basename = os.path.basename(path)
            match = re.search(r'\.restart(\d+)$', basename)
            if match:
                numbers.append(int(match.group(1)))

        if not numbers:
            return 0

        highest = max(numbers)
        return (highest + 1) // 2

    def generate(self, run_index=None):
        """
        Generate the LAMMPS input file for the given (or auto-detected) run.

        Parameters
        ----------
        run_index : int, optional
            Explicit run index. If None, calls :meth:`detect_run_index`.

        Returns
        -------
        str
            Path to the generated input file.
        """
        if run_index is None:
            run_index = self.detect_run_index()

        os.makedirs(self.output_dir, exist_ok=True)

        if run_index == 0:
            path = self._generate_initial(run_index)
        else:
            path = self._generate_restart(run_index)

        self._write_data_file()
        return path

    def _read_template(self, name):
        path = os.path.join(self.template_dir, name)
        with open(path, 'r') as f:
            return f.read()

    def _element_info(self):
        """Return mass lines, atomic number list, and symbol list."""
        masses = []
        numbers = []
        symbols = []
        for i, sym in enumerate(self.elements, 1):
            el = Element(sym)
            masses.append(f'mass {i} {float(el.atomic_mass)}')
            numbers.append(str(el.number))
            symbols.append(sym)
        return masses, numbers, symbols

    def _apply_common_replacements(self, content, run_index):
        """Substitutions shared by both initial and restart templates."""
        masses, numbers, symbols = self._element_info()

        content = content.replace('timestep-to-adapt', str(self.timestep))
        content = content.replace('simulation-to-adapt', str(self.simulation))
        content = content.replace(
            'temperature equal temperature-to-adapt',
            f'temperature equal {self.temperature}',
        )
        content = content.replace(
            'formula-to-adapt.log', f'{self.formula}_{run_index}.log',
        )
        content = content.replace(
            'formula-to-adapt.lammpstrj', f'{self.formula}_{run_index}.lammpstrj',
        )
        content = content.replace('mass mass-to-adapt', '\n'.join(masses))
        content = content.replace('atomic-number-to-adapt', ' '.join(numbers))
        content = content.replace('atomic-symbols-to-adapt', ' '.join(symbols))

        return content

    def _generate_initial(self, run_index):
        content = self._read_template('in.template')
        content = self._apply_common_replacements(content, run_index)

        content = content.replace(
            'formula-to-adapt.lmp', f'{self.formula}.lmp',
        )
        content = content.replace(
            'formula-to-adapt.restart1', f'{self.formula}.restart1',
        )
        content = content.replace(
            'formula-to-adapt.restart2', f'{self.formula}.restart2',
        )

        return self._write_input(content, run_index)

    def _generate_restart(self, run_index):
        content = self._read_template('in.template_restart')
        content = self._apply_common_replacements(content, run_index)

        read_from = 2 * run_index
        write_a = 2 * run_index + 1
        write_b = 2 * run_index + 2

        content = content.replace(
            'formula-to-adapt.restart26', f'{self.formula}.restart{read_from}',
        )
        content = content.replace(
            'formula-to-adapt.restart27', f'{self.formula}.restart{write_a}',
        )
        content = content.replace(
            'formula-to-adapt.restart28', f'{self.formula}.restart{write_b}',
        )

        return self._write_input(content, run_index)

    def _write_input(self, content, run_index):
        path = os.path.join(self.output_dir, f'in.{self.formula}_{run_index}')
        with open(path, 'w') as f:
            f.write(content)
        print(f'Created: {path}')
        return path

    def _write_data_file(self):
        path = os.path.join(self.output_dir, f'{self.formula}.lmp')
        if not os.path.exists(path):
            lammps_data = LammpsData.from_structure(
                self.structure, atom_style='atomic',
            )
            lammps_data.write_file(path)
            print(f'Created: {path}')


if __name__ == '__main__':
    # Example usage
    from aiida import orm, load_profile
    load_profile('fpmd')

    aiida_structure = orm.load_node('acff0e4a-6b1d-4ca6-a5c8-33bb481713aa')
    structure = aiida_structure.get_pymatgen()

    # structure.make_supercell([2, 2, 2])  # Example supercell
    
    gen = LammpsInputGenerator(
        structure=structure,
        output_dir='./lammps_runs',
        temperature=1000.0,
        simulation=2500,
        extras='',
    )
    # Auto-detect next run index and generate
    gen.generate()

    # Or explicitly generate a specific run
    # gen.generate(run_index=0)   # initial
    # gen.generate(run_index=3)   # 3rd restart
