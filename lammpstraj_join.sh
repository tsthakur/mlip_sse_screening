#!/bin/bash

# Function to join LAMMPS trajectory files in a given directory
# or in batch_?? directories if no directory is specified

# Check if f1 and f2 are provided as arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <f1> <f2> [directory1] [directory2] ..."
    echo "  f1, f2: trajectory file suffixes to join"
    echo "  If no directories specified, will process all batch_?? directories"
    exit 1
fi

f1=$1
f2=$2
shift 2  # Remove f1 and f2 from the argument list

join_lammpstrj_in_dir() {
    local dir=$1
    echo "Processing directory: $dir"
    
    local original_dir=$(pwd)
    cd "$dir" || return 1

    for file in *.lammpstrj; do
        if [[ "$file" != *"__"* ]]; then
            formula="${file%.lammpstrj}"
            echo "Processing formula: $formula"
            file1="${formula}__${f1}.lammpstrj"
            file2="${formula}__${f2}.lammpstrj"
            output="${formula}__${f1}${f2}.lammpstrj"
            
            if [[ -f "$file2" ]]; then
                total_lines=$(wc -l < "$file")
                num_steps=$(grep "ITEM: TIMESTEP" "$file" | wc -l)
                lines_per_step=$((total_lines / num_steps))

                end_step=$(( $(tail -n $lines_per_step $file1 | head -2 | tail -1) / 50 ))

                start_step=$(( $(head -2 "$file2" | tail -1) / 50 ))

                repeated_steps=$((end_step - start_step + 1))
                
                lines_to_remove=$((repeated_steps * lines_per_step))

                echo "Removing $repeated_steps steps"
                
                temp_output="${output}.tmp"
                head -n -"$lines_to_remove" "$file1" > "$temp_output"
                cat "$temp_output" "$file2" > "$output"
                rm "$temp_output"
                echo "Created $output"
            fi
        fi
    done
    
    cd "$original_dir"
}

# Process directories
if [ $# -eq 0 ]; then
  # No directories specified, process all batch_?? directories
  for d in batch_??; do
    [ -d "$d" ] || continue
    join_lammpstrj_in_dir "$d"
  done
else
  # Process specified directories
  for d in "$@"; do
    [ -d "$d" ] && join_lammpstrj_in_dir "$d"
  done
fi