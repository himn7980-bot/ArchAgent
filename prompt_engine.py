class PromptEngine:
    @staticmethod
    def get_style_details(style: str) -> str:
        styles = {
            "modern": """
modern architectural style, clean geometric lines, refined minimal detailing,
premium glass, concrete, wood, and metal materials,
high-end modern composition
""".strip(),

            "classic": """
neoclassical architectural style, elegant symmetry, refined arches,
classical proportions, white travertine or limestone surfaces,
luxury classical detailing
""".strip(),

            "minimal": """
ultra-minimal architectural style, restrained palette, seamless surfaces,
clean forms, high-end finishing, subtle refined details
""".strip(),

            "luxury": """
high-end luxury architectural design, premium layered materials,
bronze accents, elegant lighting, sophisticated detailing,
exclusive upscale visual identity
""".strip(),

            "arabic": """
contemporary Middle Eastern architectural style, elegant arches,
regional proportions, warm stone materials,
luxury Arabic villa aesthetic, mashrabiya-inspired refinement
""".strip(),
        }
        return styles.get(style, "professional architectural design")

    @staticmethod
    def get_space_details(space_type: str) -> str:
        spaces = {
            "kitchen": """
professional kitchen interior design visualization,
custom cabinetry, premium countertop, integrated appliances,
balanced interior composition, clean functional layout
""".strip(),

            "bathroom": """
high-end bathroom interior design visualization,
premium sanitary fixtures, elegant tile and stone finishes,
refined lighting, spa-like atmosphere
""".strip(),

            "living_room": """
luxury living room interior architecture,
refined furniture composition, layered lighting,
premium wall and floor finishes, elegant ambiance
""".strip(),

            "interior": """
professional interior architectural visualization,
refined spatial composition, premium materials,
balanced lighting and realistic interior atmosphere
""".strip(),

            "unfinished": """
unfinished building redesign, transform raw concrete structure
into a completed premium architectural exterior,
preserve the main structure and proportions,
make the building appear fully finished and realistic
""".strip(),

            "exterior": """
professional exterior architectural facade redesign,
realistic urban context, refined facade composition,
premium materials, windows, balconies, and lighting
""".strip(),
        }
        return spaces.get(space_type, "professional architectural visualization")

    @staticmethod
    def get_environment_details(time_of_day: str, weather: str, space_type: str) -> str:
        env_parts = []

        is_interior = space_type in {"kitchen", "bathroom", "living_room", "interior"}

        if time_of_day == "day":
            if is_interior:
                env_parts.append(
                    "bright natural daylight entering the interior, soft balanced exposure, realistic daylight mood"
                )
            else:
                env_parts.append(
                    "bright natural daylight, clean sky, realistic sun shadows, crisp visibility"
                )

        elif time_of_day == "night":
            if is_interior:
                env_parts.append(
                    "interior night mood, warm artificial lighting, low daylight contribution, cinematic contrast, cozy atmosphere"
                )
            else:
                env_parts.append(
                    "night exterior scene, architectural facade lighting, warm interior window glow, deep blue night sky, cinematic night render"
                )

        elif time_of_day == "sunset":
            if is_interior:
                env_parts.append(
                    "warm sunset glow entering through windows, golden ambient interior light, soft warm shadows, cinematic evening atmosphere"
                )
            else:
                env_parts.append(
                    "golden hour exterior lighting, warm sunset glow, orange and purple sky tones, long dramatic shadows"
                )

        if weather == "rain":
            if is_interior:
                env_parts.append(
                    "soft overcast daylight through windows, slightly dim natural light, moody interior atmosphere"
                )
            else:
                env_parts.append(
                    "rainy exterior atmosphere, wet reflective ground, overcast sky, water sheen on surfaces, moody weather"
                )

        elif weather == "snow":
            if is_interior:
                env_parts.append(
                    "cold winter light from outside, soft diffused daylight through windows, subtle cozy interior contrast"
                )
            else:
                env_parts.append(
                    "snowy winter exterior scene, snow accumulation on surfaces, cold atmospheric lighting, soft diffused winter mood"
                )

        elif weather == "clear":
            if is_interior:
                env_parts.append(
                    "clean natural daylight quality, clear exterior light entering through windows"
                )
            else:
                env_parts.append(
                    "clear weather, clean visibility, stable natural lighting"
                )

        return ", ".join(env_parts) if env_parts else "balanced realistic architectural lighting"

    @classmethod
    def build_final_prompt(
        cls,
        space_type: str,
        style: str,
        time_of_day: str,
        weather: str,
        user_text: str,
    ) -> str:
        style_text = cls.get_style_details(style)
        space_text = cls.get_space_details(space_type)
        env_text = cls.get_environment_details(time_of_day, weather, space_type)

        is_interior = space_type in {"kitchen", "bathroom", "living_room", "interior"}
        is_exterior = space_type in {"exterior", "unfinished"}

        material_rules = """
Guarantee strong material contrast between walls, frames, glass, cabinetry, countertops, flooring, and decorative surfaces.
Use premium photorealistic textures.
Avoid flat, washed-out, or plastic-looking materials.
""".strip()

        realism_rules = """
Highly realistic architectural visualization.
Professional archviz quality.
Clean geometry, realistic lighting, realistic material response, natural shadows.
""".strip()

        negative_rules = """
No text, no logo, no watermark, no distorted lines, no warped windows, no broken geometry,
no duplicated facade elements, no cartoon look, no plastic materials, no unrealistic artifacts.
""".strip()

        transformation_rules = """
The redesign must be clearly visible.
Apply a strong and obvious transformation according to the user's request.
Do not keep the original color palette or original materials if the user asked for change.
Make the requested new style, colors, lighting, and mood clearly noticeable in the final image.
""".strip()

        if is_interior:
            preserve_rules = """
Preserve only the room layout, proportions, and camera angle.
It is allowed to visibly change cabinetry, finishes, walls, flooring, countertops, lighting, and color palette.
""".strip()
        elif is_exterior:
            preserve_rules = """
Preserve the main building massing, facade proportions, and camera perspective.
It is allowed to visibly change facade materials, windows, balconies, lighting, and atmosphere.
""".strip()
        else:
            preserve_rules = """
Preserve the main composition and camera perspective unless structural change is explicitly requested.
""".strip()

        prompt = f"""
Task:
Create a professional architectural visualization based on the source image.

Scene Type:
{space_text}

Style Direction:
{style_text}

Lighting and Environment:
{env_text}

User Request:
{user_text}

Transformation Rules:
{transformation_rules}

Material Rules:
{material_rules}

Preservation Rules:
{preserve_rules}

Quality Target:
{realism_rules}

Negative Constraints:
{negative_rules}
"""
        return prompt.strip()
