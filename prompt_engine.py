class PromptEngine:
    @staticmethod
    def get_style_details(style: str) -> str:
        styles = {
            "modern": "modern architectural style, industrial-chic elements, floor-to-ceiling glazing, seamless concrete, natural oak wood slats, black steel accents, minimalist high-end finish",
            "classic": "neoclassical grand architecture, symmetrical limestone facade, ornate cornices, ionic columns, double-height arched windows, white travertine surfaces, timeless luxury",
            "minimal": "pure minimalist aesthetic, monolithic forms, micro-cement finishes, hidden lighting, zero-frame joinery, muted tonal palette, architectural silence",
            "luxury": "ultra-luxury premium design, book-matched marble slabs, polished brass and bronze details, layered architectural volumes, sophisticated cove lighting, penthouse aesthetic",
            "arabic": "contemporary khaleeji architecture, modern mashrabiya screens, elegant pointed arches, sand-toned textured stone, desert-modern villa aesthetic, luxury majlis refinement"
        }
        return styles.get(style, "high-quality architectural design")

    @staticmethod
    def get_space_details(space_type: str) -> str:
        spaces = {
            "kitchen": "high-end kitchen interior, bespoke cabinetry, waterfall marble island, designer appliances, integrated lighting, professional gourmet kitchen atmosphere",
            "bathroom": "luxury spa-like bathroom, walk-in rain shower, premium stone tiling, freestanding tub, floating vanity, indirect ambient lighting",
            "living_room": "sophisticated living area, architectural feature wall, designer furniture composition, premium flooring, open-concept luxury living",
            "interior": "professional interior architectural visualization, curated decor, premium material palette, realistic depth and spatial awareness",
            "unfinished": "fully finished luxury architectural masterpiece, premium cladding, brand new windows, beautiful landscaping, pristine condition",
            "exterior": "architectural facade redesign, premium exterior cladding, modern window systems, balcony integration, professional landscape context"
        }
        return spaces.get(space_type, "architectural visualization")

    @staticmethod
    def get_environment_details(time_of_day: str, weather: str, space_type: str) -> str:
        is_interior = space_type in {"kitchen", "bathroom", "living_room", "interior"}
        env_parts = []

        if time_of_day == "day":
            env_parts.append("bright direct sunlight, 5500K color temperature, realistic sun-casting shadows" if not is_interior else "bright diffused daylight through windows, natural bounce lighting")
        elif time_of_day == "night":
            env_parts.append("cinematic night photography, glowing interior lights, warm architectural uplighting, dark blue hour sky")
        elif time_of_day == "sunset":
            env_parts.append("golden hour lighting, 3000K warm glow, long dramatic orange-tinted shadows, vivid sunset sky")

        if weather == "rain":
            env_parts.append("wet reflective surfaces, PBR puddle reflections, moody overcast sky, raindrop textures")
        elif weather == "snow":
            env_parts.append("heavy snow accumulation, frosty textures, cold 6500K atmosphere, white-covered landscape")
        elif weather == "clear":
            env_parts.append("pristine visibility, clear atmosphere, stable global illumination")

        return ", ".join(env_parts) if env_parts else "balanced global illumination"

    @classmethod
    def build_final_prompt(cls, space_type: str, style: str, time_of_day: str, weather: str, user_text: str) -> dict:
        style_text = cls.get_style_details(style)
        space_text = cls.get_space_details(space_type)
        env_text = cls.get_environment_details(time_of_day, weather, space_type)

        # 👈 استفاده از وزن‌دهی قوی (1.5) برای مجبور کردن هوش مصنوعی به تغییر رنگ
        user_focus = f"({user_text}:1.5), strongly colored {user_text}, " if user_text else ""

        positive_prompt = f"{user_focus}{space_text}, {style_text}, {env_text}, Hyper-realistic photogrammetry-grade textures, cinematic lighting"
        
        # 👈 پرامپت منفی بسیار سخت‌گیرانه تا رنگ سفید عکس اصلی را رها کند
        negative_prompt = "white cabinets, pale colors, original materials, cartoon, drawing, 3d render style, low quality, plastic textures, blurry, flat lighting"

        return {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt
        }
