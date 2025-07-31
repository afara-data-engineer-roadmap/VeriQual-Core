import os
import pytest
from unittest.mock import patch
import json
import pandas as pd


from VeriQual_Core.audit_runner import AuditRunner


def test_run_audit_file_not_found():
    runner = AuditRunner(filepath="fichier_inexistant.csv")
    result = runner.run_audit()

    assert "structural_errors" in result
    assert len(result["structural_errors"]) == 1
    error = result["structural_errors"][0]
    assert error["error_code"] == "file_not_found"
    assert error["is_blocking"] is True


def test_run_audit_file_unreadable(tmp_path):
    fake_file = tmp_path / "unreadable.csv"
    fake_file.write_text("some,data\n1,2")

    with patch("os.access", return_value=False):
        runner = AuditRunner(filepath=str(fake_file))
        result = runner.run_audit()

    assert "structural_errors" in result
    error = result["structural_errors"][0]
    assert error["error_code"] == "file_unreadable"
    assert error["is_blocking"] is True

def test_run_audit_encoding_undetectable(tmp_path):
    # Création d’un fichier binaire illisible
    binary_file = tmp_path / "corrupt.csv"
    binary_file.write_bytes(b"\x93\xfa\x96\x7b\x00\xff\xfe\xfa\xfb")  # octets non UTF-8

    runner = AuditRunner(filepath=str(binary_file))
    result = runner.run_audit()

    assert "structural_errors" in result
    error = result["structural_errors"][0]
    assert error["error_code"] == "encoding_undetectable"
    assert error["is_blocking"] is True

def test_run_audit_file_empty_content(tmp_path):
    empty_content_file = tmp_path / "spaces_only.csv"
    empty_content_file.write_text("\n \r\t\n\n    ")  # contenu vide sémantiquement

    runner = AuditRunner(filepath=str(empty_content_file))
    result = runner.run_audit()

    assert "structural_errors" in result
    error = result["structural_errors"][0]
    assert error["error_code"] == "file_empty_content"
    assert error["is_blocking"] is True

def test_run_audit_success_minimal(tmp_path):
    valid_file = tmp_path / "valid.csv"
    valid_file.write_text("id,name\n1,Alice\n2,Bob\n")  # UTF-8 implicite

    runner = AuditRunner(filepath=str(valid_file))
    result = runner.run_audit()

    assert "structural_errors" in result
    assert result["structural_errors"] == []  # aucun échec
    assert result["file_info"]["detected_encoding"] in ["utf-8", "ascii"]
    assert result["file_info"]["encoding_confidence"] >= 0.0  # 0.0 (fallback) ou >0.0 (chardet fiable)
    # Vérifications F-01 (suite)
    assert result["file_info"]["total_rows"] == 2
    assert result["file_info"]["total_columns"] == 2
    assert result["file_info"]["detected_separator"] == ","
    # Vérifications F-02
    assert result["header_info"]["has_normalization_alerts"] is False
    assert result["header_info"]["header_map"] == {}


def test_detect_semicolon_separator(tmp_path):
    file_content = "Nom;Age;Ville\nAlice;30;Paris\nBob;25;Lyon\n"
    test_file = tmp_path / "semicolon_test.csv"
    test_file.write_text(file_content, encoding="utf-8")

    runner = AuditRunner(str(test_file))
    report = runner.run_audit()

    print(json.dumps(report, indent=2))
    assert report["file_info"]["detected_separator"] == ";"
    assert report["file_info"]["total_columns"] == 3
    assert report["file_info"]["total_rows"] == 2
    assert report["structural_errors"] == []


def test_non_rectangular_structure(tmp_path):
    file_content = "id,name\n1,alice\n2\n3,bob,paris"
    test_file = tmp_path / "non_rect.csv"
    test_file.write_text(file_content, encoding="utf-8")

    # Mock detect_csv_separator pour qu'il retourne un séparateur valide
    with patch("VeriQual_Core.audit_runner.detect_csv_separator") as mock_detect_separator:
        mock_detect_separator.return_value = (",", None) # Force le séparateur à être la virgule
        with patch("VeriQual_Core.audit_runner.load_dataframe_robustly") as mock_load_df:
            # Simuler un échec de parsing (structure non rectangulaire)
            mocked_message = "Message de test pour structure non rectangulaire."
            mock_load_df.return_value = (
                None,
                None,
                mocked_message,
                "non_rectangular_structure"
            )

            runner = AuditRunner(str(test_file))
            report = runner.run_audit()
            print(json.dumps(report, indent=2))

            assert report["structural_errors"][0]["error_code"] == "non_rectangular_structure"
            assert report["structural_errors"][0]["is_blocking"] is True
            assert report["structural_errors"][0]["message"] == mocked_message


