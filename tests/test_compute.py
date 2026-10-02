"""
tests/test_compute.py
=====================
Unit tests for app/compute.py.

All workloads use NumPy random generation, so results are non-deterministic.
Tests therefore verify:
  - Returned dict keys exactly match the documented interface.
  - Numeric fields are Python float (JSON-serializable, not np.float64).
  - Shape / size fields reflect the requested input dimension.
  - Values that are mathematically bounded (uniform [0, 1)) stay in range.
  - Invalid input raises the correct error type with the exact message.
"""

import pytest

from app.compute import (
    DISPATCH_TABLE,
    dispatch_job,
    run_data_stats,
    run_matrix_multiply,
    run_matrix_stats,
)


# ---------------------------------------------------------------------------
# run_matrix_stats
# ---------------------------------------------------------------------------

class TestRunMatrixStats:
    """Tests for run_matrix_stats()."""

    def test_returns_all_expected_keys(self):
        result = run_matrix_stats({"size": 10})
        assert set(result.keys()) == {"shape", "mean", "std", "min", "max", "sum"}

    def test_shape_matches_requested_size(self):
        result = run_matrix_stats({"size": 7})
        assert result["shape"] == [7, 7]

    def test_shape_is_plain_list(self):
        result = run_matrix_stats({"size": 5})
        assert isinstance(result["shape"], list)

    def test_numeric_fields_are_python_float(self):
        result = run_matrix_stats({"size": 5})
        for key in ("mean", "std", "min", "max", "sum"):
            assert isinstance(result[key], float), f"{key!r} is not a float"

    def test_uniform_distribution_bounds(self):
        """Uniform [0, 1) → min >= 0 and max < 1 for a reasonable matrix."""
        result = run_matrix_stats({"size": 50})
        assert result["min"] >= 0.0
        assert result["max"] < 1.0

    def test_mean_within_expected_range(self):
        """Mean of uniform [0, 1) should be close to 0.5."""
        result = run_matrix_stats({"size": 200})
        assert 0.0 < result["mean"] < 1.0

    def test_default_size_when_input_data_is_none(self):
        """Passing None should use the default size of 100."""
        result = run_matrix_stats(None)
        assert result["shape"] == [100, 100]

    def test_default_size_when_input_data_is_empty_dict(self):
        result = run_matrix_stats({})
        assert result["shape"] == [100, 100]

    def test_size_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="Matrix size must be a positive integer."):
            run_matrix_stats({"size": 0})

    def test_negative_size_raises_value_error(self):
        with pytest.raises(ValueError, match="Matrix size must be a positive integer."):
            run_matrix_stats({"size": -5})


# ---------------------------------------------------------------------------
# run_matrix_multiply
# ---------------------------------------------------------------------------

class TestRunMatrixMultiply:
    """Tests for run_matrix_multiply()."""

    def test_returns_all_expected_keys(self):
        result = run_matrix_multiply({"size": 10})
        assert set(result.keys()) == {"shape", "mean", "std", "min", "max"}

    def test_does_not_return_sum(self):
        """run_matrix_multiply deliberately omits 'sum' — verify that contract."""
        result = run_matrix_multiply({"size": 10})
        assert "sum" not in result

    def test_shape_matches_requested_size(self):
        result = run_matrix_multiply({"size": 8})
        assert result["shape"] == [8, 8]

    def test_shape_is_plain_list(self):
        result = run_matrix_multiply({"size": 5})
        assert isinstance(result["shape"], list)

    def test_numeric_fields_are_python_float(self):
        result = run_matrix_multiply({"size": 5})
        for key in ("mean", "std", "min", "max"):
            assert isinstance(result[key], float), f"{key!r} is not a float"

    def test_result_values_are_non_negative(self):
        """Product of two uniform [0, 1) matrices → all values >= 0."""
        result = run_matrix_multiply({"size": 30})
        assert result["min"] >= 0.0

    def test_default_size_when_input_data_is_none(self):
        result = run_matrix_multiply(None)
        assert result["shape"] == [100, 100]

    def test_default_size_when_input_data_is_empty_dict(self):
        result = run_matrix_multiply({})
        assert result["shape"] == [100, 100]

    def test_size_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="Matrix size must be a positive integer."):
            run_matrix_multiply({"size": 0})

    def test_negative_size_raises_value_error(self):
        with pytest.raises(ValueError, match="Matrix size must be a positive integer."):
            run_matrix_multiply({"size": -3})


