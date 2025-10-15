import os
import time
import json
import pathlib
from typing import Optional, Tuple, Dict, Any, List

import requests
import pingintel_api


def _get_token(env: str) -> Optional[str]:
    if env == "staging":
        names = [
            "PING_SOVFIXER_AUTH_TOKEN_STG",
            "PING_SOVFIXER_AUTH_TOKEN",
            "PING_DATA_STG_AUTH_TOKEN",
        ]
    else:
        names = [
            "PING_SOVFIXER_AUTH_TOKEN",
            "PING_SOVFIXER_AUTH_TOKEN_PROD",
            "PING_DATA_PROD_AUTH_TOKEN",
            "PING_DATA_STG_AUTH_TOKEN",
        ]
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None


def start_and_poll(
    file_path: str,
    env: str = "staging",
    interval: float = 2.5,
    timeout: int = 600,
    outdir: str = ".",
) -> Tuple[bool, Dict[str, Any], List[pathlib.Path]]:
    token = _get_token(env)
    if not token:
        raise RuntimeError("Missing auth token. Set PING_SOVFIXER_AUTH_TOKEN[_STG/_PROD] or PING_DATA_*_AUTH_TOKEN.")

    client = pingintel_api.SOVFixerAPIClient(environment=env, auth_token=token)
    start_ret = client.fix_sov_async_start(file=file_path, document_type="SOV")
    sovid = getattr(start_ret, 'id', None) or (start_ret.get('id') if isinstance(start_ret, dict) else None)
    print("Started async SOV Fixer:")
    print(start_ret)
    if not sovid:
        print("Warning: Could not extract 'id' from start response; will pass full object to progress API.")
    else:
        print(f"Polling status for {sovid} every {interval}s...")

    t0 = time.time()
    last_pct = None
    final_resp: Dict[str, Any] = {}
    while True:
        if time.time() - t0 > timeout:
            raise TimeoutError("Timeout reached while polling status.")
        resp = client.fix_sov_async_check_progress(sovid or start_ret)
        if hasattr(resp, 'model_dump'):
            d = resp.model_dump()
        else:
            try:
                d = resp if isinstance(resp, dict) else resp.__dict__
            except Exception:
                d = {"repr": repr(resp)}
        req = d.get('request') or {}
        status = req.get('status') or d.get('status') or d.get('state')
        pct = req.get('pct_complete')
        if pct != last_pct:
            suffix = f" ({pct}%)" if isinstance(pct, (int, float)) else ""
            print(f"Status: {str(status).upper() if status else 'UNKNOWN'}{suffix}")
            last_pct = pct
        term = str(status).upper() if status else None
        if term in {"C", "COMPLETE", "COMPLETED", "DONE", "READY", "F", "FAILED", "E", "ERROR"}:
            final_resp = d
            break
        time.sleep(interval)

    # If failed, return without download
    if (final_resp.get('result') or {}).get('status') in ("FAILED", "ERROR") or (
        (final_resp.get('request') or {}).get('status') in ("FAILED", "ERROR")
    ):
        return False, final_resp, []

    # Download outputs
    outputs = (final_resp.get('result') or {}).get('outputs', [])
    out_paths: List[pathlib.Path] = []
    outdir_p = pathlib.Path(outdir)
    outdir_p.mkdir(parents=True, exist_ok=True)
    if not outputs:
        print("No outputs found in response.")
        return True, final_resp, out_paths
    print(f"Downloading {len(outputs)} output(s) to {outdir_p.resolve()} ...")
    for idx, out in enumerate(outputs, 1):
        name = out.get('filename') or out.get('name') or f"{sovid}_out_{idx}"
        fmt = out.get('format') or out.get('output_format') or out.get('extension')
        ext = None
        if isinstance(fmt, str) and fmt.startswith('.'): ext = fmt
        elif isinstance(fmt, str): ext = f".{fmt}"
        dest = outdir_p / (name if not ext or name.endswith(ext) else f"{name}{ext}")
        url = out.get('download_url') or out.get('url') or out.get('downloadUrl')
        try:
            if url:
                client.download_file(url, output_path=str(dest), actually_write=True)
            else:
                client.fix_sov_download(out, output_path=str(dest), actually_write=True)
            print(f"  ✓ Saved {dest}")
            out_paths.append(dest)
        except Exception as de:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                r = requests.get(url, headers=headers, timeout=60)
                r.raise_for_status()
                with open(dest, 'wb') as fh:
                    fh.write(r.content)
                print(f"  ✓ Saved {dest}")
                out_paths.append(dest)
            except Exception as de2:
                print(f"  ✗ Failed to download {url}: {de2}")
    return True, final_resp, out_paths

