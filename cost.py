def estimate_cost(space_type: str, style: str) -> str:
    table = {
        "interior": {
            "modern": "$1,500 - $4,500",
            "classic": "$2,000 - $6,000",
            "minimal": "$1,200 - $3,500",
            "luxury": "$4,000 - $12,000",
            "arabic": "$3,000 - $8,000",
        },
        "exterior": {
            "modern": "$6,000 - $18,000",
            "classic": "$8,000 - $25,000",
            "minimal": "$5,000 - $15,000",
            "luxury": "$12,000 - $35,000",
            "arabic": "$10,000 - $28,000",
        },
        "unfinished": {"default": "$5,000 - $20,000"},
        "renovation": {"default": "$3,000 - $15,000"},
    }

    if space_type in {"unfinished", "renovation"}:
        return table[space_type]["default"]
    return table.get(space_type, {}).get(style, "$2,000 - $10,000")