"""Archive validated FEC snapshots without confusing filings with certified ballots."""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def archive(snapshot, root, checked_at=None):
    # Accept only this explicitly reviewed dataset. Other datasets need their own validator.
    if snapshot.get('dataset') != 'fec_candidate_filings_2026':
        raise ValueError('Unsupported dataset')
    if snapshot.get('ballot_qualification_verified') is not False:
        raise ValueError('FEC filings cannot certify ballot qualification')
    records = snapshot['records']
    if not records or len(records) != snapshot['record_count']:
        raise ValueError('Invalid record count')
    digest = hashlib.sha256(canonical(records)).hexdigest()
    if digest != snapshot['records_sha256']:
        raise ValueError('Record hash mismatch')
    if snapshot['source']['url'] != 'https://www.fec.gov/files/bulk-downloads/2026/cn26.zip':
        raise ValueError('Unexpected source')
    root = Path(root)
    dataset = snapshot['dataset']
    relative = Path('history') / dataset / (digest + '.json')
    destination = root / relative
    if destination.exists():
        stored = json.loads(destination.read_text(encoding='utf-8'))
        if stored['records'] != records:
            raise ValueError('Archive collision or corruption')
    else:
        atomic_json(destination, snapshot)
    manifest_path = root / 'collection_status.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'schema_version': 1, 'datasets': {}}
    previous = manifest['datasets'].get(dataset, {})
    history = previous.get('versions', [])
    if not any(item['records_sha256'] == digest for item in history):
        history.append({'records_sha256': digest, 'retrieved_at': snapshot['retrieved_at'], 'path': str(relative), 'record_count': len(records)})
    manifest['datasets'][dataset] = {
        'source_url': snapshot['source']['url'],
        'last_successful_check_at': checked_at or datetime.now(timezone.utc).isoformat(),
        'latest_content_retrieved_at': snapshot['retrieved_at'],
        'records_sha256': digest,
        'record_count': len(records),
        'ballot_qualification_verified': False,
        'versions': history,
    }
    atomic_json(manifest_path, manifest)
    return manifest


if __name__ == '__main__':
    path = ROOT / 'public/data/fec_candidate_filings_2026.json'
    archive(json.loads(path.read_text(encoding='utf-8')), path.parent)
