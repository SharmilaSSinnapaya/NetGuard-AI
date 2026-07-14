"""Attack label taxonomy and NSL-KDD column definitions."""

from __future__ import annotations

# 41 features + attack label + difficulty score
NSL_KDD_COLUMNS: list[str] = [
    "duration",
    "protocol_type",
    "service",
    "flag",
    "src_bytes",
    "dst_bytes",
    "land",
    "wrong_fragment",
    "urgent",
    "hot",
    "num_failed_logins",
    "logged_in",
    "num_compromised",
    "root_shell",
    "su_attempted",
    "num_root",
    "num_file_creations",
    "num_shells",
    "num_access_files",
    "num_outbound_cmds",
    "is_host_login",
    "is_guest_login",
    "count",
    "srv_count",
    "serror_rate",
    "srv_serror_rate",
    "rerror_rate",
    "srv_rerror_rate",
    "same_srv_rate",
    "diff_srv_rate",
    "srv_diff_host_rate",
    "dst_host_count",
    "dst_host_srv_count",
    "dst_host_same_srv_rate",
    "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate",
    "dst_host_srv_serror_rate",
    "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate",
    "label",
    "difficulty",
]

NSL_KDD_COLUMN_COUNT = len(NSL_KDD_COLUMNS)

FEATURE_COLUMNS: list[str] = NSL_KDD_COLUMNS[:-2]  # exclude label + difficulty

ATTACK_CATEGORIES: tuple[str, ...] = ("normal", "dos", "probe", "r2l", "u2r")

# Fine-grained NSL-KDD labels → coarse attack category
# Sources: NSL-KDD / KDD Cup'99 taxonomy commonly used in IDS literature
_DOS = {
    "apache2",
    "back",
    "land",
    "neptune",
    "mailbomb",
    "pod",
    "processtable",
    "smurf",
    "teardrop",
    "udpstorm",
    "worm",
}
_PROBE = {
    "ipsweep",
    "mscan",
    "nmap",
    "portsweep",
    "saint",
    "satan",
}
_R2L = {
    "ftp_write",
    "guess_passwd",
    "httptunnel",
    "imap",
    "multihop",
    "named",
    "phf",
    "sendmail",
    "snmpgetattack",
    "snmpguess",
    "spy",
    "warezclient",
    "warezmaster",
    "xlock",
    "xsnoop",
}
_U2R = {
    "buffer_overflow",
    "loadmodule",
    "perl",
    "ps",
    "rootkit",
    "sqlattack",
    "xterm",
}

ATTACK_TO_CATEGORY: dict[str, str] = {
    "normal": "normal",
    **{name: "dos" for name in _DOS},
    **{name: "probe" for name in _PROBE},
    **{name: "r2l" for name in _R2L},
    **{name: "u2r" for name in _U2R},
}


def normalize_label(raw: str) -> str:
    """Normalize raw attack labels (strip, lowercase, drop trailing '.')."""
    return str(raw).strip().lower().rstrip(".")


def label_to_category(raw_label: str) -> str:
    """Map a fine-grained attack label to a coarse category."""
    key = normalize_label(raw_label)
    if key not in ATTACK_TO_CATEGORY:
        raise KeyError(f"Unknown NSL-KDD label: {raw_label!r}")
    return ATTACK_TO_CATEGORY[key]
