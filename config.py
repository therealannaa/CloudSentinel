import os
from dotenv import load_dotenv

load_dotenv()

# AWS / LocalStack
LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localhost:4566")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
APPROVED_REGIONS = os.getenv("APPROVED_REGIONS", "ap-south-1").split(",")

# AI / Enrichment API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ABUSEIPDB_KEY = os.getenv("ABUSEIPDB_KEY", "")
VIRUSTOTAL_KEY = os.getenv("VIRUSTOTAL_KEY", "")

# Infrastructure
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Database
DB_PATH = os.getenv("DB_PATH", "cloudsentinel.db")

# Risk Thresholds
RISK_CRITICAL = int(os.getenv("RISK_CRITICAL", "75"))
RISK_HIGH = int(os.getenv("RISK_HIGH", "50"))
MTTD_TARGET = int(os.getenv("MTTD_TARGET", "300"))

# Collector Settings (matching Anna's defaults)
ZEEK_LOG_PATH = os.getenv("ZEEK_LOG_PATH", "data/conn.log")
PORT_SCAN_THRESHOLD = int(os.getenv("PORT_SCAN_THRESHOLD", "20"))
EXFIL_THRESHOLD_MB = int(os.getenv("EXFIL_THRESHOLD_MB", "100"))
MASS_DOWNLOAD_THRESHOLD = int(os.getenv("MASS_DOWNLOAD_THRESHOLD", "50"))
BULK_DELETE_THRESHOLD = int(os.getenv("BULK_DELETE_THRESHOLD", "20"))

# Ephemeral Instance Detection (10 minutes in seconds)
EPHEMERAL_INSTANCE_THRESHOLD = int(os.getenv("EPHEMERAL_INSTANCE_THRESHOLD", "600"))