# ---------------------------------------------------------------------------
# run_data_stats
# ---------------------------------------------------------------------------

class TestRunDataStats:
    """Tests for run_data_stats()."""

    def test_returns_all_expected_keys(self):
        result = run_data_stats({"size": 100})
        assert set(result.keys()) == {"size", "mean", "std", "min", "max", "sum", "median"}

    def test_size_field_matches_requested_size(self):
        result = run_data_stats({"size": 42})
        assert result["size"] == 42

    def test_size_field_is_plain_int(self):
        result = run_data_stats({"size": 10})
        assert isinstance(result["size"], int)

    def test_numeric_fields_are_python_float(self):
        result = run_data_stats({"size": 10})
        for key in ("mean", "std", "min", "max", "sum", "median"):
            assert isinstance(result[key], float), f"{key!r} is not a float"

    def test_uniform_distribution_bounds(self):
        """Uniform [0, 1) → min >= 0 and max < 1."""
        result = run_data_stats({"size": 500})
        assert result["min"] >= 0.0
        assert result["max"] < 1.0

    def test_median_within_expected_range(self):
        """Median of uniform [0, 1) should be close to 0.5."""
        result = run_data_stats({"size": 1000})
        assert 0.0 < result["median"] < 1.0

    def test_default_size_when_input_data_is_none(self):
        """Passing None should use the default size of 1000."""
        result = run_data_stats(None)
        assert result["size"] == 1000

    def test_default_size_when_input_data_is_empty_dict(self):
        result = run_data_stats({})
        assert result["size"] == 1000

    def test_size_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="Data size must be a positive integer."):
            run_data_stats({"size": 0})

    def test_negative_size_raises_value_error(self):
        with pytest.raises(ValueError, match="Data size must be a positive integer."):
            run_data_stats({"size": -1})


# ---------------------------------------------------------------------------
# dispatch_job
# ---------------------------------------------------------------------------

class TestDispatchJob:
    """Tests for dispatch_job() routing logic."""

    def test_dispatch_table_contains_all_expected_workloads(self):
        assert set(DISPATCH_TABLE.keys()) == {"matrix_stats", "matrix_multiply", "data_stats"}

    def test_dispatches_matrix_stats(self):
        result = dispatch_job("matrix_stats", {"size": 5})
        assert result["shape"] == [5, 5]
        assert "mean" in result

    def test_dispatches_matrix_multiply(self):
        result = dispatch_job("matrix_multiply", {"size": 5})
        assert result["shape"] == [5, 5]
        assert "mean" in result

    def test_dispatches_data_stats(self):
        result = dispatch_job("data_stats", {"size": 50})
        assert result["size"] == 50
        assert "median" in result

    def test_unsupported_job_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported job type: unknown_workload"):
            dispatch_job("unknown_workload")

    def test_unsupported_job_type_error_includes_job_type_name(self):
        """Verify the error message format embeds the bad job_type string."""
        bad_type = "not_a_real_workload"
        with pytest.raises(ValueError, match=bad_type):
            dispatch_job(bad_type)

    def test_dispatch_passes_none_input_data_correctly(self):
        """dispatch_job with no input_data argument should still succeed."""
        result = dispatch_job("matrix_stats")
        assert result["shape"] == [100, 100]

    def test_dispatch_passes_custom_input_data(self):
        result = dispatch_job("data_stats", {"size": 7})
        assert result["size"] == 7
