#!/usr/bin/env bash
# Issue TLS certificates for Thunder Main.
#
# Why a private CA rather than a single self-signed certificate: the CA
# certificate is what the Android app has to trust, and shipping a new trust
# anchor means shipping a new APK. With a CA in the middle, the anchor is
# issued once for ten years and the server certificate under it can be
# reissued - after an IP change, an expiry, or a suspected key compromise -
# with nothing to do on the phone.
#
# A public CA cannot help here. There is no public name to validate; Thunder
# answers on a LAN address. A private CA that only this fleet trusts is not a
# downgrade from that, it is stronger: exactly one issuer can mint a
# certificate the app accepts, where the public trust store has hundreds.
#
#   ./make_certs.sh                 # first run, or reissue the server cert
#   ./make_certs.sh 10.168.168.10 thunder.local   # override the names
set -euo pipefail
cd "$(dirname "$0")"

OUT="${THUNDER_TLS_DIR:-../thunder-data/tls}"
mkdir -p "$OUT"
chmod 700 "$OUT"

CA_DAYS=3650
SRV_DAYS=825   # the longest span browsers and Android will accept

# Every address the app might use to reach Main. A certificate is only valid
# for the names inside it, so a missing one here is a connection failure later.
IPS=("${1:-10.168.168.10}" "127.0.0.1")
DNS=("${2:-thunder.local}" "localhost" "thunder-main")

if [[ ! -f "$OUT/ca.key" ]]; then
  echo "creating certificate authority (once, 10 years)"
  openssl genrsa -out "$OUT/ca.key" 4096 2>/dev/null
  chmod 600 "$OUT/ca.key"
  openssl req -x509 -new -key "$OUT/ca.key" -sha256 -days "$CA_DAYS" \
    -out "$OUT/ca.crt" \
    -subj "/CN=Thunder Fleet CA/O=Thunder" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
else
  echo "reusing existing CA (the app already trusts it - do not delete it)"
fi

# The SAN list is what actually gets validated; the CN is legacy and ignored.
san="subjectAltName="
for d in "${DNS[@]}"; do san+="DNS:$d,"; done
for i in "${IPS[@]}"; do san+="IP:$i,"; done
san="${san%,}"

echo "issuing server certificate for: ${DNS[*]} ${IPS[*]}"
openssl genrsa -out "$OUT/server.key" 2048 2>/dev/null
chmod 600 "$OUT/server.key"
openssl req -new -key "$OUT/server.key" -out "$OUT/server.csr" \
  -subj "/CN=thunder-main/O=Thunder" 2>/dev/null
openssl x509 -req -in "$OUT/server.csr" \
  -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" -CAcreateserial \
  -out "$OUT/server.crt" -days "$SRV_DAYS" -sha256 \
  -extfile <(printf '%s\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' "$san") 2>/dev/null
rm -f "$OUT/server.csr"

echo
openssl x509 -in "$OUT/server.crt" -noout -subject -dates \
  -ext subjectAltName | sed 's/^/  /'
echo
echo "CA fingerprint (this is what the app pins):"
openssl x509 -in "$OUT/ca.crt" -noout -fingerprint -sha256 | sed 's/^/  /'
