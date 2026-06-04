import json
import re
from pathlib import Path

def convert_py_to_ipynb(py_path, ipynb_path):
    py_path = Path(py_path)
    ipynb_path = Path(ipynb_path)
    
    with open(py_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    cells = []
    current_cell_type = None
    current_cell_lines = []
    
    for line in lines:
        # Check if line is a cell separator
        if line.startswith('# %%'):
            # Save the previous cell
            if current_cell_type is not None:
                cells.append({
                    "cell_type": current_cell_type,
                    "metadata": {},
                    "source": current_cell_lines
                })
            
            # Determine new cell type
            if '[markdown]' in line:
                current_cell_type = 'markdown'
            else:
                current_cell_type = 'code'
                
            current_cell_lines = []
        else:
            # If we haven't seen a cell separator yet, assume code cell
            if current_cell_type is None:
                current_cell_type = 'code'
                
            if current_cell_type == 'markdown':
                # Remove leading '#' and optional space from markdown cells
                if line.startswith('# '):
                    processed_line = line[2:]
                elif line.startswith('#'):
                    processed_line = line[1:]
                else:
                    processed_line = line
                current_cell_lines.append(processed_line)
            else:
                current_cell_lines.append(line)
                
    # Save the last cell
    if current_cell_type is not None:
        cells.append({
            "cell_type": current_cell_type,
            "metadata": {},
            "source": current_cell_lines
        })
        
    # Clean up empty cells and format cells
    cleaned_cells = []
    for cell in cells:
        # For code cells, add outputs and execution_count fields
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
            
        # Only add cell if it has non-empty source
        if cell["source"]:
            cleaned_cells.append(cell)
            
    notebook = {
        "cells": cleaned_cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }
    
    ipynb_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ipynb_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=1, ensure_ascii=False)
        
    print(f"Successfully converted {py_path} to {ipynb_path} with {len(cleaned_cells)} cells.")

if __name__ == '__main__':
    convert_py_to_ipynb('atlas_experiment.py', 'notebooks/atlas_experiment.ipynb')
