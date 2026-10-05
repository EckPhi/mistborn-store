import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
p = root
c = json.loads((p/'config.json').read_text())
assert c['id'] == p.name
assert c['supported_architectures'] == ['amd64']
assert c['dynamic_config'] and not c['force_pull']
assert c['min_tipi_version'] == '4.10.1'
assert 1 <= c['port'] <= 65535
assert {'utilities'} == set(c['categories'])
for f in c['form_fields']:
    assert f['type'] in ('text', 'password', 'number')
    if f['type'] != 'number': assert f['required']
    assert f['env_variable'] in (p/'docker-compose.yml').read_text()
for name in ['logo.jpg','description.md']:
    assert (p/'metadata'/name).stat().st_size > 0
assert (p/'metadata/logo.jpg').read_bytes()[:2] == b'\xff\xd8'
print('Documented metadata invariants passed (not a live Runtipi schema check).')
