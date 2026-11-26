# 🛡️ NYAYA VAULT

**Secure Legal Evidence & Document Management Platform**

NYAYA VAULT is a cybersecurity-focused platform for law enforcement and legal professionals to securely store, manage, and verify legal case documents. It ensures document integrity through SHA-256 hashing, protects evidence with AES-256-GCM encryption, and maintains a tamper-evident audit trail.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Secure Authentication** | Role-based login (Admin & Officer) with hashed passwords |
| **Case Management** | Create and organize legal cases with unique IDs |
| **Document Encryption** | AES-256-GCM encryption for all uploaded evidence |
| **Integrity Verification** | SHA-256 hash comparison to detect tampering |
| **Audit Trail** | Blockchain-style hash-linked activity log |
| **File Validation** | Type (PDF, JPG, PNG, TXT) and size (16 MB) restrictions |

---

## 🛠️ Tech Stack

- **Backend:** Python Flask
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **Database:** SQLite
- **Encryption:** AES-256-GCM (via `cryptography` library)
- **Hashing:** SHA-256

---

## 📁 Project Structure

```
nyaya-vault/
├── app.py                 # Flask application & routes
├── database.py            # Database setup & seed data
├── security.py            # Encryption, hashing & audit chain
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── .gitignore
├── templates/
│   ├── base.html          # Base layout
│   ├── login.html         # Login page
│   ├── dashboard.html     # Dashboard with stats
│   ├── cases.html         # Case listing & creation
│   ├── case_details.html  # Case documents & upload
│   ├── audit.html         # Audit trail viewer
│   └── partials/
│       └── sidebar.html   # Navigation sidebar
├── static/
│   ├── style.css          # Dark cybersecurity theme
│   └── script.js          # Verification & UI logic
├── uploads/               # Temporary upload directory
└── encrypted_files/       # AES-256-GCM encrypted evidence
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.9 or higher
- pip

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/raghavreddy342-dotcom/nyaya-vault.git
   cd nyaya-vault
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set:
   - `FLASK_SECRET_KEY` – a random secret string for Flask sessions
   - `ENCRYPTION_KEY` – a 64-character hex string (32 bytes) for AES-256

   Generate a secure encryption key:
   ```bash
   python -c "import os; print(os.urandom(32).hex())"
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

---

## 🔐 Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Officer | `officer1` | `officer123` |

---

## 🔑 Security Features

### AES-256-GCM Encryption
- Every uploaded file is encrypted before storage
- Original plaintext is never kept on disk
- 12-byte random nonce per file
- Authenticated encryption prevents silent tampering

### SHA-256 Integrity Verification
- Hash computed at upload time and stored in DB
- On verification, file is decrypted and re-hashed
- **VERIFIED** = hashes match → document is intact
- **INTEGRITY MISMATCH** = hashes differ → possible tampering

### Hash-Linked Audit Trail
- Every action (login, upload, download, verify) is logged
- Each record's SHA-256 hash includes the previous record's hash
- Chain verification detects any modification or deletion of audit records

---

## 🧪 Running Tests

```bash
python test_app.py
```

This runs 34 automated integration tests covering login, case management, document upload/encryption, SHA-256 verification, download/decryption, audit logging, and authorization.

---

## ⚠️ Important Notes

- This is an **MVP / hackathon project** — not production-ready
- Change the default `.env` values before any real deployment
- The `.env` file is excluded from Git via `.gitignore`
- Never commit encryption keys or the SQLite database

---

## 📝 License

This project was built for educational and hackathon purposes.
