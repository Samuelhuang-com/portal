"""
validate_forms_spec.py v1.0
驗證 specs/forms.yaml 的結構完整性：
  - 每張表單必須有 key, name, ragic_path, permission_key
  - 每個欄位必須有 name, type
  - link/lookup 欄位必須有 source_form 或 source
  - formula 欄位必須有 formula
  - select 欄位必須有 options 或 lookup_from
"""
import sys
import logging
from pathlib import Path

try:
    import yaml
except ImportError:
    raise ImportError("請先安裝 PyYAML：pip install pyyaml")

VERSION = "v1.0"
ICON = "🔍"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_FORM_KEYS = ["key", "name", "ragic_path", "permission_key"]
REQUIRED_FIELD_KEYS = ["name", "type"]


def validate_field(field: dict, form_key: str, table: str = "") -> list:
    errors = []
    location = f"{form_key}.{table}.{field.get('name', '?')}" if table else f"{form_key}.{field.get('name', '?')}"

    for k in REQUIRED_FIELD_KEYS:
        if k not in field:
            errors.append(f"❌ {location}：缺少欄位屬性 '{k}'")

    ftype = field.get("type", "")
    if ftype == "link" and "source_form" not in field:
        errors.append(f"❌ {location}：link 欄位缺少 'source_form'")
    if ftype == "lookup" and "source" not in field and "lookup_from" not in field:
        errors.append(f"❌ {location}：lookup 欄位缺少 'source' 或 'lookup_from'")
    if ftype == "formula" and "formula" not in field:
        errors.append(f"❌ {location}：formula 欄位缺少 'formula'")
    if ftype == "select" and "options" not in field and "lookup_from" not in field:
        errors.append(f"❌ {location}：select 欄位缺少 'options' 或 'lookup_from'")

    return errors


def validate_spec(spec_path: Path) -> bool:
    logger.info(f"{ICON} [{VERSION}] 載入規格檔：{spec_path}")
    with open(spec_path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    forms = spec.get("forms", [])
    if not forms:
        logger.error(f"{ICON} 規格檔中無 forms 定義。")
        return False

    all_errors = []
    for form in forms:
        form_key = form.get("key", "unknown")
        for k in REQUIRED_FORM_KEYS:
            if k not in form:
                all_errors.append(f"❌ 表單 '{form_key}'：缺少屬性 '{k}'")

        for field in form.get("fields", []):
            all_errors.extend(validate_field(field, form_key))

        for subtable in form.get("subtables", []):
            table_name = subtable.get("name", "?")
            for field in subtable.get("fields", []):
                all_errors.extend(validate_field(field, form_key, table_name))

    if all_errors:
        logger.error(f"{ICON} 發現 {len(all_errors)} 個錯誤：")
        for err in all_errors:
            logger.error(f"  {err}")
        return False

    logger.info(f"{ICON} ✅ 驗證通過！共 {len(forms)} 張表單，無錯誤。")
    return True


def main():
    spec_path = Path(__file__).parent.parent / "specs" / "forms.yaml"
    if not spec_path.exists():
        logger.error(f"{ICON} 找不到規格檔：{spec_path}")
        sys.exit(1)

    ok = validate_spec(spec_path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
