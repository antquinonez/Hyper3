"""
Building and Querying a Threat Intelligence Knowledge Base
==========================================================

This example builds a realistic cyber threat intelligence graph with 100+
nodes and 200+ edges, then demonstrates how to query it for actionable
security insights that would be impractical to find by manual inspection.

Use case: A security operations center (SOC) analyst needs to understand
which CVEs are most heavily linked to active threat actors, find isolated
indicators that lack context, trace attack paths from specific APT groups
to targeted industries, and identify which threat ecosystems are connected
through shared infrastructure or malware.

Run with:
    .venv/bin/python examples/basic/01_knowledge_basics.py
"""

from __future__ import annotations

from hyper3 import CognitiveMemory, Modality


THREAT_ACTORS = [
    {"label": "APT28", "data": {"sophistication": "high", "origin": "Russia", "targets": ["government", "military"]}},
    {"label": "APT29", "data": {"sophistication": "high", "origin": "Russia", "targets": ["government", "think_tanks"]}},
    {"label": "APT41", "data": {"sophistication": "high", "origin": "China", "targets": ["telecom", "healthcare", "technology"]}},
    {"label": "APT38", "data": {"sophistication": "high", "origin": "North_Korea", "targets": ["financial", "cryptocurrency"]}},
    {"label": "Lazarus", "data": {"sophistication": "high", "origin": "North_Korea", "targets": ["financial", "defense", "cryptocurrency"]}},
    {"label": "APT33", "data": {"sophistication": "medium", "origin": "Iran", "targets": ["energy", "aerospace"]}},
    {"label": "APT35", "data": {"sophistication": "medium", "origin": "Iran", "targets": ["government", "academia", "media"]}},
    {"label": "FIN7", "data": {"sophistication": "high", "origin": "Eastern_Europe", "targets": ["retail", "hospitality", "restaurant"]}},
    {"label": "FIN6", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "targets": ["retail", "e_commerce"]}},
    {"label": "Carbanak", "data": {"sophistication": "high", "origin": "Eastern_Europe", "targets": ["financial", "banking"]}},
    {"label": "Turla", "data": {"sophistication": "high", "origin": "Russia", "targets": ["government", "diplomacy", "military"]}},
    {"label": "Sandworm", "data": {"sophistication": "high", "origin": "Russia", "targets": ["energy", "telecom", "government"]}},
    {"label": "Equation_Group", "data": {"sophistication": "very_high", "origin": "USA", "targets": ["telecom", "government", "technology"]}},
    {"label": "APT10", "data": {"sophistication": "high", "origin": "China", "targets": ["technology", "aerospace", "managed_service_providers"]}},
    {"label": "APT1", "data": {"sophistication": "medium", "origin": "China", "targets": ["technology", "aerospace", "telecom"]}},
    {"label": "DarkHotel", "data": {"sophistication": "high", "origin": "North_Korea", "targets": ["executives", "government"]}},
    {"label": "OceanLotus", "data": {"sophistication": "medium", "origin": "Vietnam", "targets": ["government", "construction", "manufacturing"]}},
    {"label": "MuddyWater", "data": {"sophistication": "medium", "origin": "Iran", "targets": ["government", "telecom", "energy"]}},
    {"label": "FIN12", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "targets": ["healthcare"]}},
    {"label": "Conti", "data": {"sophistication": "high", "origin": "Eastern_Europe", "targets": ["healthcare", "government", "technology"]}},
    {"label": "LockBit", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "targets": ["manufacturing", "retail", "healthcare"]}},
    {"label": "BlackBasta", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "targets": ["manufacturing", "construction"]}},
    {"label": "Volt_Typhoon", "data": {"sophistication": "high", "origin": "China", "targets": ["energy", "telecom", "water"]}},
    {"label": "APT43", "data": {"sophistication": "medium", "origin": "North_Korea", "targets": ["think_tanks", "academia"]}},
    {"label": "Charming_Kitten", "data": {"sophistication": "medium", "origin": "Iran", "targets": ["academia", "media", "government"]}},
    {"label": "Fancy_Bear", "data": {"sophistication": "high", "origin": "Russia", "targets": ["government", "military", "elections"]}},
    {"label": "TA505", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "targets": ["financial", "retail"]}},
    {"label": "Hafnium", "data": {"sophistication": "high", "origin": "China", "targets": ["defense", "technology", "infectious_disease_research"]}},
    {"label": "Kimsuky", "data": {"sophistication": "medium", "origin": "North_Korea", "targets": ["think_tanks", "government", "academia"]}},
    {"label": "Clop", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "targets": ["financial", "technology", "government"]}},
    {"label": "Royal", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "targets": ["manufacturing", "healthcare"]}},
    {"label": "Play", "data": {"sophistication": "medium", "origin": "Unknown", "targets": ["technology", "government"]}},
]

