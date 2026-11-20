"""Offline defensive review of a user-selected project folder."""
from pathlib import Path

RISK_PATTERNS=("eval(","exec(","subprocess.Popen(","shell=True","password","api_key","secret")

def audit_folder(folder):
    root=Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Selecione uma pasta existente.")
    findings=[]
    allowed={".py",".js",".ts",".html",".json",".yml",".yaml",".env.example"}
    for file in root.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in allowed:
            continue
        if any(part in {".git","node_modules","venv",".venv","dist","build"} for part in file.parts):
            continue
        try:
            if file.stat().st_size>500_000: continue
            lines=file.read_text(encoding="utf-8",errors="replace").splitlines()
        except OSError:
            continue
        for number,line in enumerate(lines,1):
            lower=line.lower()
            for pattern in RISK_PATTERNS:
                if pattern in lower:
                    findings.append({"file":str(file.relative_to(root)),"line":number,
                                     "pattern":pattern,"note":"Revisão manual necessária; ocorrência não prova vulnerabilidade."})
    return findings
