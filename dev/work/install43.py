from pathlib import Path
import hashlib,json,shutil,datetime,sys
root=Path(__file__).resolve().parents[1]
stage=root/'outputs/investingOS_ChatGPT-update'
dest=Path('/Users/dcr3104/Desktop/investingOS_ChatGPT')
manifest=root/'work/desktop-preconditions.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
files=sorted(p for p in stage.rglob('*') if p.is_file())
if '--prepare' in sys.argv:
 manifest.write_text(json.dumps({str(p.relative_to(stage)):sha(dest/p.relative_to(stage)) for p in files},indent=2));print('Prepared 13 bounded targets');sys.exit()
expected=json.loads(manifest.read_text())
assert len(files)==13
for rel,h in expected.items():assert sha(dest/rel)==h, 'Changed target: '+rel
backup=dest/'archive'/('pre-chatgpt-v4.3-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
for p in files:
 rel=p.relative_to(stage);target=dest/rel
 if target.exists():
  saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 if target.suffix=='.command':target.chmod(0o755)
 assert sha(p)==sha(target)
report={'backup':str(backup),'files':[str(p.relative_to(stage)) for p in files],'verified':True,'at':datetime.datetime.now().astimezone().isoformat()}
(root/'outputs/investingOS-v4.2/audit/desktop-deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