CVES = [
    {"label": "CVE-2024-21762", "data": {"cvss": 9.8, "product": "FortiOS", "year": 2024}},
    {"label": "CVE-2024-3400", "data": {"cvss": 10.0, "product": "PAN-OS", "year": 2024}},
    {"label": "CVE-2023-44228", "data": {"cvss": 10.0, "product": "Apache_Log4j2", "year": 2023}},
    {"label": "CVE-2023-34362", "data": {"cvss": 9.8, "product": "MOVEit_Transfer", "year": 2023}},
    {"label": "CVE-2024-1709", "data": {"cvss": 10.0, "product": "ConnectWise_ScreenConnect", "year": 2024}},
    {"label": "CVE-2023-46805", "data": {"cvss": 8.1, "product": "Ivanti_Connect_Secure", "year": 2023}},
    {"label": "CVE-2024-21893", "data": {"cvss": 8.1, "product": "Ivanti_Policy_Secure", "year": 2024}},
    {"label": "CVE-2023-27997", "data": {"cvss": 9.2, "product": "FortiOS_SSL-VPN", "year": 2023}},
    {"label": "CVE-2024-27198", "data": {"cvss": 9.8, "product": "JetBrains_TeamCity", "year": 2024}},
    {"label": "CVE-2023-22515", "data": {"cvss": 10.0, "product": "Atlassian_Confluence", "year": 2023}},
    {"label": "CVE-2023-46604", "data": {"cvss": 10.0, "product": "Apache_ActiveMQ", "year": 2023}},
    {"label": "CVE-2024-23897", "data": {"cvss": 9.8, "product": "Jenkins_CLI", "year": 2024}},
    {"label": "CVE-2023-36884", "data": {"cvss": 8.8, "product": "Microsoft_Office", "year": 2023}},
    {"label": "CVE-2023-29357", "data": {"cvss": 9.8, "product": "Microsoft_SharePoint", "year": 2023}},
    {"label": "CVE-2024-21412", "data": {"cvss": 8.1, "product": "Microsoft_Windows_Kerberos", "year": 2024}},
    {"label": "CVE-2023-4966", "data": {"cvss": 7.5, "product": "NetScaler_ADC", "year": 2023}},
    {"label": "CVE-2024-0204", "data": {"cvss": 9.8, "product": "GoAnywhere_MFT", "year": 2024}},
    {"label": "CVE-2023-20269", "data": {"cvss": 9.8, "product": "Cisco_AnyConnect", "year": 2023}},
    {"label": "CVE-2024-20353", "data": {"cvss": 8.6, "product": "Cisco_IOS_XE", "year": 2024}},
    {"label": "CVE-2023-38545", "data": {"cvss": 9.8, "product": "curl SOCKS5", "year": 2023}},
    {"label": "CVE-2024-0012", "data": {"cvss": 9.8, "product": "PAN-OS_Management", "year": 2024}},
    {"label": "CVE-2023-20198", "data": {"cvss": 10.0, "product": "Cisco_IOS_XE_WebUI", "year": 2023}},
    {"label": "CVE-2024-47176", "data": {"cvss": 8.6, "product": "CUPS", "year": 2024}},
    {"label": "CVE-2023-42793", "data": {"cvss": 9.8, "product": "iOS_Kernel", "year": 2023}},
    {"label": "CVE-2024-38063", "data": {"cvss": 9.8, "product": "Windows_TCP/IP", "year": 2024}},
    {"label": "CVE-2023-43177", "data": {"cvss": 9.8, "product": "Darktrace_Immune_System", "year": 2023}},
    {"label": "CVE-2024-24919", "data": {"cvss": 8.6, "product": "Check_Point_Gateway", "year": 2024}},
    {"label": "CVE-2023-35078", "data": {"cvss": 10.0, "product": "Ivanti_EPM", "year": 2023}},
    {"label": "CVE-2024-29847", "data": {"cvss": 9.8, "product": "Ivanti_VTM", "year": 2024}},
    {"label": "CVE-2023-49103", "data": {"cvss": 9.8, "product": "ownCloud", "year": 2023}},
    {"label": "CVE-2024-4577", "data": {"cvss": 9.8, "product": "PHP_CGI", "year": 2024}},
    {"label": "CVE-2023-50164", "data": {"cvss": 9.8, "product": "Apache_Struts", "year": 2023}},
]

MALWARE = [
    {"label": "Cobalt_Strike", "data": {"type": "RAT", "platform": "Windows"}},
    {"label": "Emotet", "data": {"type": "Trojan", "platform": "Windows"}},
    {"label": "TrickBot", "data": {"type": "Trojan", "platform": "Windows"}},
    {"label": "Ryuk", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "Conti_Ransomware", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "LockBit_Builder", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "QakBot", "data": {"type": "Trojan", "platform": "Windows"}},
    {"label": "Mimikatz", "data": {"type": "Credential_Theft", "platform": "Windows"}},
    {"label": "BloodHound", "data": {"type": "Recon", "platform": "Windows"}},
    {"label": "PlugX", "data": {"type": "RAT", "platform": "Windows"}},
    {"label": "ShadowPad", "data": {"type": "Backdoor", "platform": "Multi"}},
    {"label": "SUNBURST", "data": {"type": "Backdoor", "platform": "Windows"}},
    {"label": "Stuxnet", "data": {"type": "Worm", "platform": "Windows"}},
    {"label": "Carbanak_DLL", "data": {"type": "Backdoor", "platform": "Windows"}},
    {"label": "Zeus", "data": {"type": "Trojan", "platform": "Windows"}},
    {"label": "Dridex", "data": {"type": "Trojan", "platform": "Windows"}},
    {"label": "BlackBasta_Ransomware", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "Play_Ransomware", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "AsyncRAT", "data": {"type": "RAT", "platform": "Windows"}},
    {"label": "Sliver", "data": {"type": "RAT", "platform": "Multi"}},
    {"label": "Royal_Ransomware", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "Agent_Tesla", "data": {"type": "Stealer", "platform": "Windows"}},
]

