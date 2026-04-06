#目前是废稿，后面也许会启用
SETTINGS_PATH='../cfgs/settings.cfg.json'
def set(id:str,context):
    with open(SETTINGS_PATH,'r') as f:
        s=dict(f.read())
    s[id]=context
    with open(SETTINGS_PATH,'w') as f:
        f.write(str(s))
def get(id:str):
    with open(SETTINGS_PATH,'r') as f:
        return dict(f.read())[id]
def js():
    with open(SETTINGS_PATH,'r') as f:
        return dict(f.read())
    