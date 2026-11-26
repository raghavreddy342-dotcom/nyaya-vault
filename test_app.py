"""Integration test for NYAYA VAULT using Flask test client (no network needed)."""
import sys, os, json, io

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

# Clean slate
if os.path.exists("nyayavault.db"):
    os.remove("nyayavault.db")

from dotenv import load_dotenv
load_dotenv()

from database import init_db
init_db()

from app import app

app.config["TESTING"] = True
client = app.test_client()

passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name}")
        failed += 1

def login(username, password):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)

print("\n=== TEST GROUP 1: Login ===")
r = client.get("/login")
test("Login page loads", r.status_code == 200)
test("Login form present", b"username" in r.data and b"password" in r.data)

r = login("admin", "admin123")
test("Admin login succeeds", r.status_code == 200 and b"Dashboard" in r.data)

# Bad login
client.get("/logout")
r = login("admin", "wrongpassword")
test("Bad password rejected", b"Invalid" in r.data)

r = login("admin", "admin123")

print("\n=== TEST GROUP 2: Dashboard ===")
r = client.get("/dashboard")
test("Dashboard loads", b"Total Cases" in r.data)
test("Shows recent activity", b"Recent Activity" in r.data)

print("\n=== TEST GROUP 3: Cases ===")
r = client.get("/cases")
test("Cases page loads", b"CASE-2026-001" in r.data)
test("Seed cases visible", b"State vs. Sharma" in r.data)

# Create new case
r = client.post("/cases/create", data={
    "case_id": "CASE-TEST-001",
    "title": "Integration Test Case",
    "description": "Automated test"
}, follow_redirects=True)
test("Create case succeeds", b"CASE-TEST-001" in r.data)

# Duplicate case
r = client.post("/cases/create", data={
    "case_id": "CASE-TEST-001",
    "title": "Duplicate",
    "description": ""
}, follow_redirects=True)
test("Duplicate case rejected", b"already exists" in r.data)

# Case details
r = client.get("/cases/CASE-2026-001")
test("Case details page", b"State vs. Sharma" in r.data)
test("Upload form present", b"multipart/form-data" in r.data)

print("\n=== TEST GROUP 4: Document Upload & Encryption ===")
file_content = b"This is test evidence for NYAYA VAULT integrity verification testing."
r = client.post("/upload", data={
    "case_id": "CASE-2026-001",
    "file": (io.BytesIO(file_content), "evidence.txt"),
}, content_type="multipart/form-data", follow_redirects=True)
test("Document uploaded", b"evidence.txt" in r.data or r.status_code == 200)

# Check encrypted file exists
enc_files = os.listdir("encrypted_files")
test("Encrypted file stored", len(enc_files) > 0)
test("File has .enc extension", any(f.endswith(".enc") for f in enc_files))

# Bad file type
r = client.post("/upload", data={
    "case_id": "CASE-2026-001",
    "file": (io.BytesIO(b"bad"), "malware.exe"),
}, content_type="multipart/form-data", follow_redirects=True)
test("Invalid file type rejected", b"not allowed" in r.data)

# No file
r = client.post("/upload", data={
    "case_id": "CASE-2026-001",
}, content_type="multipart/form-data", follow_redirects=True)
test("No file rejected", b"No file" in r.data)

print("\n=== TEST GROUP 5: SHA-256 Verification ===")
r = client.get("/documents/1/verify")
result = json.loads(r.data)
test("Verify returns VERIFIED", result["status"] == "VERIFIED")
test("Hashes match", result["original_hash"] == result["current_hash"])
test("Has 64-char SHA-256 hash", len(result["original_hash"]) == 64)

# Non-existent document
r = client.get("/documents/999/verify")
test("Missing doc returns 404", r.status_code == 404)

print("\n=== TEST GROUP 6: Document Download ===")
r = client.get("/documents/1/download")
test("Download succeeds", r.status_code == 200)
test("Decrypted content matches", r.data == file_content)
test("Content-Disposition header", "attachment" in r.headers.get("Content-Disposition", ""))

print("\n=== TEST GROUP 7: Audit Trail ===")
r = client.get("/audit")
test("Audit page loads", b"Audit Trail" in r.data)
test("Login recorded", b"LOGIN" in r.data)
test("Upload recorded", b"UPLOAD" in r.data)
test("Verify recorded", b"VERIFY" in r.data)
test("Download recorded", b"DOWNLOAD" in r.data)

# Verify audit chain
r = client.get("/audit/verify-chain")
result = json.loads(r.data)
test("Audit chain VERIFIED", result["status"] == "VERIFIED")
test("Multiple records checked", result["checked"] > 3)

print("\n=== TEST GROUP 8: Authorization ===")
client.get("/logout")
r = client.get("/dashboard", follow_redirects=True)
test("Redirect to login when logged out", b"Login" in r.data or b"login" in r.data.lower())

# Officer login
r = login("officer1", "officer123")
test("Officer login succeeds", b"Dashboard" in r.data)

# Officer can access cases
r = client.get("/cases")
test("Officer can view cases", r.status_code == 200)

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed+failed}")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
