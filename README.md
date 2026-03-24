# 🏛 ArchAgent — Your AI Architect on TON

**ArchAgent** is an intelligent, Telegram-native AI assistant designed for architecture, interior design, and real estate visualization. It seamlessly combines Large Language Models (LLMs), advanced Image Generation AI, and the **TON Blockchain** into a unified architectural workflow.

Built for the **TON AI Agent Hackathon 2026** (User-Facing AI Agents Track).

---

## 🌟 Vision
Most AI image bots are simple, single-purpose tools. **ArchAgent** is a true **Autonomous Agent**. It understands the user’s complex intent and independently decides whether to provide professional advice, redesign an uploaded image, or generate a completely new architectural concept. 

By integrating a **TON-powered credit economy**, ArchAgent solves the challenge of sustainable monetization for high-compute AI infrastructure, creating a real business use-case on The Open Network.

## ✨ Core Features

* 🤖 **Autonomous AI Architect:** Acts as a professional consultant, discussing materials, suggesting structural improvements, and answering complex design questions.
* 📸 **AI Image Redesign (Image-to-Image):** Upload a photo of a room or building facade. ArchAgent preserves the geometry using Structure-Control AI while completely transforming the style, lighting, and materials.
* 🎨 **Concept Ideation (Text-to-Image):** Generate high-fidelity architectural visualizations from simple natural language prompts (e.g., *"Design a modern desert villa with large glass windows"*).
* 💎 **TON-Powered Economy:** A seamless **Telegram Mini App (TMA)** connected via **TON Connect**. Users purchase "Render Credits" (0.5, 1, or 2 TON) using Tonkeeper or Telegram Wallet.
* 🌍 **Global Localization:** Automatically supports **English, Arabic, Persian, and Russian** based on the user's Telegram settings.
* 👥 **Growth Engine:** Built-in **Referral System** that rewards users with credits for inviting colleagues, ensuring organic viral growth.

---

## 💎 The TON Integration
Meaningful blockchain integration is at the heart of ArchAgent:
- **Direct Monetization:** Real-time TON transactions to fund AI GPU cycles.
- **TMA Experience:** A sleek Mini App store for a frictionless Web3 user experience.
- **On-chain Verification:** Payment status is verified via blockchain hooks to instantly update user balances.

---

## 🛠 Tech Stack

* **Backend:** Python 3 (FastAPI & python-telegram-bot v20+)
* **AI Engines:** OpenAI (Agent Logic), Stability AI (Image Synthesis & ControlNet)
* **Frontend:** HTML5, JavaScript, Telegram WebApp SDK, `@tonconnect/ui`
* **Database:** SQLite3
* **Deployment:** Ready for Render / Heroku / Railway

---

## 🚀 Quick Start (For Developers)

1.  **Clone the repo:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/ArchAgent.git](https://github.com/YOUR_USERNAME/ArchAgent.git)
    cd ArchAgent
    ```
2.  **Install requirements:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set Environment Variables:**
    Create a `.env` file with `BOT_TOKEN`, `OPENAI_API_KEY`, and `STABILITY_API_KEY`.
4.  **Run:**
    ```bash
    python bot.py
    ```

---

## 🎬 Submission Info

* **Bot Link:** [t.me/ArchAgent_hadi_bot](https://t.me/ArchAgent_hadi_bot)
* **Category:** User-Facing AI Agent
* **Hackathon:** TON AI Agent Hackathon 2026

---
*ArchAgent — Bringing decentralized architectural intelligence to The Open Network.*