def test_file_empty_after_header(tmp_path):
    file_content = "col1,col2\n" # En-tête mais pas de données
    test_file = tmp_path / "empty_after_header.csv"
    test_file.write_text(file_content, encoding="utf-8")

    runner = AuditRunner(str(test_file))
    report = runner.run_audit()
    print(json.dumps(report, indent=2))

    assert report["structural_errors"][0]["error_code"] == "file_empty_after_header"
    assert report["structural_errors"][0]["is_blocking"] is True
    assert "vide de données après l'en-tête" in report["structural_errors"][0]["message"]


def test_unicode_decode_error_in_load(tmp_path):
    # Fichier avec un encodage qui provoquera UnicodeDecodeError lors du chargement pandas
    # même si l'encodage de detect_file_encoding est "correct" (e.g., utf-8)
    # On simule un cas où le fichier est corrompu après l'échantillon initial
    corrupt_file = tmp_path / "corrupt_load.csv"
    corrupt_file.write_bytes(b"col1,col2\nline1,data1\n\xff\xfe\nline3,data3") # Octets invalides après la 2ème ligne

    # Mock detect_csv_separator pour qu'il retourne un séparateur valide
    with patch("VeriQual_Core.audit_runner.detect_csv_separator") as mock_detect_separator:
        mock_detect_separator.return_value = (",", None) # Force le séparateur à être la virgule
        with patch("VeriQual_Core.audit_runner.load_dataframe_robustly") as mock_load_df:
            # Simuler un échec de décodage Unicode
            mocked_message = "Message de test pour erreur de décodage Unicode."
            mock_load_df.return_value = (
                None,
                None,
                mocked_message,
                "unicode_decode_error_in_load"
            )

            runner = AuditRunner(str(corrupt_file))
            report = runner.run_audit()
            print(json.dumps(report, indent=2))

            assert report["structural_errors"][0]["error_code"] == "unicode_decode_error_in_load"
            assert report["structural_errors"][0]["is_blocking"] is True
            assert report["structural_errors"][0]["message"] == mocked_message


def test_normalize_headers_with_modifications(tmp_path):
    file_content = " ID Client \xa0; Nom\n1;Alice" # En-têtes avec espaces et insécables
    test_file = tmp_path / "headers_mod.csv"
    test_file.write_text(file_content, encoding="utf-8")

    runner = AuditRunner(str(test_file))
    report = runner.run_audit()
    print(json.dumps(report, indent=2))

    assert report["header_info"]["has_normalization_alerts"] is True
    assert report["header_info"]["header_map"] == {" ID Client \xa0": "ID Client", " Nom": "Nom"}
    assert report["file_info"]["total_columns"] == 2
    assert report["structural_errors"] == []


def test_normalize_headers_no_modifications(tmp_path):
    file_content = "ID_Client,Nom\n1,Alice" # En-têtes propres
    test_file = tmp_path / "headers_clean.csv"
    test_file.write_text(file_content, encoding="utf-8")

    runner = AuditRunner(str(test_file))
    report = runner.run_audit()
    print(json.dumps(report, indent=2))

    assert report["header_info"]["has_normalization_alerts"] is False
    assert report["header_info"]["header_map"] == {}
    assert report["structural_errors"] == []


