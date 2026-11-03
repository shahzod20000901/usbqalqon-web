"""Desktop dasturning Devices.txt formatini o'qish va yozish."""

import re

SERIAL_RE = re.compile(r"Seriya raqami\s*:\s*([^;\n\r]+)", re.IGNORECASE)
VENDOR_RE = re.compile(r"Ishlab chiqaruvchi\s*:\s*([^;\n\r]+)", re.IGNORECASE)
MODEL_RE = re.compile(r"Model\s*:\s*([^;\n\r]+)", re.IGNORECASE)
GRIF_RE = re.compile(r"Grif\s*:\s*([^;\n\r]+)", re.IGNORECASE)
TYPE_RE = re.compile(r"Qurilma turi\s*:\s*([^;\n\r]+)", re.IGNORECASE)


def infer_device_type(vendor: str, model: str) -> str:
    text = f"{vendor} {model}".lower()
    if "android" in text or "adb" in text or "mtp" in text:
        return "Android smartfon"
    if "iphone" in text or "apple" in text:
        return "Iphone smartphone"
    if "external" in text or "passport" in text or "hdd" in text or "hard disk" in text:
        return "Hard disk"
    if any(word in text for word in ("flash", "datatraveler", "storage", "usb", "disk")):
        return "Fleshka"
    return "USB qurilma"


def _find(pattern: re.Pattern, text: str, default: str = "") -> str:
    match = pattern.search(text)
    if not match:
        return default
    return match.group(1).strip().strip('"').strip("'")


def parse_devices_text(content: str) -> tuple[list[dict], list[str]]:
    """Matnni qurilmalar ro'yxatiga aylantiradi.

    Har bir yozuv bitta qatorda yoki bir nechta qatorda bo'lishi mumkin.
    """
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    records_text: list[str] = []
    buffer: list[str] = []

    for line in normalized.split("\n"):
        if SERIAL_RE.search(line):
            if buffer:
                records_text.append("\n".join(buffer))
            buffer = [line]
        elif buffer:
            buffer.append(line)
        elif line.strip():
            buffer = [line]

    if buffer:
        records_text.append("\n".join(buffer))

    records: list[dict] = []
    errors: list[str] = []

    for index, chunk in enumerate(records_text, start=1):
        serial = _find(SERIAL_RE, chunk)
        if not serial:
            if chunk.strip():
                errors.append(f"{index}-yozuv: seriya raqami topilmadi")
            continue

        vendor = _find(VENDOR_RE, chunk)
        model = _find(MODEL_RE, chunk)
        grif = _find(GRIF_RE, chunk) or "Nomaxfiy"
        device_type = _find(TYPE_RE, chunk) or infer_device_type(vendor, model)

        records.append(
            {
                "serial_number": serial,
                "vendor": vendor,
                "model": model,
                "grif": grif,
                "device_type": device_type,
            }
        )

    return records, errors


def device_to_line(device) -> str:
    return (
        f"Seriya raqami: {device.serial_number}; "
        f"Ishlab chiqaruvchi: {device.vendor}; "
        f"Model: {device.model}; "
        f"Grif: {device.grif}"
    )