TTPS = [
    {"label": "T1566_Phishing", "data": {"tactic": "Initial_Access", "difficulty": "low"}},
    {"label": "T1190_Exploit_Public_App", "data": {"tactic": "Initial_Access", "difficulty": "medium"}},
    {"label": "T1078_Valid_Accounts", "data": {"tactic": "Defense_Evasion", "difficulty": "low"}},
    {"label": "T1059_Command_Scripting", "data": {"tactic": "Execution", "difficulty": "low"}},
    {"label": "T1053_Scheduled_Task", "data": {"tactic": "Persistence", "difficulty": "medium"}},
    {"label": "T1547_Boot_Autostart", "data": {"tactic": "Persistence", "difficulty": "medium"}},
    {"label": "T1003_Credential_Dumping", "data": {"tactic": "Credential_Access", "difficulty": "medium"}},
    {"label": "T1082_System_Info", "data": {"tactic": "Discovery", "difficulty": "low"}},
    {"label": "T1083_File_Discovery", "data": {"tactic": "Discovery", "difficulty": "low"}},
    {"label": "T1041_Exfiltration_Over_C2", "data": {"tactic": "Exfiltration", "difficulty": "medium"}},
    {"label": "T1486_Data_Encrypted_Impact", "data": {"tactic": "Impact", "difficulty": "low"}},
    {"label": "T1490_Inhibit_Recovery", "data": {"tactic": "Impact", "difficulty": "low"}},
    {"label": "T1562_Impair_Defenses", "data": {"tactic": "Defense_Evasion", "difficulty": "medium"}},
    {"label": "T1071_App_Layer_Protocol", "data": {"tactic": "Command_And_Control", "difficulty": "low"}},
    {"label": "T1105_Ingress_Tool_Transfer", "data": {"tactic": "Command_And_Control", "difficulty": "low"}},
    {"label": "T1021_Remote_Services", "data": {"tactic": "Lateral_Movement", "difficulty": "medium"}},
    {"label": "T1048_Alternative_Exfil", "data": {"tactic": "Exfiltration", "difficulty": "medium"}},
    {"label": "T1133_External_Remote", "data": {"tactic": "Initial_Access", "difficulty": "medium"}},
    {"label": "T1055_Process_Injection", "data": {"tactic": "Defense_Evasion", "difficulty": "high"}},
    {"label": "T1548_Abuse_Elevate", "data": {"tactic": "Privilege_Escalation", "difficulty": "medium"}},
    {"label": "T1098_Account_Manipulation", "data": {"tactic": "Persistence", "difficulty": "medium"}},
    {"label": "T1110_Brute_Force", "data": {"tactic": "Credential_Access", "difficulty": "low"}},
    {"label": "T1036_Masquerading", "data": {"tactic": "Defense_Evasion", "difficulty": "low"}},
]

INFRASTRUCTURE = [
    {"label": "C2_VPN_GATE_01", "data": {"type": "C2_server", "location": "Russia"}},
    {"label": "C2_CLOUD_PROXY_02", "data": {"type": "C2_server", "location": "Netherlands"}},
    {"label": "C2_RESIDENTIAL_03", "data": {"type": "C2_server", "location": "USA"}},
    {"label": "BOTNET_MIRAI_NET", "data": {"type": "Botnet", "location": "Distributed"}},
    {"label": "C2_TOR_EXIT_04", "data": {"type": "C2_server", "location": "Germany"}},
    {"label": "PROXY_VPN_CHAIN_05", "data": {"type": "Proxy_chain", "location": "Romania"}},
    {"label": "C2_DNS_TUNNEL_06", "data": {"type": "C2_server", "location": "China"}},
    {"label": "C2_CDN_FRONT_07", "data": {"type": "C2_server", "location": "Cloudflare"}},
    {"label": "BOTNET_EMOTET_MESH", "data": {"type": "Botnet", "location": "Distributed"}},
    {"label": "C2_CUSTOM_PROTO_08", "data": {"type": "C2_server", "location": "Iran"}},
    {"label": "EXFIL_DROP_09", "data": {"type": "Exfil_server", "location": "Seychelles"}},
    {"label": "C2_SOCIAL_MEDIA_10", "data": {"type": "C2_server", "location": "Twitter_API"}},
    {"label": "PHISHING_KIT_HOST_11", "data": {"type": "Phishing_infrastructure", "location": "Bulgaria"}},
    {"label": "C2_WEB_SHELL_12", "data": {"type": "C2_server", "location": "Panama"}},
    {"label": "BOTNET_TRICKBOT_POOL", "data": {"type": "Botnet", "location": "Distributed"}},
    {"label": "EXFIL_CLOUD_STORAGE_13", "data": {"type": "Exfil_server", "location": "AWS_S3"}},
]

INDUSTRIES = [
    {"label": "GOV", "data": {"sector": "Government"}},
    {"label": "MIL", "data": {"sector": "Military"}},
    {"label": "FIN", "data": {"sector": "Financial"}},
    {"label": "HC", "data": {"sector": "Healthcare"}},
    {"label": "TECH", "data": {"sector": "Technology"}},
    {"label": "ENERGY", "data": {"sector": "Energy"}},
    {"label": "TELECOM", "data": {"sector": "Telecom"}},
    {"label": "RETAIL", "data": {"sector": "Retail"}},
    {"label": "MFG", "data": {"sector": "Manufacturing"}},
    {"label": "AERO", "data": {"sector": "Aerospace"}},
    {"label": "ACAD", "data": {"sector": "Academia"}},
    {"label": "MEDIA", "data": {"sector": "Media"}},

    {"label": "CRYPTO", "data": {"sector": "Cryptocurrency"}},
    {"label": "HOSPITALITY", "data": {"sector": "Hospitality"}},
    {"label": "MSP", "data": {"sector": "Managed_Service_Providers"}},
]

