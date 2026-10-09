"""Curated MITRE ATT&CK Enterprise subset (attributed to attack.mitre.org).
Used for coverage/gap analysis. Refreshable: replace this file from the official
STIX dataset. Version pinned so coverage math is reproducible."""

ATTACK_VERSION = "v14.1 (curated subset)"

TACTICS = [
    {"id": "TA0001", "name": "Initial Access", "short": "initial-access"},
    {"id": "TA0002", "name": "Execution", "short": "execution"},
    {"id": "TA0003", "name": "Persistence", "short": "persistence"},
    {"id": "TA0004", "name": "Privilege Escalation", "short": "privilege-escalation"},
    {"id": "TA0005", "name": "Defense Evasion", "short": "defense-evasion"},
    {"id": "TA0006", "name": "Credential Access", "short": "credential-access"},
    {"id": "TA0007", "name": "Discovery", "short": "discovery"},
    {"id": "TA0008", "name": "Lateral Movement", "short": "lateral-movement"},
    {"id": "TA0009", "name": "Collection", "short": "collection"},
    {"id": "TA0011", "name": "Command and Control", "short": "command-and-control"},
    {"id": "TA0010", "name": "Exfiltration", "short": "exfiltration"},
    {"id": "TA0040", "name": "Impact", "short": "impact"},
]

# technique id -> {name, tactics[]}
TECHNIQUES = [
    {"id": "T1190", "name": "Exploit Public-Facing Application", "tactics": ["TA0001"]},
    {"id": "T1133", "name": "External Remote Services", "tactics": ["TA0001", "TA0003"]},
    {"id": "T1566", "name": "Phishing", "tactics": ["TA0001"]},
    {"id": "T1078", "name": "Valid Accounts", "tactics": ["TA0001", "TA0003", "TA0004", "TA0005"]},
    {"id": "T1059", "name": "Command and Scripting Interpreter", "tactics": ["TA0002"]},
    {"id": "T1059.001", "name": "PowerShell", "tactics": ["TA0002"]},
    {"id": "T1059.003", "name": "Windows Command Shell", "tactics": ["TA0002"]},
    {"id": "T1053", "name": "Scheduled Task/Job", "tactics": ["TA0002", "TA0003", "TA0004"]},
    {"id": "T1136", "name": "Create Account", "tactics": ["TA0003"]},
    {"id": "T1547", "name": "Boot or Logon Autostart Execution", "tactics": ["TA0003", "TA0004"]},
    {"id": "T1543", "name": "Create or Modify System Process", "tactics": ["TA0003", "TA0004"]},
    {"id": "T1068", "name": "Exploitation for Privilege Escalation", "tactics": ["TA0004"]},
    {"id": "T1055", "name": "Process Injection", "tactics": ["TA0004", "TA0005"]},
    {"id": "T1562", "name": "Impair Defenses", "tactics": ["TA0005"]},
    {"id": "T1070", "name": "Indicator Removal", "tactics": ["TA0005"]},
    {"id": "T1110", "name": "Brute Force", "tactics": ["TA0006"]},
    {"id": "T1110.003", "name": "Password Spraying", "tactics": ["TA0006"]},
    {"id": "T1003", "name": "OS Credential Dumping", "tactics": ["TA0006"]},
    {"id": "T1555", "name": "Credentials from Password Stores", "tactics": ["TA0006"]},
    {"id": "T1046", "name": "Network Service Discovery", "tactics": ["TA0007"]},
    {"id": "T1018", "name": "Remote System Discovery", "tactics": ["TA0007"]},
    {"id": "T1087", "name": "Account Discovery", "tactics": ["TA0007"]},
    {"id": "T1021", "name": "Remote Services", "tactics": ["TA0008"]},
    {"id": "T1021.001", "name": "Remote Desktop Protocol", "tactics": ["TA0008"]},
    {"id": "T1570", "name": "Lateral Tool Transfer", "tactics": ["TA0008"]},
    {"id": "T1005", "name": "Data from Local System", "tactics": ["TA0009"]},
    {"id": "T1560", "name": "Archive Collected Data", "tactics": ["TA0009"]},
    {"id": "T1071", "name": "Application Layer Protocol", "tactics": ["TA0011"]},
    {"id": "T1071.004", "name": "DNS", "tactics": ["TA0011"]},
    {"id": "T1095", "name": "Non-Application Layer Protocol", "tactics": ["TA0011"]},
    {"id": "T1572", "name": "Protocol Tunneling", "tactics": ["TA0011"]},
    {"id": "T1041", "name": "Exfiltration Over C2 Channel", "tactics": ["TA0010"]},
    {"id": "T1048", "name": "Exfiltration Over Alternative Protocol", "tactics": ["TA0010"]},
    {"id": "T1486", "name": "Data Encrypted for Impact", "tactics": ["TA0040"]},
    {"id": "T1490", "name": "Inhibit System Recovery", "tactics": ["TA0040"]},
    {"id": "T1498", "name": "Network Denial of Service", "tactics": ["TA0040"]},
]
