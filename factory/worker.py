"""The only image-processing integration: frozen OpenAPI over HTTP."""
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import aiohttp
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from .config import ROOT, Config

CONTRACT_SHA256 = "836bf9654da8bc538de67434d9e94a4682fd1c127a08647283151d24485b7c74"

class WorkerError(RuntimeError):
    def __init__(self, code, message="", status=None):
        super().__init__(code + (": " + message if message else ""))
        self.code, self.status = code, status

class Contract:
    def __init__(self):
        content = (ROOT / "docs/contracts/worker-openapi.yaml").read_bytes()
        if hashlib.sha256(content).hexdigest() != CONTRACT_SHA256:
            raise WorkerError("BLOCKED_API_CONTRACT", "Snapshot hash changed")
        self.doc = yaml.safe_load(content)

    def validate(self, name, value):
        schema = {"$ref": f"#/components/schemas/{name}", "components": self.doc["components"]}
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))
        if errors:
            raise WorkerError("BLOCKED_API_CONTRACT", f"Invalid {name} response")
        return value

class WorkerClient:
    def __init__(self, config: Config):
        self.config, self.contract = config, Contract()
        host = urlparse(config.worker_url).hostname
        if config.mode == 'MOCK' and host not in ('127.0.0.1', 'localhost', '::1'):
            raise WorkerError("PAID_CALLS_DISABLED", "MOCK Worker must be loopback")
        if config.mode == 'REAL' and not (config.allow_paid and config.budget > 0 and config.attempt_cap > 0):
            raise WorkerError("PAID_CALLS_DISABLED", "Explicit approval and finite spending caps required")

    async def _request(self, method, path, schema=None, data=None, binary=False):
        headers = {"Authorization": "Bearer " + self.config.worker_token}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as s:
            async with s.request(method, self.config.worker_url.rstrip('/') + path, headers=headers, data=data) as r:
                if r.status >= 400:
                    try:
                        body = self.contract.validate('ErrorEnvelope', await r.json())
                    except (ValueError, aiohttp.ContentTypeError):
                        raise WorkerError("BLOCKED_API_CONTRACT", "Non-JSON error", r.status) from None
                    raise WorkerError(body['error']['code'], body['error']['message'], r.status)
                expected = (200,202) if method == 'POST' else (200,)
                if r.status not in expected:
                    raise WorkerError("BLOCKED_API_CONTRACT", "Unexpected HTTP status")
                if binary:
                    content = await r.read()
                    mime = r.headers.get('Content-Type','').split(';')[0]
                    if mime not in ('image/png','image/jpeg','image/webp'):
                        raise WorkerError("BLOCKED_API_CONTRACT", "Unexpected result MIME")
                    if hashlib.sha256(content).hexdigest() != r.headers.get('X-Content-SHA256'):
                        raise WorkerError("RESULT_HASH_MISMATCH")
                    return content, mime
                try:
                    return self.contract.validate(schema, await r.json())
                except (ValueError, aiohttp.ContentTypeError):
                    raise WorkerError("BLOCKED_API_CONTRACT", "Non-JSON response") from None

    async def capabilities(self):
        v = await self._request('GET','/v1/capabilities','Capabilities')
        if '1.0' not in v['contract_versions']:
            raise WorkerError("BLOCKED_API_CONTRACT", "Contract 1.0 unavailable")
        if self.config.mode == 'MOCK' and not (v.get('pipeline_version') or '').startswith('fake/'):
            raise WorkerError("PAID_CALLS_DISABLED", "MOCK requires the fake Worker")
        return v

    async def prepare_submission(self, request_id, original: Path, reference: Path, pair_id):
        caps = await self.capabilities()
        form = aiohttp.FormData()
        form.add_field('request_id',request_id)
        form.add_field('photo_pair_id',pair_id)
        import mimetypes
        for name, path in (('original',original),('reference',reference)):
            content = path.read_bytes()
            mime = mimetypes.guess_type(path.name)[0]
            if mime not in caps['supported_mime_types'] or len(content)>caps['max_file_bytes']:
                raise WorkerError("INVALID_INPUT", "Image exceeds Worker capabilities")
            form.add_field(name,content,filename=path.name,content_type=mime)
        return form

    async def submit(self, request_id, original: Path, reference: Path, pair_id):
        form=await self.prepare_submission(request_id,original,reference,pair_id)
        return await self.submit_prepared(request_id,form)

    async def submit_prepared(self,request_id,form):
        response = await self._request('POST','/v1/jobs','JobAccepted',data=form)
        if response['request_id'] != request_id:
            raise WorkerError("BLOCKED_API_CONTRACT", "Wrong request ID")
        return response

    async def status(self, request_id):
        response = await self._request('GET',f'/v1/jobs/{request_id}','JobStatus')
        if response['request_id'] != request_id:
            raise WorkerError("BLOCKED_API_CONTRACT", "Wrong request ID")
        return response

    async def result(self, request_id):
        return await self._request('GET',f'/v1/jobs/{request_id}/result',binary=True)
