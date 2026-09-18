import binascii
import json
import re
from datetime import datetime
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct
from google.protobuf.wrappers_pb2 import StringValue

from utils.logger import logger

class Util:
    @staticmethod
    def is_protobuf_envelope(value) -> bool:
        """True if value is an OpenGIN protobuf Any wrapper ({typeUrl, value})."""
        if isinstance(value, dict):
            return "value" in value and bool(value.get("typeUrl") or value.get("type_url"))
        if isinstance(value, str):
            stripped = value.strip()
            return stripped.startswith("{") and (
                "typeUrl" in stripped or "type_url" in stripped
            )
        return False

    # helper: decode protobuf attribute name
    @staticmethod
    def decode_protobuf_attribute_name(name: str | dict) -> str:
            try:
                data = name if isinstance(name, dict) else json.loads(name)
                hex_value = data.get("value")
                if not hex_value:
                    return "Unknown"

                decoded_bytes = binascii.unhexlify(hex_value)
                type_url = str(data.get("typeUrl") or data.get("type_url") or "")
                if "Struct" in type_url:
                    return Util._decode_protobuf_struct(decoded_bytes)

                sv = StringValue()
                try:
                    sv.ParseFromString(decoded_bytes)
                    if(sv.value.strip() == ""):
                        return decoded_bytes.decode("utf-8", errors="ignore").strip()
                    return sv.value.strip()
                except Exception:
                    decoded_str = decoded_bytes.decode("utf-8", errors="ignore")
                    cleaned = ''.join(ch for ch in decoded_str if ch.isprintable())
                    return cleaned.strip()
            except Exception as e:
                logger.error(f"Attribute decode error: {e}")
                return "Unknown"

    @staticmethod
    def _decode_protobuf_struct(decoded_bytes: bytes) -> str:
        """Struct → inner 'data' string (table JSON) or JSON of the struct."""
        struct = Struct()
        struct.ParseFromString(decoded_bytes)
        as_dict = MessageToDict(struct)
        data_field = as_dict.get("data")
        if isinstance(data_field, str):
            return data_field.strip()
        if data_field is not None:
            return json.dumps(data_field)
        return json.dumps(as_dict)

    @staticmethod
    def normalize_name(value: str | None) -> str:
        """Strip and coerce a name value to a plain string for comparison."""
        return str(value or "").strip()

    @staticmethod
    def decode_search_entity_name(name: str) -> str:
        """Decode entity name from search API; pass through plain text unchanged."""
        stripped = str(name or "").strip()
        if not stripped:
            return ""
        if not (stripped.startswith("{") and '"value"' in stripped):
            return stripped
        decoded = Util.decode_protobuf_attribute_name(stripped)
        return decoded if decoded != "Unknown" else stripped

    @staticmethod
    def validate_and_sanitize_tabular_dataset(data_content: dict) -> bool:
        """
        Validate the structure of a dataset JSON content.
        
        Validates:
        - data_content is a dictionary
        - Has 'columns' key that is a non-empty list
        - Has 'rows' key that is a list
        - Each row is a list
        - All rows have the same number of columns (matching columns length)
        
        Args:
            data_content: Dictionary containing dataset data with 'columns' and 'rows' keys
            
        Returns:
            True if validation passes, False otherwise
        """
        # Validate structure: must have columns and rows
        if not isinstance(data_content, dict):
            logger.error("data.json is not a dictionary")
            return False
        
        columns = data_content.get('columns')
        rows = data_content.get('rows')
        
        if not isinstance(columns, list):
            logger.error("'columns' in data.json is not a list")
            return False
        
        if not isinstance(rows, list):
            logger.error("'rows' in data.json is not a list")
            return False
        
        if not columns:
            logger.error("'columns' list is empty")
            return False
        
        if not rows:
            logger.error("'rows' list is empty")
            return False
        
        expected_column_count = len(columns)
        
        # Validate rows structure and sanitize null values
        # Each row must be a list with the same number of columns.
        # Null values are converted to empty strings as the server doesn't support them.
        for i, row in enumerate(rows):
            if not isinstance(row, list):
                logger.error(f"Row {i} is not a list")
                return False
            if len(row) != expected_column_count:
                logger.error(f"Row {i} has {len(row)} values but expected {expected_column_count}")
                return False
            # Sanitize: replace None with empty string in-place
            for j, cell in enumerate(row):
                if cell is None:
                    row[j] = ''
        
        return True

    # Format name to human readable title case
    @staticmethod
    def format_attribute_name(name: str) -> str:
        
        formatted = str(name).strip()
        # Replace underscores and hyphens with spaces
        formatted = formatted.replace('_', ' ').replace('-', ' ')
        # Remove extra whitespace and convert to title case
        formatted = ' '.join(formatted.split())
        formatted = formatted.title()
        return formatted
