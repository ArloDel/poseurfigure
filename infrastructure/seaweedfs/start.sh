#!/bin/sh
# Starts a single-node SeaweedFS with its S3 API. Credentials come from the environment,
# so nothing secret is committed. Dev only: one master, one volume server, one filer.
set -e

: "${S3_ACCESS_KEY:?S3_ACCESS_KEY is required}"
: "${S3_SECRET_KEY:?S3_SECRET_KEY is required}"

cat > /tmp/s3.json <<EOF
{
  "identities": [
    {
      "name": "figurepose",
      "credentials": [{ "accessKey": "${S3_ACCESS_KEY}", "secretKey": "${S3_SECRET_KEY}" }],
      "actions": ["Admin", "Read", "Write", "List", "Tagging"]
    }
  ]
}
EOF

exec weed server -dir=/data -ip.bind=0.0.0.0 -master.volumeSizeLimitMB=1024 \
  -s3 -s3.port=8333 -s3.config=/tmp/s3.json
