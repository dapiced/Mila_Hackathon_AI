#!/usr/bin/env python3
"""Upload a model tar.gz to S3 using hackathon credentials.

Usage:
    source ../.env
    python ../scripts/upload_model_s3.py /tmp/mbert_v4.tar.gz team_021/mbert_finetuned_v4.tar.gz
"""
import datetime
import hashlib
import hmac
import os
import ssl
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

if len(sys.argv) < 3:
    print("Usage: python upload_model_s3.py <local_file> <s3_key>")
    print("Example: python upload_model_s3.py /tmp/mbert_v4.tar.gz team_021/mbert_finetuned_v4.tar.gz")
    sys.exit(1)

filepath = Path(sys.argv[1])
key = sys.argv[2]

if not filepath.exists():
    print(f"File not found: {filepath}")
    sys.exit(1)

bucket = os.environ.get("S3_BUCKET_NAME", "hackathon-s3-bucket-21-e8b3s")
endpoint = os.environ["S3_ENDPOINT_URL"]
access_key = os.environ["S3_ACCESS_KEY"]
secret_key = os.environ["S3_SECRET_KEY"]

host = endpoint.replace("https://", "").replace("http://", "")
region = "us-east-1"
service = "s3"
now = datetime.datetime.utcnow()
date_stamp = now.strftime("%Y%m%d")
amz_date = now.strftime("%Y%m%dT%H%M%SZ")

print(f"Reading {filepath} ({filepath.stat().st_size / 1024 / 1024:.1f} MB)...")
data = filepath.read_bytes()
payload_hash = hashlib.sha256(data).hexdigest()
content_type = "application/gzip"

canonical_uri = f"/{bucket}/{key}"
canonical_querystring = ""
signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"
canonical_request = (
    f"PUT\n{canonical_uri}\n{canonical_querystring}\n"
    f"content-type:{content_type}\n"
    f"host:{host}\n"
    f"x-amz-content-sha256:{payload_hash}\n"
    f"x-amz-date:{amz_date}\n"
    f"\n{signed_headers}\n{payload_hash}"
)

algorithm = "AWS4-HMAC-SHA256"
credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
cr_hash = hashlib.sha256(canonical_request.encode()).hexdigest()
string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{cr_hash}"


def sign(k, m):
    return hmac.new(k, m.encode(), hashlib.sha256).digest()


k_date = sign(f"AWS4{secret_key}".encode(), date_stamp)
k_region = sign(k_date, region)
k_service = sign(k_region, service)
k_signing = sign(k_service, "aws4_request")
signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

authorization = (
    f"{algorithm} Credential={access_key}/{credential_scope}, "
    f"SignedHeaders={signed_headers}, Signature={signature}"
)

url = f"{endpoint}/{bucket}/{key}"
req = urllib.request.Request(url, data=data, method="PUT")
req.add_header("Host", host)
req.add_header("Content-Type", content_type)
req.add_header("x-amz-content-sha256", payload_hash)
req.add_header("x-amz-date", amz_date)
req.add_header("Authorization", authorization)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print(f"Uploading to {url}...")
with urllib.request.urlopen(req, context=ctx) as resp:
    print(f"Status: {resp.status}")
    print(f"SHA256: {payload_hash}")
print("Done!")