RELATIONSHIP_MAP = {
    "uses": [
        ("APT28", "Cobalt_Strike"), ("APT28", "Mimikatz"), ("APT28", "PlugX"),
        ("APT29", "SUNBURST"), ("APT29", "Mimikatz"),
        ("APT41", "PlugX"), ("APT41", "ShadowPad"), ("APT41", "Cobalt_Strike"),
        ("APT38", "Zeus"), ("APT38", "Agent_Tesla"),
        ("Lazarus", "Cobalt_Strike"), ("Lazarus", "Dridex"),
        ("APT33", "Cobalt_Strike"), ("APT33", "Sliver"),
        ("APT35", "AsyncRAT"), ("APT35", "PlugX"),
        ("FIN7", "Carbanak_DLL"), ("FIN7", "Cobalt_Strike"),
        ("FIN6", "TrickBot"), ("FIN6", "Emotet"),
        ("Carbanak", "Carbanak_DLL"), ("Carbanak", "Zeus"),
        ("Turla", "Cobalt_Strike"), ("Turla", "Mimikatz"),
        ("Sandworm", "Cobalt_Strike"), ("Sandworm", "Mimikatz"),
        ("Equation_Group", "Stuxnet"), ("Equation_Group", "Mimikatz"),
        ("APT10", "PlugX"), ("APT10", "ShadowPad"),
        ("APT1", "Mimikatz"), ("APT1", "PlugX"),
        ("DarkHotel", "Cobalt_Strike"), ("DarkHotel", "Agent_Tesla"),
        ("OceanLotus", "Cobalt_Strike"), ("OceanLotus", "Mimikatz"),
        ("MuddyWater", "AsyncRAT"), ("MuddyWater", "Sliver"),
        ("FIN12", "TrickBot"), ("FIN12", "Cobalt_Strike"),
        ("Conti", "Conti_Ransomware"), ("Conti", "Cobalt_Strike"),
        ("LockBit", "LockBit_Builder"), ("LockBit", "Cobalt_Strike"),
        ("BlackBasta", "BlackBasta_Ransomware"), ("BlackBasta", "QakBot"),
        ("Volt_Typhoon", "Cobalt_Strike"), ("Volt_Typhoon", "Mimikatz"),
        ("APT43", "AsyncRAT"), ("APT43", "Sliver"),
        ("Charming_Kitten", "AsyncRAT"), ("Charming_Kitten", "Agent_Tesla"),
        ("Fancy_Bear", "Cobalt_Strike"), ("Fancy_Bear", "Mimikatz"),
        ("TA505", "Emotet"), ("TA505", "Dridex"),
        ("Hafnium", "Cobalt_Strike"), ("Hafnium", "Sliver"),
        ("Kimsuky", "AsyncRAT"), ("Kimsuky", "Agent_Tesla"),
        ("Clop", "LockBit_Builder"), ("Clop", "TrickBot"),
        ("Royal", "Royal_Ransomware"), ("Royal", "Cobalt_Strike"),
        ("Play", "Play_Ransomware"), ("Play", "Cobalt_Strike"),
    ],
    "exploits": [
        ("APT28", "CVE-2023-44228"), ("APT28", "CVE-2023-20198"),
        ("APT29", "CVE-2023-22515"), ("APT29", "CVE-2024-3400"),
        ("APT41", "CVE-2024-21762"), ("APT41", "CVE-2023-27997"),
        ("APT38", "CVE-2023-46604"),
        ("Lazarus", "CVE-2024-4577"), ("Lazarus", "CVE-2023-44228"),
        ("APT33", "CVE-2023-44228"), ("APT33", "CVE-2024-3400"),
        ("APT35", "CVE-2023-46805"), ("APT35", "CVE-2024-21893"),
        ("FIN7", "CVE-2023-34362"), ("FIN7", "CVE-2024-1709"),
        ("FIN6", "CVE-2023-44228"), ("FIN6", "CVE-2024-0204"),
        ("Carbanak", "CVE-2023-29357"),
        ("Turla", "CVE-2023-44228"), ("Turla", "CVE-2023-20269"),
        ("Sandworm", "CVE-2023-20198"), ("Sandworm", "CVE-2024-3400"),
        ("Equation_Group", "CVE-2023-42793"),
        ("APT10", "CVE-2023-44228"), ("APT10", "CVE-2024-27198"),
        ("APT1", "CVE-2023-38545"),
        ("DarkHotel", "CVE-2023-4966"),
        ("Hafnium", "CVE-2023-44228"), ("Hafnium", "CVE-2023-22515"),
        ("Volt_Typhoon", "CVE-2024-3400"), ("Volt_Typhoon", "CVE-2023-44228"),
        ("Clop", "CVE-2023-34362"), ("Clop", "CVE-2024-0204"),
        ("Royal", "CVE-2024-1709"), ("Royal", "CVE-2023-44228"),
        ("Play", "CVE-2024-23897"),
        ("BlackBasta", "CVE-2024-0012"), ("BlackBasta", "CVE-2023-44228"),
        ("LockBit", "CVE-2023-44228"), ("LockBit", "CVE-2024-1709"),
        ("MuddyWater", "CVE-2023-46805"), ("MuddyWater", "CVE-2024-24919"),
        ("Kimsuky", "CVE-2023-36884"),
    ],
    "targets": [
        ("APT28", "GOV"), ("APT28", "MIL"),
        ("APT29", "GOV"), ("APT29", "TECH"),
        ("APT41", "TELECOM"), ("APT41", "HC"), ("APT41", "TECH"),
        ("APT38", "FIN"), ("APT38", "CRYPTO"),
        ("Lazarus", "FIN"), ("Lazarus", "CRYPTO"),
        ("APT33", "ENERGY"), ("APT33", "AERO"),
        ("APT35", "GOV"), ("APT35", "ACAD"), ("APT35", "MEDIA"),
        ("FIN7", "RETAIL"), ("FIN7", "HOSPITALITY"),
        ("FIN6", "RETAIL"),
        ("Carbanak", "FIN"),
        ("Turla", "GOV"), ("Turla", "MIL"),
        ("Sandworm", "ENERGY"), ("Sandworm", "TELECOM"),
        ("Equation_Group", "TELECOM"), ("Equation_Group", "TECH"),
        ("APT10", "TECH"), ("APT10", "AERO"), ("APT10", "MSP"),
        ("APT1", "TECH"), ("APT1", "AERO"),
        ("DarkHotel", "GOV"),
        ("OceanLotus", "GOV"), ("OceanLotus", "MFG"),
        ("MuddyWater", "GOV"), ("MuddyWater", "TELECOM"),
        ("FIN12", "HC"),
        ("Conti", "HC"), ("Conti", "GOV"), ("Conti", "TECH"),
        ("LockBit", "MFG"), ("LockBit", "RETAIL"), ("LockBit", "HC"),
        ("BlackBasta", "MFG"),
        ("Volt_Typhoon", "ENERGY"), ("Volt_Typhoon", "TELECOM"),
        ("Charming_Kitten", "ACAD"), ("Charming_Kitten", "MEDIA"),
        ("Fancy_Bear", "GOV"), ("Fancy_Bear", "MIL"),
        ("TA505", "FIN"), ("TA505", "RETAIL"),
        ("Hafnium", "TECH"), ("Hafnium", "AERO"),
        ("Kimsuky", "ACAD"), ("Kimsuky", "GOV"),
        ("Clop", "FIN"), ("Clop", "TECH"),
        ("Royal", "MFG"), ("Royal", "HC"),
        ("Play", "TECH"), ("Play", "GOV"),
    ],
    "variant_of": [
        ("Emotet", "Zeus"),
        ("TrickBot", "Zeus"),
        ("QakBot", "Zeus"),
        ("Dridex", "Zeus"),
        ("LockBit_Builder", "BlackBasta_Ransomware"),
        ("Royal_Ransomware", "BlackBasta_Ransomware"),
        ("Conti_Ransomware", "Ryuk"),
        ("Play_Ransomware", "Royal_Ransomware"),
    ],
    "communicates_with": [
        ("Cobalt_Strike", "C2_VPN_GATE_01"),
        ("Cobalt_Strike", "C2_CLOUD_PROXY_02"),
        ("Emotet", "BOTNET_EMOTET_MESH"),
        ("TrickBot", "BOTNET_TRICKBOT_POOL"),
        ("QakBot", "BOTNET_TRICKBOT_POOL"),
        ("SUNBURST", "C2_CDN_FRONT_07"),
        ("PlugX", "C2_DNS_TUNNEL_06"),
        ("ShadowPad", "C2_DNS_TUNNEL_06"),
        ("AsyncRAT", "C2_RESIDENTIAL_03"),
        ("Sliver", "C2_TOR_EXIT_04"),
        ("Conti_Ransomware", "C2_VPN_GATE_01"),
        ("LockBit_Builder", "C2_CLOUD_PROXY_02"),
        ("BlackBasta_Ransomware", "EXFIL_CLOUD_STORAGE_13"),
        ("Agent_Tesla", "EXFIL_DROP_09"),
        ("Carbanak_DLL", "C2_CUSTOM_PROTO_08"),
        ("Mimikatz", "C2_WEB_SHELL_12"),
        ("BloodHound", "C2_RESIDENTIAL_03"),
        ("Dridex", "EXFIL_DROP_09"),
        ("Play_Ransomware", "C2_SOCIAL_MEDIA_10"),
        ("Royal_Ransomware", "EXFIL_CLOUD_STORAGE_13"),
        ("Zeus", "BOTNET_MIRAI_NET"),
    ],
    "attributed_to": [
        ("C2_VPN_GATE_01", "APT28"),
        ("C2_CLOUD_PROXY_02", "FIN7"),
        ("C2_RESIDENTIAL_03", "APT35"),
        ("BOTNET_MIRAI_NET", "FIN6"),
        ("C2_TOR_EXIT_04", "APT33"),
        ("PROXY_VPN_CHAIN_05", "TA505"),
        ("C2_DNS_TUNNEL_06", "APT10"),
        ("C2_CDN_FRONT_07", "APT29"),
        ("BOTNET_EMOTET_MESH", "TA505"),
        ("C2_CUSTOM_PROTO_08", "Carbanak"),
        ("EXFIL_DROP_09", "FIN6"),
        ("C2_SOCIAL_MEDIA_10", "APT35"),
        ("PHISHING_KIT_HOST_11", "FIN7"),
        ("C2_WEB_SHELL_12", "Volt_Typhoon"),
        ("BOTNET_TRICKBOT_POOL", "FIN12"),
        ("EXFIL_CLOUD_STORAGE_13", "Conti"),
    ],
    "mitigates": [
        ("T1566_Phishing", "CVE-2023-36884"),
        ("T1190_Exploit_Public_App", "CVE-2024-3400"),
        ("T1190_Exploit_Public_App", "CVE-2023-44228"),
        ("T1190_Exploit_Public_App", "CVE-2024-21762"),
        ("T1190_Exploit_Public_App", "CVE-2023-22515"),
        ("T1190_Exploit_Public_App", "CVE-2024-1709"),
        ("T1190_Exploit_Public_App", "CVE-2023-34362"),
        ("T1190_Exploit_Public_App", "CVE-2023-20198"),
        ("T1078_Valid_Accounts", "CVE-2024-21412"),
        ("T1133_External_Remote", "CVE-2023-46805"),
        ("T1133_External_Remote", "CVE-2023-20269"),
        ("T1059_Command_Scripting", "CVE-2024-23897"),
        ("T1071_App_Layer_Protocol", "CVE-2023-4966"),
        ("T1105_Ingress_Tool_Transfer", "CVE-2023-46604"),
        ("T1562_Impair_Defenses", "CVE-2024-29847"),
        ("T1021_Remote_Services", "CVE-2023-27997"),
    ],
}

