import json,subprocess,tempfile
from pathlib import Path
config=json.loads(Path('configs/task_a_full_audit.json').read_text())
original=dict(config)
with tempfile.TemporaryDirectory() as tmp:
 for key in ['report','review_queue','near_duplicate_pairs']:
  config[key]=str(Path(tmp)/Path(config[key]).name)
 path=Path(tmp)/'config.json'; path.write_text(json.dumps(config))
 subprocess.run(['.venv/bin/python','scripts/audit_wildguard.py','--config',str(path)],check=True,stdout=subprocess.DEVNULL)
 for key in ['review_queue','near_duplicate_pairs']:
  assert Path(config[key]).read_bytes()==Path(original[key]).read_bytes(),key
 a=json.loads(Path(config['report']).read_text()); b=json.loads(Path(original['report']).read_text())
 a.pop('config'); b.pop('config'); assert a==b
 print('PASS: audit statistics, review sample and near-duplicate pairs reproduced exactly')
