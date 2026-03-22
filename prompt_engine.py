
class PromptEngine:
    @staticmethod
    def get_style_details(style: str) -> str:
        styles = {
            "modern": "modern architectural style, clean geometric lines, refined minimal detailing, premium glass, concrete, and metal materials",
            "classic": "neoclassical architectural style, white travertine or limestone cladding, elegant arches, columns, symmetrical facade composition, refined classical detailing",
            "minimal": "ultra-minimalist architectural style, seamless surfaces, restrained material palette, pure forms, refined high-end finishing",
            "luxury": "high-end luxury architectural design, premium materials, layered facade composition, bronze accents, dramatic lighting, sophisticated detailing",
            "arabic": "contemporary Middle Eastern architectural style, elegant arches, mashrabiya-inspired details, warm stone materials, luxury villa facade aesthetic",
        }
        return styles.get(style, "professional architectural design")

    @staticmethod
    def get_space_details(space_type: str) -> str:
        spaces = {
            "exterior": "architectural exterior facade design, realistic street-facing composition, facade materials, window proportions, balcony detailing",
            "unfinished": "unfinished building facade redesign, transform raw concrete structure into a completed premium architectural exterior, preserve main structure and proportions",
            "interior": "interior architectural visualization, refined spatial composition, premium finishes, realistic material transitions",
            "kitchen": "luxury kitchen interior design, custom cabinetry, premium countertop, integrated appliances, balanced composition",
            "bathroom": "high-end bathroom interior design, elegant sanitary fixtures, refined stone and tile finishes, premium lighting",
            "living_room": "luxury living room interior architecture, refined furniture layout, layered lighting, premium wall and floor finishes",
        }
        return spaces.get(space_type, "professional architectural visualization")

    @staticmethod
    def get_environment_details(time_of_day: str, weather: str, space_type: str) -> str:
        env_parts = []

        if time_of_day == "day":
            env_parts.append("bright natural daylight, realistic sun shadows, balanced exposure")
        elif time_of_day == "night":
            env_parts.append("night scene, architectural lighting, warm interior glow, cinematic contrast")
        elif time_of_day == "sunset":
            env_parts.append("golden hour lighting, warm sunset tones, soft dramatic shadows")

        if space_type in {"exterior", "unfinished"}:
            if weather == "rain":
                env_parts.append("rainy atmosphere, wet reflective ground, overcast sky, realistic moisture effects")
            elif weather == "snow":
                env_parts.append("winter snowy scene, snow accumulation on surfaces, cold atmospheric lighting")
            elif weather == "clear":
                env_parts.append("clear weather, clean visibility")

        return ", ".join(env_parts) if env_parts else "balanced realistic lighting"

    @classmethod
    def build_final_prompt(cls, space_type: str, style: str, time_of_day: str, weather: str, user_text: str) -> str:
        style_desc = cls.get_style_details(style)
        space_desc = cls.get_space_details(space_type)
        env_desc = cls.get_environment_details(time_of_day, weather, space_type)

        material_rules = (
            "Guarantee strong material contrast between walls, frames, glass, flooring, and decorative surfaces. "
            "Use premium photorealistic textures and avoid flat or plastic-looking materials."
        )

        negative_rules = (
            "No text, no logos, no watermark, no distorted geometry, no warped windows, "
            "no duplicated facade elements, no cartoon look, no plastic materials."
        )

        prompt = f"""
Task: Create a professional architectural visualization.

Scene Type:
{space_desc}

Style Direction:
{style_desc}

Environment:
{env_desc}

User Request:
{user_text}

Technical Requirements:
- {material_rules}
- Preserve the main building massing and original camera perspective unless the request explicitly requires structural change.
- Highly detailed architectural rendering.
- Realistic lighting, realistic materials, clean geometry.
- {negative_rules}
"""
        return prompt.strip()
