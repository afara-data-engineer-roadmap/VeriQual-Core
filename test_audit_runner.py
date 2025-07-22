import os
import pytest
from VeriQual_Core.audit_runner import AuditRunner
def test_audit_runner_valid_config(tmp_path):
    dummy_file = tmp_path / "valid.csv"
    dummy_file.write_text("col1,col2\n1,2\n3,4")

    config = {
        "file_config": {
            "filepath": str(dummy_file)
        },
        "checks_config": {
            "check_f01_struct": True
        }
    }

    runner = AuditRunner(config)
    assert runner.filepath == str(dummy_file)
    assert runner.checks.check_f01_struct is True
    assert isinstance(runner.profile, dict)

def test_audit_runner_invalid_config():
    invalid_config = {
        "file_config": {
            "filepath": 123  # Erreur : doit être une chaîne
        }
    }

    with pytest.raises(ValueError) as exc_info:
        AuditRunner(invalid_config)

    assert "Configuration invalide" in str(exc_info.value)

def test_run_audit_file_not_found():
    config = {
        "file_config": {
            "filepath": "fichier_inexistant.csv"
        }
    }

    runner = AuditRunner(config)
    result = runner.run_audit()

    assert "structural_errors" in result
    assert len(result["structural_errors"]) == 1
    assert "fichier_inexistant.csv" in result["structural_errors"][0]
    
from unittest import mock

def test_run_audit_file_not_readable_windows(tmp_path):
    fake_file = tmp_path / "protected.csv"
    fake_file.write_text("data")

    config = {
        "file_config": {
            "filepath": str(fake_file)
        }
    }

    with mock.patch("os.access", return_value=False):
        runner = AuditRunner(config)
        result = runner.run_audit()

        assert "structural_errors" in result
        assert any("lecture" in msg.lower() for msg in result["structural_errors"])
