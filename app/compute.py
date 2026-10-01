"""
app/compute.py
==============
Scientific computation module for ComputeGrid.

This module houses isolated computational workloads. It is decoupled from
database models, Redis queues, and worker lifecycle logic.
"""

from typing import Any, Callable
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


def run_matrix_multiply(input_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Perform matrix multiplication on two random NxN matrices using NumPy.

    Parameters:
        input_data (dict, optional): Dictionary containing job parameters.
            - "size" (int): Dimension of the NxN square matrices (default: 100).

    Returns:
        dict: Plain Python dictionary containing JSON-serializable results:
            - "shape": [N, N]
            - "mean": float
            - "std": float
            - "min": float
            - "max": float
    """
    if input_data is None:
        input_data = {}

    size = int(input_data.get("size", 100))
    if size <= 0:
        raise ValueError("Matrix size must be a positive integer.")

    # Generate two random NxN matrices
    matrix_a = np.random.rand(size, size)
    matrix_b = np.random.rand(size, size)

    # Multiply the two matrices
    result = np.matmul(matrix_a, matrix_b)

    return {
        "shape": list(result.shape),
        "mean": round(float(np.mean(result)), 6),
        "std": round(float(np.std(result)), 6),
        "min": round(float(np.min(result)), 6),
        "max": round(float(np.max(result)), 6),
    }


def run_data_stats(input_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Perform 1D dataset statistical computations using NumPy.

    Parameters:
        input_data (dict, optional): Dictionary containing job parameters.
            - "size" (int): Number of elements in the 1D dataset (default: 1000).

    Returns:
        dict: Plain Python dictionary containing JSON-serializable results:
            - "size": int
            - "mean": float
            - "std": float
            - "min": float
            - "max": float
            - "sum": float
            - "median": float
    """
    if input_data is None:
        input_data = {}

    size = int(input_data.get("size", 1000))
    if size <= 0:
        raise ValueError("Data size must be a positive integer.")

    # Generate a random 1D dataset
    data = np.random.rand(size)

    return {
        "size": int(data.size),
        "mean": round(float(np.mean(data)), 6),
        "std": round(float(np.std(data)), 6),
        "min": round(float(np.min(data)), 6),
        "max": round(float(np.max(data)), 6),
        "sum": round(float(np.sum(data)), 6),
        "median": round(float(np.median(data)), 6),
    }


DISPATCH_TABLE: dict[str, Callable[[dict[str, Any] | None], dict[str, Any]]] = {
    "matrix_stats": run_matrix_stats,
    "matrix_multiply": run_matrix_multiply,
    "data_stats": run_data_stats,
}


def dispatch_job(job_type: str, input_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Dispatch a compute job to the appropriate workload function.

    Parameters:
        job_type (str): The identifier of the computation workload to run.
        input_data (dict, optional): Parameters passed to the workload.

    Returns:
        dict: Plain Python dictionary containing JSON-serializable computation results.

    Raises:
        ValueError: If job_type is unsupported.
    """
    job_handler = DISPATCH_TABLE.get(job_type)
    if job_handler is None:
        raise ValueError(f"Unsupported job type: {job_type}")

    return job_handler(input_data)

