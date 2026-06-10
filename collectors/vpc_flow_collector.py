import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

ZEEK_LOG_PATH = os.getenv("ZEEK_LOG_PATH", "data/conn.log")
PORT_SCAN_THRESHOLD = int(os.getenv("PORT_SCAN_THRESHOLD", "20"))
PORT_SCAN_WINDOW = int(os.getenv("PORT_SCAN_WINDOW", "60"))
EXFIL_THRESHOLD_MB = int(os.getenv("EXFIL_THRESHOLD_MB", "100"))

INTERNAL_CIDR_PREFIXES = ["10.", "172.16.", "192.168."]

def is_internal(ip):
    return any(ip.startswith(prefix) for prefix in INTERNAL_CIDR_PREFIXES)

def parse_zeek_line(line):
    if line.startswith("#") or not line.strip():
        return None
    fields = line.strip().split("\t")
    if len(fields) < 9:
        return None
    try:
        return {
            "timestamp": fields[0],
            "srcaddr": fields[2],
            "srcport": fields[3],
            "dstaddr": fields[4],
            "dstport": fields[5],
            "protocol": fields[6],
            "bytes": int(fields[9]) if fields[9] not in ["-", ""] else 0,
            "action": "REJECT" if fields[7] == "REJ" else "ACCEPT",
        }
    except (IndexError, ValueError):
        return None

def detect_port_scan(connections):
    reject_counts = {}
    for conn in connections:
        if conn["action"] == "REJECT":
            src = conn["srcaddr"]
            reject_counts[src] = reject_counts.get(src, 0) + 1

    findings = []
    for src_ip, count in reject_counts.items():
        if count >= PORT_SCAN_THRESHOLD:
            findings.append({
                "timestamp": datetime.utcnow().isoformat(),
                "source_ip": src_ip,
                "event_type": "PORT_SCAN_DETECTED",
                "severity": "HIGH",
                "raw_event": json.dumps({
                    "rejected_connections": count,
                    "threshold": PORT_SCAN_THRESHOLD,
                    "mitre_technique": "T1046"
                }),
                "agent_id": "network_hunter",
                "username": "unknown"
            })
            print(f"[VPC Flow] Port scan detected from {src_ip} — {count} rejected connections")

    return findings

def detect_exfiltration(connections):
    outbound_bytes = {}
    for conn in connections:
        if not is_internal(conn["srcaddr"]) or is_internal(conn["dstaddr"]):
            continue
        src = conn["srcaddr"]
        outbound_bytes[src] = outbound_bytes.get(src, 0) + conn["bytes"]

    findings = []
    for src_ip, total_bytes in outbound_bytes.items():
        total_mb = total_bytes / (1024 * 1024)
        if total_mb >= EXFIL_THRESHOLD_MB:
            findings.append({
                "timestamp": datetime.utcnow().isoformat(),
                "source_ip": src_ip,
                "event_type": "LARGE_OUTBOUND_TRANSFER",
                "severity": "CRITICAL",
                "raw_event": json.dumps({
                    "total_mb": round(total_mb, 2),
                    "threshold_mb": EXFIL_THRESHOLD_MB,
                    "mitre_technique": "T1537"
                }),
                "agent_id": "network_hunter",
                "username": "unknown"
            })
            print(f"[VPC Flow] Large outbound transfer from {src_ip} — {round(total_mb, 2)} MB")

    return findings

def collect_vpc_flow_events(log_path=None):
    path = log_path or ZEEK_LOG_PATH
    findings = []

    if not os.path.exists(path):
        print(f"[VPC Flow] Log file not found at {path} — using empty dataset")
        return findings

    connections = []
    with open(path, "r") as f:
        for line in f:
            parsed = parse_zeek_line(line)
            if parsed:
                connections.append(parsed)

    print(f"[VPC Flow] Parsed {len(connections)} connections from {path}")

    findings += detect_port_scan(connections)
    findings += detect_exfiltration(connections)

    print(f"[VPC Flow] Total findings: {len(findings)}")
    return findings

if __name__ == "__main__":
    results = collect_vpc_flow_events()
    print(json.dumps(results, indent=2, default=str))