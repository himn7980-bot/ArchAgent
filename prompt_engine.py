class PromptEngine:
    @staticmethod
    def get_style_details(style: str) -> str:
        styles = {
            "modern": "ultra-modern architectural style, sleek geometric forms, floor-to-ceiling glazing, seamless concrete, natural oak wood slats, black steel accents, minimalist high-end finish",
            "classic": "neoclassical grand architecture, symmetrical limestone facade, ornate cornices, ionic columns, double-height arched windows, white travertine surfaces, timeless luxury",
            "minimal": "pure minimalist aesthetic, monolithic forms, micro-cement finishes, hidden lighting, zero-frame joinery, muted tonal palette, architectural silence, wabi-sabi influence",
            "luxury": "ultra-luxury premium design, book-matched marble slabs, polished brass and bronze details, layered architectural volumes, sophisticated cove lighting, high-end penthouse aesthetic",
            "arabic": "contemporary khaleeji architecture, modern mashrabiya screens, elegant pointed arches, sand-toned textured stone, desert-modern luxury villa aesthetic, premium geometric Islamic patterns"
        }
        return styles.get(style, "high-quality architectural design, award-winning architecture")

    @staticmethod
    def get_space_details(space_type: str) -> str:
        spaces = {
            "kitchen": "high-end modern kitchen interior, bespoke cabinetry, waterfall marble island, designer appliances, integrated LED lighting, professional gourmet kitchen atmosphere",
            "bathroom": "luxury spa-like bathroom interior, walk-in rain shower, premium large-format stone tiling, freestanding tub, floating vanity, indirect ambient lighting",
            "living_room": "sophisticated living area interior, architectural feature wall, designer furniture composition, premium flooring, open-concept luxury living space",
            "interior": "professional interior architectural visualization, curated high-end decor, premium material palette, realistic depth and spatial awareness, 8k resolution",
            "unfinished": "fully finished luxury architectural masterpiece, premium cladding, brand new window systems, beautiful professional landscaping, pristine condition, highly detailed",
            "exterior": "architectural facade redesign, premium exterior cladding, modern window systems, architectural context, professional landscape design, photorealistic building exterior"
        }
        return spaces.get(space_type, "architectural visualization, V-Ray render, Octane render")

    @staticmethod
    def get_environment_details(time_of_day: str, weather: str, space_type: str) -> dict:
        is_interior = space_type in {"kitchen", "bathroom", "living_room", "interior"}
        
        env_pos = []
        env_neg = []

        # --- Time of Day Handling ---
        if time_of_day == "day":
            if is_interior:
                env_pos.append("(bright diffused daylight through windows:1.4), (natural bounce lighting:1.3), well-lit interior")
            else:
                env_pos.append("(bright direct sunlight:1.4), (clear blue sky:1.3), 5500K color temperature, realistic crisp sun-casting shadows")
            env_neg.append("(night:1.5), (darkness:1.5), artificial glowing lights, dark sky")
            
        elif time_of_day == "night":
            env_pos.append("(nighttime architectural photography:1.5), (deep dark night sky:1.5), (glowing interior lights:1.5), (dramatic artificial architectural uplighting:1.4), cinematic high-contrast lighting")
            env_neg.append("(daylight:1.5), (sunlight:1.5), (bright sky:1.5), overexposed, sun shadows")
            
        elif time_of_day == "sunset":
            env_pos.append("(golden hour lighting:1.5), (vivid sunset sky:1.4), 3000K warm glow, (long dramatic orange-tinted shadows:1.3), twilight architecture")
            env_neg.append("(midday sun:1.4), flat lighting, clear blue sky, white light")

        # --- Weather Handling ---
        if weather == "rain":
            env_pos.append("(heavy rain:1.5), (wet reflective surfaces:1.5), (PBR puddle reflections:1.4), moody overcast sky, volumetric fog, damp architectural materials")
            env_neg.append("(dry surfaces:1.5), sunny, bright blue sky, arid")
            
        elif weather == "snow":
            env_pos.append("(heavy snow accumulation:1.5), (frosty textures:1.4), cold 6500K atmosphere, (white-covered landscape:1.5), winter wonderland architecture, gentle snowfall")
            env_neg.append("(summer:1.5), green grass, dry surfaces, tropical leaves")
            
        elif weather == "clear":
            env_pos.append("(pristine visibility:1.3), clear atmosphere, stable global illumination, HDRI lighting")
            env_neg.append("fog, rain, snow, overcast, blurry atmosphere")

        return {
            "positive": ", ".join(env_pos) if env_pos else "balanced global illumination",
            "negative": ", ".join(env_neg) if env_neg else ""
        }

    @classmethod
    def build_final_prompt(cls, space_type: str, style: str, time_of_day: str, weather: str, user_text: str) -> dict:
        style_text = cls.get_style_details(style)
        space_text = cls.get_space_details(space_type)
        env_data = cls.get_environment_details(time_of_day, weather, space_type)

        # وزن دادن به درخواست کاربر بدون اضافه کردن کلمات اضافی مثل strongly colored که برای متن‌هایی مثل شهر کربلا خرابکاری می‌کرد
        user_focus = f"({user_text}:1.5), " if user_text else ""

        # ساختاربندی اصولی پرامپت: اولویت با درخواست کاربر + زمان/آب‌وهوا + نوع فضا + استایل + کلمات کلیدی کیفیت
        positive_prompt = (
            f"{user_focus}"
            f"{env_data['positive']}, "
            f"{space_text}, "
            f"{style_text}, "
            f"Hyper-realistic photogrammetry-grade textures, cinematic lighting, 8k resolution, Unreal Engine 5 render, architectural masterpiece"
        )
        
        # ترکیب پرامپت منفی پایه برای معماری با پرامپت‌های منفی مربوط به زمان و آب‌وهوا
        base_negative = "cartoon, illustration, drawing, 3d render style, low quality, plastic textures, blurry, flat lighting, distorted perspective, bad geometry, mutated structure, watermark, text"
        
        final_negative = base_negative
        if env_data['negative']:
            final_negative = f"{env_data['negative']}, {base_negative}"

        return {
            "prompt": positive_prompt.strip(", "),
            "negative_prompt": final_negative.strip(", ")
        }
