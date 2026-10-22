- Start Date: 2026-10-21
- RFC PR: [#TBD](https://github.com/CERNDocumentServer/cds-videos/pull/0000)
- Authors: Zacharias Zacharodimos

# EOS Download Offload

## Summary

This RFC proposes offloading **file downloads** in CDS Videos from the
application (uWSGI) process to nginx, which streams the bytes directly from EOS
using an `X-Accel-Redirect` internal proxy. A custom storage class resolves the
physical EOS URL for a requested file and returns an empty response carrying the
redirect header; nginx then proxies the file from EOS to the client without the
application ever touching the file data.

The scope is limited to the files-rest download endpoint
(`invenio_files_rest.object_api`, i.e. `GET /api/files/<bucket>/<key>`). Video
**streaming** is already served by a separate streaming server (Wowza) and never
reaches files-rest, so it is unaffected.

This mirrors the `OffloadFileStorage` implementation already running in
production on `cds-rdm`, adapted to the CDS Videos (legacy Invenio) stack and
scoped to downloads only.

## Motivation

Today every file download is streamed byte-by-byte through the application:
`client -> nginx -> uwsgi_pass webapp -> ObjectResource.get -> storage.send_file()`,
and the app reads the whole file from EOS (over XRootD) and pushes it back
through uWSGI and nginx. Large downloads tie up a uWSGI worker for the entire
transfer, consuming worker slots, memory and CPU, and reducing the number of
concurrent requests the backend can serve.

Offloading downloads to nginx frees the uWSGI worker as soon as the redirect is
issued. nginx proxies the file straight from EOS to the client. This:

- removes large-file transfers from the limited uWSGI worker pool,
- reduces backend memory/CPU pressure,
- and keeps all access-control and statistics logic in the application (the
  request still enters the app; only the byte transfer is delegated).

## Detailed design

### Scope and guarantees

Only the files-rest download endpoint is offloaded. Concretely, the storage
`send_file()` override offloads **only** when **all** of the following hold:

- `FILES_REST_XSENDFILE_ENABLED` is `True` (master switch), and
- `CDS_EOS_OFFLOAD_ENABLED` is `True`, and
- `request.method == "GET"` (never `HEAD`), and
- `request.endpoint == "invenio_files_rest.object_api"`.

Everything else falls through to the normal in-app `super().send_file()`:

- video streaming (served by Wowza, never hits files-rest),
- `HEAD` probes,
- uploads (`PUT`),
- previewer reads (use `storage.open()`, not `send_file()`),
- IIIF image serving,
- any future non-download caller of `send_file()`.

On **any** error while resolving the EOS redirect (gateway unreachable,
unexpected status, timeout, auth failure) the override logs and transparently
falls back to in-app streaming, so a misconfiguration or EOS hiccup never
produces a user-visible download failure.

### Request flow (after)

```
GET /api/files/<bucket>/<key>
  -> nginx (uwsgi_pass webapp)
  -> ObjectResource.get               # permission check + file_downloaded signal
  -> OffloadEOSFileStorage.send_file   # resolves EOS URL, returns X-Accel-Redirect
  <- empty response: X-Accel-Redirect: /eos_storage/{scheme}/{host}/{port}/{path}
  -> nginx internal location ^/eos_storage/...
  -> proxy_pass to reconstructed EOS URL
  <- bytes streamed EOS -> client   (uWSGI worker already released)
```

### Code changes (cds-videos)

**1. New storage class — `cds/modules/xrootd/storage.py` (new file).**

Port `cds_rdm.files.OffloadFileStorage`, subclassing the EOS storage CDS Videos
already uses, with two differences: endpoint scoping, and no local-offload
branch (not needed here).

```python
from urllib.parse import quote, urlsplit, urlunsplit
import mimetypes, unicodedata, requests
from flask import current_app, make_response, request
from invenio_files_rest.helpers import sanitize_mimetype
from invenio_files_rest.storage.pyfs import pyfs_storage_factory

try:
    from invenio_xrootd.storage import EOSFileStorage as BaseFileStorage
    from requests_kerberos import DISABLED, HTTPKerberosAuth
except ImportError:
    HTTPKerberosAuth = type("obj", (object,), {})
    DISABLED = 3
    from invenio_files_rest.storage.pyfs import PyFSFileStorage as BaseFileStorage

# Only the files-rest download endpoint is offloaded.
OFFLOAD_ENDPOINTS = {"invenio_files_rest.object_api"}


class OffloadEOSFileStorage(BaseFileStorage):
    """Offload file downloads to nginx via X-Accel-Redirect to EOS."""

    def _get_auth_session(self):
        """requests session authenticated to EOS (X.509 if configured, else Kerberos)."""
        s = requests.Session()
        x509 = current_app.config.get("CDS_EOS_OFFLOAD_AUTH_X509", False)
        cert = current_app.config.get("CDS_EOS_OFFLOAD_X509_CERT_PATH")
        key = current_app.config.get("CDS_EOS_OFFLOAD_X509_KEY_PATH")
        if x509 and cert and key:
            s.cert = (cert, key)
            s.verify = False
        else:
            s.auth = HTTPKerberosAuth(DISABLED)
            s.verify = False
        return s

    def _get_eos_redirect_path(self):
        """Resolve the physical EOS URL and build the /eos_storage/... path."""
        host = current_app.config["CDS_EOS_OFFLOAD_HTTPHOST"]
        base = current_app.config["CDS_EOS_OFFLOAD_REDIRECT_BASE_PATH"]
        path = urlsplit(self.fileurl).path
        resp = self._get_auth_session().get(f"{host}/{path}", allow_redirects=False, timeout=5)
        if resp.status_code != 307:
            raise Exception(f"EOS redirect failed: {resp.status_code} {resp.text}")
        parts = urlsplit(resp.next.url)
        redirect = f"{base}/{parts.scheme}/{parts.hostname}/{parts.port}/{parts.path}"
        return urlunsplit(("", "", redirect, parts.query, ""))

    def send_file(self, filename, mimetype=None, restricted=True, checksum=None,
                  trusted=False, chunk_size=None, as_attachment=False, **kwargs):
        offload = (
            current_app.config.get("FILES_REST_XSENDFILE_ENABLED", False)
            and current_app.config.get("CDS_EOS_OFFLOAD_ENABLED", False)
            and request
            and request.method == "GET"
            and request.endpoint in OFFLOAD_ENDPOINTS
        )
        if not offload:
            return super().send_file(filename, mimetype=mimetype, restricted=restricted,
                                     checksum=checksum, trusted=trusted,
                                     chunk_size=chunk_size, as_attachment=as_attachment)
        response = make_response()
        try:
            response.headers["X-Accel-Redirect"] = self._get_eos_redirect_path()
        except Exception as ex:
            current_app.logger.exception(ex)
            return super().send_file(filename, mimetype=mimetype, restricted=restricted,
                                     checksum=checksum, trusted=trusted,
                                     chunk_size=chunk_size, as_attachment=as_attachment)
        # Buffering, mimetype, Content-Disposition (derived from `filename` so the
        # existing download-rename behaviour is preserved), and the security headers
        # are set exactly as in cds-rdm's OffloadFileStorage. Also sets:
        response.headers["Invenio-Offload"] = "true"
        return response


def offload_storage_factory(**kwargs):
    return pyfs_storage_factory(filestorage_class=OffloadEOSFileStorage, **kwargs)
```

**2. Wire the factory.** The storage factory is selected by the
`INVENIO_FILES_REST_STORAGE_FACTORY` env var in the deployment configmap (it
currently reads `invenio_xrootd:eos_storage_factory` and overrides the default
set in `cds/modules/xrootd/ext.py`). Switch both:

- configmap: `INVENIO_FILES_REST_STORAGE_FACTORY: cds.modules.xrootd.storage:offload_storage_factory`
- `cds/modules/xrootd/ext.py`: set the same default when `XROOTD_ENABLED`.

Because `OffloadEOSFileStorage` subclasses `EOSFileStorage`, write/read semantics
are unchanged; only `send_file` is extended. With `CDS_EOS_OFFLOAD_ENABLED=False`
it behaves byte-identically to today.

**3. Config — `cds/config.py` (Files section).**

```python
FILES_REST_XSENDFILE_ENABLED = False
CDS_EOS_OFFLOAD_ENABLED = False
CDS_EOS_OFFLOAD_HTTPHOST = "https://eosmedia.cern.ch:8444"
CDS_EOS_OFFLOAD_REDIRECT_BASE_PATH = "/eos_storage"
CDS_EOS_OFFLOAD_AUTH_X509 = False   # default to Kerberos (already provisioned in the web pod)
CDS_EOS_OFFLOAD_X509_CERT_PATH = "/etc/certificates/cert.pem"
CDS_EOS_OFFLOAD_X509_KEY_PATH = "/etc/certificates/key.pem"
```

### Deployment changes (cds-videos-openshift)

**nginx `site.conf` (configmap `nginx-config`).** Add an `internal` location that
reconstructs the EOS URL from the redirect path and proxies the bytes. Ported
from the cds-rdm `^/eos_storage/...` block:

```nginx
# /eos_storage/{scheme}/{host}/{port}/{path}
location ~ ^/eos_storage/(.*?)/(.*?)/(.*?)/(.*) {
    internal;
    resolver 137.138.16.5 ipv6=off;              # CERN DNS; confirm reachable from the nginx pod
    proxy_pass_request_body off;
    set $download_url $1://$2:$3/$4;
    proxy_set_header Host $2;
    proxy_set_header Authorization '';
    proxy_set_header Cookie '';
    add_header Accept-Ranges bytes;              # EOS HTTP gateway supports Range
    proxy_max_temp_file_size 0;                  # stream through, don't buffer to disk
    # re-expose upstream Content-Type/MD5/security headers (see cds-rdm nginx-config.yaml)
    proxy_pass $download_url$is_args$args;
}
```

**App configmap (`invenio-config`).** Add `INVENIO_FILES_REST_XSENDFILE_ENABLED`,
`INVENIO_CDS_EOS_OFFLOAD_ENABLED`, `INVENIO_CDS_EOS_OFFLOAD_HTTPHOST`,
`INVENIO_CDS_EOS_OFFLOAD_REDIRECT_BASE_PATH`, `INVENIO_CDS_EOS_OFFLOAD_AUTH_X509`,
and the switched `INVENIO_FILES_REST_STORAGE_FACTORY`.

**Auth.** The web pod already runs the `kerberos-ticket-manager` init+daemon
sidecar (`eos-keytab` secret) with a shared `/tmp` credentials cache, so the
Kerberos path works with no new secret. X.509 is optional and would require
mounting a `service-certificates` secret at `/etc/certificates` on the web pod.

### Verifying nginx -> EOS egress (deployment pre-requisite)

CDS Videos runs nginx as a **separate deployment** (not a web-pod sidecar), and
the app reaches EOS only over **XRootD (`root://`, port 1094)**. The offload
needs the nginx pod to reach the **EOS HTTP gateway (`:8444`)** and the **FST
data node** the gateway's `307` redirect points to (a different host/port). This
egress path is new and must be verified before enabling the flag. There are no
`NetworkPolicy`/`EgressFirewall` objects in the repo, so egress is governed at
the CERN network/namespace level.

Layered verification, cheapest first:

**(A) Discover the real redirect target** from the web pod (which can authenticate
to EOS). Read the `307 Location` for a published file to learn the FST host:port
nginx will need to reach:

```bash
oc -n <namespace> exec deploy/invenio-webapp -c invenio-webapp -- \
  bash -lc 'KRB5CCNAME=$(ls /tmp/krb5cc* 2>/dev/null | head -1); export KRB5CCNAME; \
    curl -sS -k --negotiate -u : -o /dev/null \
      -w "status=%{http_code} redirect=%{redirect_url}\n" \
      "https://eosmedia.cern.ch:8444/eos/media/cds/test/videos/files/<...>/data"'
```

Expect `status=307` and a `redirect=` URL. Note its host and port.

**(B) Probe egress with the nginx pod's network identity.** The nginx image has
no curl, so run a short-lived curl pod in the **same namespace** (representative,
since egress is namespace-level), targeting both the gateway and the FST host
from (A):

```bash
oc -n <namespace> run egress-test --rm -it --restart=Never \
  --image=registry.cern.ch/docker.io/curlimages/curl -- sh -c '
    curl -sS -k --max-time 10 -o /dev/null -w "gateway=%{http_code}\n" https://eosmedia.cern.ch:8444/ ;
    curl -sS -k --max-time 10 -o /dev/null -w "fst=%{http_code}\n"     https://<FST-host>:<FST-port>/ '
```

Any HTTP status back (even 400/403/404) proves TCP+TLS reachability; a timeout
means egress is blocked and a firewall opening is needed. Also check DNS from the
real nginx pod: `oc exec <nginx-pod> -c nginx -- getent hosts eosmedia.cern.ch`.

**(C) Definitive end-to-end test on sandbox.** Deploy the nginx `site.conf`
change with the app flag still off, then flip `CDS_EOS_OFFLOAD_ENABLED=True` on
sandbox and download a real file. Confirm the response carries
`X-Accel-Redirect`/`Invenio-Offload: true` and the bytes arrive correctly,
including a `Range` (resume) request. This exercises auth, DNS, egress and nginx
config together; rollback is a single flag flip.

### Behaviour invariants (each covered by a test)

- `HEAD` never offloaded.
- Non-`object_api` `send_file` callers never offloaded (streaming/IIIF/previewer).
- `file_downloaded` signal and download statistics still fire (the request still
  enters the app).
- Download-rename (`Content-Disposition` filename from the master, via
  `on_download_rename_file`) preserved.
- EOS/auth error -> transparent fallback to in-app streaming.
- `CDS_EOS_OFFLOAD_ENABLED=False` -> byte-identical to current behaviour.

### Test plan

**Unit** (`tests/unit/test_eos_offload.py`; add a storage-factory fixture to
`conftest.py`):

- correct `X-Accel-Redirect` path built from a mocked EOS `307`;
- fallback to `super().send_file` on non-307 / exception / timeout;
- `HEAD` -> no offload; `GET` on `object_api` -> offload; `GET` on another
  endpoint -> no offload;
- auth session selection (X.509 when configured+present, else Kerberos);
- `Content-Disposition` reflects the (renamed) `filename`; `Invenio-Offload: true`;
- disabled flags -> `super().send_file`.

**Integration** (Flask test client):

- `GET /api/files/<bucket>/<key>` with offload on -> `X-Accel-Redirect` and no
  body; off -> real body;
- `Range` request -> correct redirect;
- `file_downloaded` receiver still runs (assert renamed key).

**Staging matrix** (sandbox, manual — the parts tests cannot cover):

- large download through nginx->EOS (Kerberos), with and without `Range`/resume;
- playback/streaming **unchanged** (regression guard: still Wowza, not offloaded);
- download statistics still recorded;
- failure injection: EOS gateway unreachable -> graceful in-app fallback.

### Rollout

Feature-flagged and dark-launchable:

1. Merge code with `CDS_EOS_OFFLOAD_ENABLED=False` (no behaviour change).
2. Deploy nginx `site.conf` + resolver; verify egress (section above) on sandbox.
3. Flip `FILES_REST_XSENDFILE_ENABLED=True` + `CDS_EOS_OFFLOAD_ENABLED=True` on
   dev -> sandbox; validate the staging matrix.
4. Enable on prod. Rollback = flip the flag off.

### Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| nginx pod cannot reach EOS HTTP gateway / FST | verify egress on sandbox before enabling (gate in step 2) |
| accidental offload of non-download serving | endpoint allowlist (`object_api`) + explicit tests |
| EOS gateway flakiness | per-request try/except -> in-app fallback; 5s timeout (tunable) |
| Kerberos ticket expiry in pod | existing ticket-manager sidecar renews it |
| stats / rename regression | invariant tests + staging check |

### Work breakdown (estimate)

- Storage class + factory wiring + config: ~0.5 day
- Unit + integration tests + conftest fixture: ~1 day
- nginx configmap + app configmap + egress verification: ~0.5 day (plus infra coordination)
- Staging validation + rollout: ~1 day

Total ~3 days, critical path being nginx->EOS egress verification and staging
validation of the download (including `Range`) behaviour.

## References

- cds-rdm reference implementation: `cds_rdm/files.py` (`OffloadFileStorage`,
  `storage_factory`) and `cds-rdm-openshift/nginx-config.yaml`
  (`^/eos_storage/...` location).
- CDS Videos current EOS storage wiring: `cds/modules/xrootd/ext.py`.
