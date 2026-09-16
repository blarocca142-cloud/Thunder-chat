# TLS

Main answers https on **8443**. Plaintext 8080 is still running during the
migration.

    ./make_certs.sh                  # issue / reissue
    sudo systemctl restart thunder-main-tls

## Why a private CA

There is no public name to validate - Thunder answers on `10.168.168.10`, and
no public authority will ever sign a certificate for a private address. So the
fleet has its own CA.

The CA certificate is the trust anchor, and it is bundled in the Android app
(`res/raw/thunder_ca.crt`). That is the reason for a CA rather than a bare
self-signed certificate: changing the anchor means shipping a new APK, but the
*server* certificate underneath it can be reissued freely - after an IP change,
an expiry, or a suspected key compromise - with nothing to do on the phone.

This is not weaker than a public CA. It is narrower: exactly one issuer can
mint a certificate the app will accept, where the public trust store carries
well over a hundred. What it does not give is trust for anyone who has not
installed the anchor, which is fine, because nobody else should be connecting.

## Files

Under `thunder-data/tls/`, which is gitignored:

| file | what it is |
|---|---|
| `ca.key` | **the secret that matters.** Anyone holding it can impersonate Main to the app. Never copy it off this box. |
| `ca.crt` | public. Bundled into the APK. Deleting it breaks every installed app. |
| `server.key` | Main's private key, 0600, read by the service |
| `server.crt` | Main's certificate, valid 825 days |

Expiry dates are real. `openssl x509 -in server.crt -noout -dates` before
wondering why the app stopped connecting.

## Names in the certificate

A certificate is only valid for the names inside it, and a missing one is a
connection failure, not a warning. Currently:

    DNS: thunder.local, localhost, thunder-main
    IP:  10.168.168.10, 127.0.0.1

If the LAN address changes, reissue with the new one:

    ./make_certs.sh 10.168.168.42 thunder.local

## Finishing the migration

1. Install 1.2.0 (it carries the CA; earlier builds cannot do https at all).
2. Set the server URL to `https://10.168.168.10:8443`.
3. Confirm chat, voice and generation all still work.
4. Then, and only then:

       sudo systemctl disable --now thunder-main        # kill plaintext 8080

5. Set `cleartextTrafficPermitted="false"` in
   `res/xml/network_security_config.xml` and ship a build. Until that flips,
   an attacker who can answer in Main's place can still downgrade the app to
   http; after it, the app refuses.

## Verified

- TLS 1.3, `TLS_AES_256_GCM_SHA384`, verify code 0 against the CA
- rejected without the CA (`unable to get local issuer certificate`)
- rejected for a hostname not in the SAN list
- the APK contains `ca.crt` with a fingerprint matching this box, and no key
- with `THUNDER_AUTH=required` over TLS: no token 401, wrong token 401,
  real token 200, `/health` open

## What TLS does not fix

It protects data in transit on the LAN, which matters most for the bearer
token. It does nothing for data at rest - the databases and generated files on
this disk are still plaintext. That is the next item, and it is the one that
counts for a claims system, since a stolen drive is a likelier loss than a
sniffed LAN.
