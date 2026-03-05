import os
from dotenv import load_dotenv

load_dotenv()

ORGANIZATION = os.getenv("AZURE_DEVOPS_ORG")
PROJECT = os.getenv("AZURE_DEVOPS_PROJECT")
PAT = os.getenv("AZURE_DEVOPS_PAT")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# Estados que indicam item concluído (separados por vírgula)
# Agile/Scrum: Done | CMMI: Closed,Resolved
DONE_STATES = {
    s.strip().lower()
    for s in os.getenv("DONE_STATES", "Done,Closed,Resolved").split(",")
}

# Tipos de work item que indicam retrabalho (separados por vírgula)
# Agile/Scrum/CMMI: Bug | Scrum também: Impediment
REWORK_TYPES = {
    t.strip().lower()
    for t in os.getenv("REWORK_TYPES", "Bug").split(",")
}

# Estados que indicam retrabalho (separados por vírgula)
# Independe do processo: Reopened é sinal direto de retrabalho
REWORK_STATES = {
    s.strip().lower()
    for s in os.getenv("REWORK_STATES", "Reopened").split(",")
}

# Tipos excluídos da análise de backlog (separados por vírgula)
# Artefatos de teste não são backlog de desenvolvimento
EXCLUDE_TYPES = {
    t.strip().lower()
    for t in os.getenv("EXCLUDE_TYPES", "Test Plan,Test Suite,Test Case").split(",")
}

# GCS — opcionais: upload só ocorre se GCS_BUCKET estiver configurado
GCS_BUCKET = os.getenv("GCS_BUCKET")
GCS_PREFIX = os.getenv("GCS_PREFIX", "azure-snapshot").strip("/")