def test_run_audit_full_success(tmp_path):
    file_content = " id_client , Nom Client\n1,Alice\n2,Bob" # Fichier propre avec en-têtes à normaliser
    test_file = tmp_path / "full_success.csv"
    test_file.write_text(file_content, encoding="utf-8")

    runner = AuditRunner(str(test_file))
    report = runner.run_audit()
    print(json.dumps(report, indent=2))

    assert report["structural_errors"] == []
    assert report["file_info"]["file_name"] == "full_success.csv"
    assert report["file_info"]["file_size_kb"] > 0
    assert report["file_info"]["total_rows"] == 2
    assert report["file_info"]["total_columns"] == 2
    assert report["file_info"]["detected_encoding"] in ["utf-8", "ascii"]
    assert report["file_info"]["encoding_confidence"] >= 0.0
    assert report["file_info"]["detected_separator"] == ","
    assert report["header_info"]["has_normalization_alerts"] is True
    assert report["header_info"]["header_map"] == {" id_client ": "id_client", " Nom Client": "Nom Client"}

# --- NOUVEAU TEST POUR F-05 ---
def test_detect_sensitive_data(tmp_path):
    file_content = (
        "Name,Email,Phone,Address,NIR\n"
        "Alice,alice@example.com,+33612345678,1 rue de Paris,1234567890123\n"
        "Bob,bob.dupont@test.fr,0798765432,2 av de Lyon,2987654321098\n"
        "Charlie,charlie@domain.com,not_a_phone,3 bd de Marseille,not_a_nir\n"
    )
    test_file = tmp_path / "sensitive_data.csv"
    test_file.write_text(file_content, encoding="utf-8")

    runner = AuditRunner(str(test_file))
    report = runner.run_audit()
    print(json.dumps(report, indent=2))

    assert report["structural_errors"] == []
    assert report["sensitive_data_report"]["contains_sensitive_data"] is True

    detected_columns = report["sensitive_data_report"]["detected_columns"]

    # Vérifier la détection pour 'Email'
    email_col = next((col for col in detected_columns if col["column_name"] == "Email"), None)
    assert email_col is not None
    assert "EMAIL" in email_col["pii_types"]

    # Vérifier la détection pour 'Phone'
    phone_col = next((col for col in detected_columns if col["column_name"] == "Phone"), None)
    assert phone_col is not None
    assert "PHONE" in phone_col["pii_types"]

    # Vérifier la détection pour 'NIR'
    nir_col = next((col for col in detected_columns if col["column_name"] == "NIR"), None)
    assert nir_col is not None
    assert "NIR" in nir_col["pii_types"]

    # S'assurer qu'Address n'est pas détecté comme PII (selon les règles actuelles)
    address_col = next((col for col in detected_columns if col["column_name"] == "Address"), None)
    assert address_col is None or not address_col["pii_types"] # S'assurer qu'il n'a pas de PII détecté


# --- NOUVEAU TEST POUR F-06 ---
def test_run_audit_with_duplicates(tmp_path):
    file_content = (
        "id,name\n"
        "1,A\n"
        "1,A\n" # Duplicate
        "2,B\n"
    )
    test_file = tmp_path / "duplicates.csv"
    test_file.write_text(file_content, encoding="utf-8")

    runner = AuditRunner(str(test_file))
    report = runner.run_audit()
    print(json.dumps(report, indent=2))

    assert report["structural_errors"] == []
    assert report["duplicate_rows_report"]["duplicate_row_count"] == 1
    assert report["duplicate_rows_report"]["duplicate_row_ratio"] == pytest.approx(0.3333, abs=1e-4) # Utiliser pytest.approx pour les floats
    assert report["file_info"]["total_rows"] == 3 # Total rows should be 3 (header + 3 data rows)

# --- NOUVEAU TEST POUR F-06 (SANS DOUBLONS) ---
def test_run_audit_without_duplicates(tmp_path):
    file_content = (
        "id,name\n"
        "1,A\n"
        "2,B\n"
        "3,C\n"
    )
    test_file = tmp_path / "no_duplicates.csv"
    test_file.write_text(file_content, encoding="utf-8")

    runner = AuditRunner(str(test_file))
    report = runner.run_audit()
    print(json.dumps(report, indent=2))

    assert report["structural_errors"] == []
    assert report["duplicate_rows_report"]["duplicate_row_count"] == 0
    assert report["duplicate_rows_report"]["duplicate_row_ratio"] == 0.0
    assert report["file_info"]["total_rows"] == 3 # Total rows should be 3 (header + 3 data rows)