EGX_TICKERS = {
    "COMI": "Commercial International Bank",
    "HRHO": "EFG Holding",
    "ABUK": "Abu Qir Fertilizers",
    "TMGH": "Talaat Moustafa Group",
    "SWDY": "Elsewedy Electric",
    "EAST": "Eastern Company",
    "ETEL": "Telecom Egypt",
    "AMOC": "Alexandria Fertilizers & Chemicals",
    "EFIH": "EFG Finance Holding",
    "ORHD": "Orascom Development",
    "ALCN": "Al Ahly Capital Holding",
}
DEFAULT_WATCHLIST = ["COMI", "HRHO", "ABUK", "TMGH", "SWDY", "EAST", "ETEL", "AMOC"]


def yahoo_symbol(symbol: str) -> str:
    return f"{symbol}.CA"


def tv_symbol(symbol: str) -> str:
    return f"EGX:{symbol}"
