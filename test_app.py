"""Integration test for NYAYA VAULT – role-based access control."""
import sys, os, json, io

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

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

# ── ADMIN TESTS ──────────────────────────────────────────────────────

print("\n=== ADMIN: Login & Dashboard ===")
r = login("admin", "admin123")
test("Admin login", b"Dashboard" in r.data)
test("Admin sees ADMIN badge", b"ADMIN" in r.data)
test("Admin sees Registered Users", b"Registered Users" in r.data)
test("Admin sees system-wide activity", b"System-Wide Activity" in r.data)
test("Admin sees quick actions", b"Quick Actions" in r.data)

print("\n=== ADMIN: Sidebar ===")
r = client.get("/dashboard")
test("Admin sees Audit Trail in sidebar", b"Audit Trail" in r.data)

print("\n=== ADMIN: Cases ===")
r = client.get("/cases")
test("Admin sees New Case button", b"New Case" in r.data)
test("Admin sees create case modal", b"newCaseModal" in r.data)

# Create a case
r = client.post("/cases/create", data={
    "case_id": "CASE-ADMIN-001", "title": "Admin Test", "description": "Test"
}, follow_redirects=True)
test("Admin can create case", b"CASE-ADMIN-001" in r.data)

print("\n=== ADMIN: Document & Verify ===")
file_content = b"Admin test evidence file content."
r = client.post("/upload", data={
    "case_id": "CASE-ADMIN-001",
    "file": (io.BytesIO(file_content), "admin_doc.txt"),
}, content_type="multipart/form-data", follow_redirects=True)
test("Admin uploads doc", b"admin_doc.txt" in r.data)

r = client.get("/documents/1/verify")
result = json.loads(r.data)
test("Admin verify VERIFIED", result["status"] == "VERIFIED")

r = client.get("/documents/1/download")
test("Admin downloads doc", r.data == file_content)

print("\n=== ADMIN: Audit Trail ===")
r = client.get("/audit")
test("Admin can access audit trail", r.status_code == 200 and b"Audit Trail" in r.data)

r = client.get("/audit/verify-chain")
result = json.loads(r.data)
test("Admin can verify chain", result["status"] == "VERIFIED")

client.get("/logout")

# ── OFFICER TESTS ────────────────────────────────────────────────────

print("\n=== OFFICER: Login & Dashboard ===")
r = login("officer1", "officer123")
test("Officer login", b"Dashboard" in r.data)
test("Officer sees OFFICER badge", b"OFFICER" in r.data)
test("Officer sees My Uploads stat", b"My Uploads" in r.data)
test("Officer sees own activity label", b"Your Recent Activity" in r.data)
test("Officer does NOT see Registered Users", b"Registered Users" not in r.data)
test("Officer does NOT see Quick Actions", b"Quick Actions" not in r.data)

print("\n=== OFFICER: Sidebar ===")
r = client.get("/dashboard")
test("Officer does NOT see Audit Trail in sidebar", b"Audit Trail" not in r.data)

print("\n=== OFFICER: Cases ===")
r = client.get("/cases")
test("Officer can view cases", b"CASE-ADMIN-001" in r.data)
test("Officer does NOT see New Case button", b"New Case" not in r.data)
test("Officer does NOT see create modal", b"newCaseModal" not in r.data)
test("Officer sees helpful message", b"View assigned cases" in r.data)

# Officer tries to create a case (backend block)
r = client.post("/cases/create", data={
    "case_id": "CASE-OFFICER-999", "title": "Sneaky", "description": "Should fail"
}, follow_redirects=True)
test("Officer blocked from creating case", b"Admin access required" in r.data)
# Verify case was NOT created
r = client.get("/cases")
test("Unauthorized case was not created", b"CASE-OFFICER-999" not in r.data)

print("\n=== OFFICER: Documents ===")
r = client.get("/cases/CASE-ADMIN-001")
test("Officer can view case details", b"Admin Test" in r.data)
test("Officer sees upload form", b"Encrypt" in r.data)

# Officer can upload
file_content2 = b"Officer evidence upload test."
r = client.post("/upload", data={
    "case_id": "CASE-ADMIN-001",
    "file": (io.BytesIO(file_content2), "officer_doc.txt"),
}, content_type="multipart/form-data", follow_redirects=True)
test("Officer can upload docs", b"officer_doc.txt" in r.data)

# Officer can verify
r = client.get("/documents/2/verify")
result = json.loads(r.data)
test("Officer can verify docs", result["status"] == "VERIFIED")

# Officer can download
r = client.get("/documents/2/download")
test("Officer can download docs", r.data == file_content2)

print("\n=== OFFICER: Audit Trail BLOCKED ===")
r = client.get("/audit", follow_redirects=True)
test("Officer blocked from audit trail", b"Admin access required" in r.data)

r = client.get("/audit/verify-chain", follow_redirects=True)
test("Officer blocked from chain verify", b"Admin access required" in r.data)

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed+failed}")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
