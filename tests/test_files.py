import tempfile
import os
from tools.common.files import detect_csv_separator

def test_detect_csv_separator_semicolon():
    csv_content = "col1;col2;col3\n1;2;3\n4;5;6"

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv", encoding="utf-8") as f:
        f.write(csv_content)
        f.flush()
        temp_path = f.name

    try:
        sep, err = detect_csv_separator(temp_path, "utf-8")
        assert sep == ";"
        assert err is None
    finally:
        os.remove(temp_path)
