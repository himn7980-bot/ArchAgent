def get_store_suggestions(space_type: str, style: str) -> list[str]:
    if space_type == "interior":
        return ["Furniture stores", "Lighting stores", "Wall finish suppliers", "Flooring stores"]
    if space_type == "exterior":
        return ["Facade stone suppliers", "Architectural lighting stores", "Aluminum & glass suppliers", "Exterior cladding stores"]
    if space_type == "unfinished":
        return ["Construction material stores", "Finishing suppliers", "Lighting stores", "Flooring suppliers"]
    return ["Renovation material stores", "Paint suppliers", "Lighting stores", "General finishing suppliers"]