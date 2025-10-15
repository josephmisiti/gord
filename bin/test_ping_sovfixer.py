import os
import sys
import time
import json
import argparse
import pprint
import pathlib
import requests
from dotenv import load_dotenv

import pingintel_api


def _to_dict(obj):
    try:
        return obj.model_dump()
    except Exception:
        pass
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            from dataclasses import asdict
            return asdict(obj)
    except Exception:
        pass
    try:
        if isinstance(obj, dict):
            return obj
        return obj.__dict__
    except Exception:
        return {"repr": repr(obj)}


def _extract_status(d):
    if not isinstance(d, dict):
        return None
    status = d.get("status") or d.get("state") or d.get("current_status")
    if isinstance(status, dict):
        status = status.get("status") or status.get("code") or status.get("name")
    if not status:
        req = d.get("request") or {}
        status = req.get("status") or req.get("state")
    return status


def _get_token(env: str) -> str | None:
    # Try a few environment variable names commonly used
    names = []
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


def main(argv=None):
    load_dotenv()

    parser = argparse.ArgumentParser(description="Ping SOV Fixer API (async): upload SOV file, poll, and download outputs.")
    parser.add_argument("--file", required=True, help="Path to the SOV file to upload")
    parser.add_argument("--env", default="staging", choices=["staging", "prod"], help="Target environment")
    parser.add_argument("--interval", type=float, default=2.5, help="Polling interval seconds (default 2.5)")
    parser.add_argument("--timeout", type=int, default=600, help="Max seconds to wait (default 600)")
    parser.add_argument("--document-type", default="SOV", help="Document type (default 'SOV')")
    parser.add_argument("--outdir", default=".", help="Directory to save outputs when complete (default current dir)")
    args = parser.parse_args(argv)

    file_path = args.file
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    token = _get_token(args.env)
    if not token:
        print("Missing auth token. Set PING_SOVFIXER_AUTH_TOKEN[_STG/_PROD] or PING_DATA_*_AUTH_TOKEN in your environment.")
        sys.exit(2)

    client = pingintel_api.SOVFixerAPIClient(environment=args.env, auth_token=token)

    try:
        start_ret = client.fix_sov_async_start(file=file_path, document_type=args.document_type)
    except Exception as e:
        print(f"Error starting async SOV Fixer: {e}")
        sys.exit(3)

    print("Started async SOV Fixer:")
    pprint.pprint(start_ret)
    # Derive ID explicitly and use it for progress calls
    try:
        sovid = getattr(start_ret, 'id', None) or (start_ret.get('id') if isinstance(start_ret, dict) else None)
    except Exception:
        sovid = None
    if not sovid:
        print("Warning: Could not extract 'id' from start response; will pass full object to progress API.")
    else:
        print(f"Polling status for {sovid} every {args.interval}s...")

    t0 = time.time()
    last_status = None
    while True:
        if time.time() - t0 > args.timeout:
            print("Timeout reached while polling status.")
            sys.exit(4)
        try:
            resp = client.fix_sov_async_check_progress(sovid or start_ret)
        except Exception as e:
            print(f"Error polling async progress: {e}")
            time.sleep(args.interval)
            continue
        d = _to_dict(resp)
        status = _extract_status(d)
        req = d.get("request") if isinstance(d, dict) else None
        pct = req.get("pct_complete") if isinstance(req, dict) else None
        suffix = f" ({pct}%)" if isinstance(pct, (int, float)) else ""
        print(f"Status: {status if status is not None else 'unknown'}{suffix}", flush=True)
        last_status = status
        term = str(status).upper() if status else None
        if term in {"C", "COMPLETED", "F", "FAILED", "E", "ERROR", "DONE", "READY", "COMPLETE"}:
            print("Final response:")
            try:
                print(json.dumps(d, indent=2))
            except Exception:
                pprint.pprint(resp)
            if term in {"F", "FAILED", "E", "ERROR"}:
                sys.exit(5)
            # Attempt to download outputs if present
            try:
                outdir = pathlib.Path(args.outdir)
                outdir.mkdir(parents=True, exist_ok=True)
                outputs = (d.get('result', {}) or {}).get('outputs', []) if isinstance(d, dict) else []
                if not outputs:
                    print("No outputs found in response.")
                else:
                    print(f"Downloading {len(outputs)} output(s) to {outdir.resolve()} ...")
                    for idx, out in enumerate(outputs, 1):
                        # Try to derive a filename
                        name = out.get('filename') or out.get('name') or f"{sovid}_out_{idx}"
                        # Add extension if present
                        ext = None
                        fmt = out.get('format') or out.get('output_format') or out.get('extension')
                        if isinstance(fmt, str) and fmt.startswith('.'):
                            ext = fmt
                        elif isinstance(fmt, str):
                            ext = f".{fmt}"
                        if ext and not name.endswith(ext):
                            name = f"{name}{ext}"
                        dest = outdir / name
                        url = out.get('download_url') or out.get('url') or out.get('downloadUrl')
                        # Prefer using the API client session (handles auth) regardless of URL presence
                        try:
                            if url:
                                client.download_file(url, output_path=str(dest), actually_write=True)
                            else:
                                client.fix_sov_download(out, output_path=str(dest), actually_write=True)
                            print(f"  ✓ Saved {dest}")
                        except Exception as de:
                            # Last resort: direct request with auth header
                            try:
                                headers = {"Authorization": f"Bearer {token}"}
                                r = requests.get(url, headers=headers, timeout=60)
                                r.raise_for_status()
                                with open(dest, 'wb') as fh:
                                    fh.write(r.content)
                                print(f"  ✓ Saved {dest}")
                            except Exception as de2:
                                print(f"  ✗ Failed to download {url}: {de2}")
            except Exception as de:
                print(f"Download step encountered an error: {de}")
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
