"""
app/compute.py
==============
Scientific computation module for ComputeGrid.

This module houses isolated computational workloads. It is decoupled from
database models, Redis queues, and worker lifecycle logic.
"""

from typing import Any
import numpy as np


def run_matrix_stats(input_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Perform statistical computations on a random 2D matrix using NumPy.

    Parameters:
        input_data (dict, optional): Dictionary containing job parameters.
            - "size" (int): Dimension of the NxN square matrix (default: 100).

    Returns:
        dict: Plain Python dictionary containing JSON-serializable results:
            - "shape": [N, N]
            - "mean": float
            - "std": float
            - "min": float
            - "max": float
            - "sum": float
    """
    if input_data is None:
        input_data = {}

    size = int(input_data.get("size", 100))
    if size <= 0:
        raise ValueError("Matrix size must be a positive integer.")

    # Generate a random matrix of uniform distribution [0.0, 1.0)
    matrix = np.random.rand(size, size)

    return {
        "shape": list(matrix.shape),
        "mean": round(float(np.mean(matrix)), 6),
        "std": round(float(np.std(matrix)), 6),
        "min": round(float(np.min(matrix)), 6),
        "max": round(float(np.max(matrix)), 6),
        "sum": round(float(np.sum(matrix)), 6),
    }