ACTOR_TO_TTP = [
    ("APT28", "T1566_Phishing"), ("APT28", "T1059_Command_Scripting"), ("APT28", "T1078_Valid_Accounts"),
    ("APT29", "T1190_Exploit_Public_App"), ("APT29", "T1053_Scheduled_Task"), ("APT29", "T1078_Valid_Accounts"),
    ("APT41", "T1190_Exploit_Public_App"), ("APT41", "T1055_Process_Injection"), ("APT41", "T1547_Boot_Autostart"),
    ("Lazarus", "T1566_Phishing"), ("Lazarus", "T1059_Command_Scripting"), ("Lazarus", "T1486_Data_Encrypted_Impact"),
    ("APT33", "T1566_Phishing"), ("APT33", "T1190_Exploit_Public_App"),
    ("APT35", "T1566_Phishing"), ("APT35", "T1078_Valid_Accounts"), ("APT35", "T1110_Brute_Force"),
    ("FIN7", "T1566_Phishing"), ("FIN7", "T1059_Command_Scripting"), ("FIN7", "T1021_Remote_Services"),
    ("FIN6", "T1566_Phishing"), ("FIN6", "T1059_Command_Scripting"),
    ("Carbanak", "T1078_Valid_Accounts"), ("Carbanak", "T1059_Command_Scripting"), ("Carbanak", "T1003_Credential_Dumping"),
    ("Turla", "T1190_Exploit_Public_App"), ("Turla", "T1053_Scheduled_Task"),
    ("Sandworm", "T1190_Exploit_Public_App"), ("Sandworm", "T1486_Data_Encrypted_Impact"), ("Sandworm", "T1490_Inhibit_Recovery"),
    ("APT10", "T1190_Exploit_Public_App"), ("APT10", "T1053_Scheduled_Task"), ("APT10", "T1071_App_Layer_Protocol"),
    ("Conti", "T1566_Phishing"), ("Conti", "T1059_Command_Scripting"), ("Conti", "T1486_Data_Encrypted_Impact"),
    ("LockBit", "T1566_Phishing"), ("LockBit", "T1021_Remote_Services"), ("LockBit", "T1486_Data_Encrypted_Impact"),
    ("BlackBasta", "T1566_Phishing"), ("BlackBasta", "T1021_Remote_Services"), ("BlackBasta", "T1486_Data_Encrypted_Impact"),
    ("Volt_Typhoon", "T1078_Valid_Accounts"), ("Volt_Typhoon", "T1082_System_Info"), ("Volt_Typhoon", "T1053_Scheduled_Task"),
    ("Hafnium", "T1190_Exploit_Public_App"), ("Hafnium", "T1055_Process_Injection"),
    ("Clop", "T1190_Exploit_Public_App"), ("Clop", "T1041_Exfiltration_Over_C2"),
    ("Royal", "T1566_Phishing"), ("Royal", "T1021_Remote_Services"), ("Royal", "T1486_Data_Encrypted_Impact"),
    ("MuddyWater", "T1566_Phishing"), ("MuddyWater", "T1078_Valid_Accounts"),
    ("Kimsuky", "T1566_Phishing"), ("Kimsuky", "T1059_Command_Scripting"),
    ("Fancy_Bear", "T1566_Phishing"), ("Fancy_Bear", "T1190_Exploit_Public_App"), ("Fancy_Bear", "T1059_Command_Scripting"),
    ("DarkHotel", "T1566_Phishing"), ("DarkHotel", "T1190_Exploit_Public_App"),
]


