def suggest_materials(space_type: str, style: str) -> list[str]:
    if space_type == "interior":
        return {
            "modern": ["Microcement", "Oak veneer", "Linear LED", "Porcelain flooring"],
            "classic": ["Walnut wood", "Decorative moldings", "Warm wall lights", "Natural stone"],
            "minimal": ["Matte paint", "Hidden LED", "Light oak", "Large tiles"],
            "luxury": ["Bookmatched marble", "Brushed brass", "Premium walnut", "Layered lighting"],
            "arabic": ["Decorative panels", "Bronze accents", "Warm stone finish", "Ambient lighting"],
        }.get(style, ["Wood finish", "Lighting", "Flooring", "Wall finish"])

    if space_type == "exterior":
        return {
            "modern": ["Aluminum frames", "Glass balustrades", "Facade panels", "Architectural lighting"],
            "classic": ["Travertine stone", "Decorative plaster", "Bronze lighting", "Stone base cladding"],
            "minimal": ["Smooth render", "Slim black frames", "Hidden lighting", "Large facade panels"],
            "luxury": ["Premium travertine", "Bronze details", "Facade porcelain", "Layered facade lighting"],
            "arabic": ["Beige natural stone", "Decorative arches", "Warm facade lighting", "Ornamental metal"],
        }.get(style, ["Stone finish", "Facade lighting", "Aluminum", "Cladding"])

    if space_type == "unfinished":
        return ["Plaster finish", "Flooring system", "Lighting fixtures", "Joinery"]
    return ["Paint", "Flooring", "Wall finish", "Lighting"]