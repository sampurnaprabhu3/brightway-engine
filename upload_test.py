import requests
import os

# 1. URL of your FastAPI upload endpoint
url = "http://127.0.0.1:8000/datasets/upload_excel"

# 2. Path to the REAL Excel file (.xlsx)
file_path = os.path.join("data", "iai_aluminium_simple.xlsx")

if not os.path.exists(file_path):
    raise FileNotFoundError(f"File not found at: {file_path}")

# 3. Open file and send in one go
with open(file_path, "rb") as f:
    files = {
        # 👇 IMPORTANT: name must be "file" (same as UploadFile(..., name="file"))
        #     Use a .xlsx filename + correct Excel MIME type
        "file": (
            "iai_aluminium_simple.xlsx",
            f,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    response = requests.post(url, files=files)

print("Status code:", response.status_code)
print("Response text:", response.text)