def main():
    mem = CognitiveMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building the Threat Intelligence Knowledge Base")
    print("=" * 70)

    for actor in THREAT_ACTORS:
        mem.store(actor["label"], data=actor["data"], modalities={Modality.CAUSAL})

    for cve in CVES:
        mem.store(cve["label"], data=cve["data"], modalities={Modality.SENSORY})

    for mw in MALWARE:
        mem.store(mw["label"], data=mw["data"], modalities={Modality.CONCEPTUAL})

    for ttp in TTPS:
        mem.store(ttp["label"], data=ttp["data"], modalities={Modality.CONCEPTUAL})

    for infra in INFRASTRUCTURE:
        mem.store(infra["label"], data=infra["data"], modalities={Modality.SENSORY})

    for ind in INDUSTRIES:
        mem.store(ind["label"], data=ind["data"], modalities={Modality.ABSTRACT})

    print(f"  Stored {mem.graph.node_count} nodes")

    edge_count = 0
    for rel_label, pairs in RELATIONSHIP_MAP.items():
        for src, tgt in pairs:
            mem.relate(src, tgt, label=rel_label)
            edge_count += 1

    for src, tgt in ACTOR_TO_TTP:
        mem.relate(src, tgt, label="uses_tactic")
        edge_count += 1

    print(f"  Created {mem.graph.edge_count} edges ({edge_count} requested)")
    print()

    print("=" * 70)
    print("SECTION 2: Recall and Neighborhood Traversal")
    print("=" * 70)

    lazarus_neighborhood = mem.recall("Lazarus", max_depth=2, max_nodes=30)
    print(f"  Lazarus neighborhood (depth=2): {len(lazarus_neighborhood)} nodes")
    neighbors_by_type: dict[str, list[str]] = {}
    for node in lazarus_neighborhood:
        if isinstance(node.data, dict):
            cat = node.data.get("type", node.data.get("sector", node.data.get("origin", "other")))
        else:
            cat = "other"
        neighbors_by_type.setdefault(cat, []).append(node.label)
    for cat, labels in sorted(neighbors_by_type.items()):
        print(f"    {cat}: {', '.join(labels[:6])}{'...' if len(labels) > 6 else ''}")

    gov_reachable = mem.query("GOV", strategy="bfs", max_depth=3, max_nodes=50)
    print(f"\n  BFS from GOV sector (depth=3): {len(gov_reachable)} nodes")
    gov_labels = [n.label for n in gov_reachable]
    actor_set = {a["label"] for a in THREAT_ACTORS}
    gov_actors = [l for l in gov_labels if l in actor_set]
    print(f"    Threat actors targeting government: {gov_actors}")
    print()

    print("=" * 70)
    print("SECTION 3: Pattern Matching for Attack Chains")
    print("=" * 70)

    exploits_edges = mem.pattern_match(edge_label="exploits")
    print(f"  Total 'exploits' edges: {len(exploits_edges)}")

    uses_edges = mem.pattern_match(edge_label="uses")
    print(f"  Total 'uses' (malware) edges: {len(uses_edges)}")

    targets_edges = mem.pattern_match(edge_label="targets")
    print(f"  Total 'targets' edges: {len(targets_edges)}")

    cve_to_industry: dict[str, set[str]] = {}
    for exp in exploits_edges:
        actor_lbl = exp["source_labels"][0] if exp["source_labels"] else ""
        for tgt in targets_edges:
            if actor_lbl and actor_lbl in tgt["source_labels"]:
                ind_lbl = tgt["target_labels"][0] if tgt["target_labels"] else ""
                cve_lbl = exp["target_labels"][0] if exp["target_labels"] else ""
                if cve_lbl and ind_lbl:
                    cve_to_industry.setdefault(cve_lbl, set()).add(ind_lbl)

    print(f"\n  CVEs enabling attacks on the most sectors:")
    sorted_cves = sorted(cve_to_industry.items(), key=lambda x: len(x[1]), reverse=True)
    for cve, sectors in sorted_cves[:5]:
        print(f"    {cve}: {len(sectors)} sectors ({', '.join(sorted(sectors))})")
    print()

    print("=" * 70)
    print("SECTION 4: Top 5 Most Connected CVEs (Highest Degree)")
    print("=" * 70)

    centrality = mem.degree_centrality_labels()
    cve_set = {c["label"] for c in CVES}
    cve_centrality = {k: v for k, v in centrality.items() if k in cve_set}
    top_cves = sorted(cve_centrality.items(), key=lambda x: x[1], reverse=True)[:5]

    print("  Rank  CVE                  Centality  CVSS   Product")
    print("  " + "-" * 60)
    for rank, (cve_label, score) in enumerate(top_cves, 1):
        node = None
        for n in mem.graph.nodes:
            if n.label == cve_label:
                node = n
                break
        cvss = node.data["cvss"] if node and isinstance(node.data, dict) else "?"
        product = node.data["product"] if node and isinstance(node.data, dict) else "?"
        print(f"  {rank}.    {cve_label:22s} {score:.4f}   {cvss:<5}  {product}")
    print()

    print("=" * 70)
    print("SECTION 5: Subgraph Extraction - APT28 Full Profile")
    print("=" * 70)

    apt28_exploits = mem.pattern_match(source_label="APT28", edge_label="exploits")
    apt28_uses = mem.pattern_match(source_label="APT28", edge_label="uses")
    apt28_targets = mem.pattern_match(source_label="APT28", edge_label="targets")
    apt28_ttps = mem.pattern_match(source_label="APT28", edge_label="uses_tactic")

    apt28_labels = {"APT28"}
    for edges in [apt28_exploits, apt28_uses, apt28_targets, apt28_ttps]:
        for e in edges:
            apt28_labels.update(e["source_labels"])
            apt28_labels.update(e["target_labels"])

    sg = mem.subgraph(apt28_labels)
    print(f"  APT28 profile subgraph: {sg['node_count']} nodes, {sg['edge_count']} edges")
    print(f"    CVEs exploited:")
    for e in apt28_exploits:
        tgt_lbl = e["target_labels"][0] if e["target_labels"] else "?"
        print(f"      {tgt_lbl}")
    print(f"    Malware used:")
    for e in apt28_uses:
        tgt_lbl = e["target_labels"][0] if e["target_labels"] else "?"
        print(f"      {tgt_lbl}")
    print(f"    Sectors targeted:")
    for e in apt28_targets:
        tgt_lbl = e["target_labels"][0] if e["target_labels"] else "?"
        print(f"      {tgt_lbl}")
    print(f"    TTPs:")
    for e in apt28_ttps:
        tgt_lbl = e["target_labels"][0] if e["target_labels"] else "?"
        print(f"      {tgt_lbl}")
    print()

    print("=" * 70)
    print("SECTION 6: Attack Paths - Lazarus to Financial Sector")
    print("=" * 70)

    paths = mem.find_paths_labels("Lazarus", "FIN", max_depth=4, max_paths=10)
    if paths:
        print(f"  Found {len(paths)} path(s) from Lazarus to Financial sector:")
        for i, path in enumerate(paths, 1):
            print(f"    Path {i}: {' -> '.join(path)}")
    else:
        print("  No direct paths found from Lazarus to Financial sector")

    paths2 = mem.find_paths_labels("Volt_Typhoon", "ENERGY", max_depth=4, max_paths=10)
    if paths2:
        print(f"\n  Found {len(paths2)} path(s) from Volt Typhoon to Energy sector:")
        for i, path in enumerate(paths2, 1):
            print(f"    Path {i}: {' -> '.join(path)}")
    else:
        print("\n  No direct paths found from Volt Typhoon to Energy sector")
    print()

    print("=" * 70)
    print("SECTION 7: Isolated Indicators Needing Enrichment")
    print("=" * 70)

    all_labels = {n.label for n in mem.graph.nodes}
    connected_labels: set[str] = set()
    for edge in mem.graph.labeled_edges:
        connected_labels.update(edge["source_labels"])
        connected_labels.update(edge["target_labels"])

    isolated = all_labels - connected_labels
    if isolated:
        print(f"  {len(isolated)} nodes with NO edges (need enrichment):")
        for label in sorted(isolated):
            node = None
            for n in mem.graph.nodes:
                if n.label == label:
                    node = n
                    break
            if node and isinstance(node.data, dict):
                detail = node.data.get("tactic", node.data.get("type", node.data.get("sector", "")))
                print(f"    {label} [{detail}]")
            else:
                print(f"    {label}")
    else:
        print("  All nodes have at least one edge.")
    print()

    print("=" * 70)
    print("SECTION 8: Connected Components - Threat Ecosystems")
    print("=" * 70)

    components = mem.connected_components_labels()
    components_sorted = sorted(components, key=len, reverse=True)
    print(f"  Total connected components: {len(components_sorted)}")
    for i, comp in enumerate(components_sorted, 1):
        actors_in_comp = comp & {a["label"] for a in THREAT_ACTORS}
        malwares_in_comp = comp & {m["label"] for m in MALWARE}
        cves_in_comp = comp & {c["label"] for c in CVES}
        infras_in_comp = comp & {inf["label"] for inf in INFRASTRUCTURE}
        industries_in_comp = comp & {ind["label"] for ind in INDUSTRIES}
        ttps_in_comp = comp & {t["label"] for t in TTPS}

        print(f"\n  Component {i} ({len(comp)} nodes):")
        if actors_in_comp:
            print(f"    Threat actors ({len(actors_in_comp)}): {', '.join(sorted(actors_in_comp)[:8])}{'...' if len(actors_in_comp) > 8 else ''}")
        if cves_in_comp:
            print(f"    CVEs ({len(cves_in_comp)}): {', '.join(sorted(cves_in_comp)[:6])}{'...' if len(cves_in_comp) > 6 else ''}")
        if malwares_in_comp:
            print(f"    Malware ({len(malwares_in_comp)}): {', '.join(sorted(malwares_in_comp)[:6])}{'...' if len(malwares_in_comp) > 6 else ''}")
        if infras_in_comp:
            print(f"    Infrastructure ({len(infras_in_comp)}): {', '.join(sorted(infras_in_comp)[:4])}{'...' if len(infras_in_comp) > 4 else ''}")
        if industries_in_comp:
            print(f"    Target sectors ({len(industries_in_comp)}): {', '.join(sorted(industries_in_comp))}")
        if ttps_in_comp:
            print(f"    TTPs ({len(ttps_in_comp)}): {', '.join(sorted(ttps_in_comp)[:5])}{'...' if len(ttps_in_comp) > 5 else ''}")

        if i >= 5:
            remaining = len(components_sorted) - 5
            if remaining > 0:
                print(f"\n  ... and {remaining} smaller components omitted")
            break
    print()

    print("=" * 70)
    print("SECTION 9: Modality-Filtered Traversal")
    print("=" * 70)

    causal_nodes = mem.query("CVE-2023-44228", modality=Modality.CAUSAL, max_depth=2, max_nodes=20)
    print(f"  CAUSAL modality from Log4j CVE: {len(causal_nodes)} nodes")
    for n in causal_nodes:
        origin = n.data.get("origin", "") if isinstance(n.data, dict) else ""
        suffix = f" (origin: {origin})" if origin else ""
        print(f"    {n.label}{suffix}")

    sensory_nodes = mem.query("CVE-2023-44228", modality=Modality.SENSORY, max_depth=2, max_nodes=20)
    print(f"\n  SENSORY modality from Log4j CVE: {len(sensory_nodes)} nodes")
    for n in sensory_nodes:
        cvss = n.data.get("cvss", n.data.get("type", "")) if isinstance(n.data, dict) else ""
        suffix = f" (cvss/type: {cvss})" if cvss else ""
        print(f"    {n.label}{suffix}")

    conceptual_nodes = mem.query("CVE-2023-44228", modality=Modality.CONCEPTUAL, max_depth=2, max_nodes=20)
    print(f"\n  CONCEPTUAL modality from Log4j CVE: {len(conceptual_nodes)} nodes")
    for n in conceptual_nodes:
        mw_type = n.data.get("type", n.data.get("tactic", "")) if isinstance(n.data, dict) else ""
        suffix = f" ({mw_type})" if mw_type else ""
        print(f"    {n.label}{suffix}")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Nodes:                {stats['nodes']}")
    print(f"  Edges:                {stats['edges']}")
    print(f"  Event log entries:    {stats['log_size']}")
    print(f"  Connected components: {stats['components']}")
    print(f"  Has cycles:           {stats['cycles']}")
    print(f"  Threat actors:        {len(THREAT_ACTORS)}")
    print(f"  CVEs:                 {len(CVES)}")
    print(f"  Malware families:     {len(MALWARE)}")
    print(f"  TTPs:                 {len(TTPS)}")
    print(f"  Infrastructure:       {len(INFRASTRUCTURE)}")
    print(f"  Target industries:    {len(INDUSTRIES)}")
    print()


if __name__ == "__main__":
    main()
