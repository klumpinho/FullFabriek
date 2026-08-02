import streamlit as st
import os
import requests
import json
import base64
from openai import OpenAI
import zipfile
import io

# We stellen de pagina in op 'wide' zodat je lekker veel ruimte hebt
st.set_page_config(layout="wide", page_title="De Film Fabriek")

# ==========================================
# NAVIGATIE MENU (SIDEBAR)
# ==========================================
st.sidebar.title("🛠️ The Film Creator")
huidige_pagina = st.sidebar.radio("Kies je tool:", ["✍️ Script Generator", "🎙️ Voice-over Studio", "🎬 Storyboard Fabriek", "📝 Beschrijving Generator", "🖼️ Thumbnail Compositor"])
st.sidebar.markdown("***")
st.sidebar.info("Let the editor use their own OpenAI API key. Voice-overs are securely handled internally.")


# ==========================================
# TOOL 1: DE SCRIPT GENERATOR
# ==========================================
if huidige_pagina == "✍️ Script Generator":
    st.title("YouTube Script Creator PRO")
    st.write("Generate perfect, ElevenLabs-ready scripts based on your bullet points.")
    
    # API key invulveld voor de editor
    user_api_key = st.text_input("Paste your OpenAI API key here:", type="password", key="api_key_script")
    
    # Velden voor de video details
    video_titel = st.text_input("Title of your video:")
    
    # Nieuw: Input voor het gewenste aantal woorden
    target_words = st.number_input("Target Word Count (approximate):", min_value=200, max_value=5000, value=1200, step=100)
    
    default_bullets = "- Point 1: ...\n- Point 2: ...\n- Point 3: ..."
    bullet_points = st.text_area("Your Bullet points (each point on a new line):", value=default_bullets, height=200)
    
    if st.button("🚀 Generate Script"):
        if not user_api_key:
            st.error("Please enter an API key!")
            st.stop()
        if not video_titel or not bullet_points or bullet_points == default_bullets:
            st.warning("Please fill in both the title and your bullet points!")
            st.stop()
            
        client = OpenAI(api_key=user_api_key)
        
        # De prompt is geüpdatet met de target_words variabele
        system_prompt = f"""
        You are writing a script for an animated stickman YouTube channel. The tone MUST be incredibly conversational, raw, and human. Imagine you are explaining deep psychology to a close friend over a cup of coffee. It must sound like real life advice. NOT a formal presentation, NOT a slideshow, and NOT a classroom lecture. 

        Write a highly engaging, IN-DEPTH video script based on the title: '{video_titel}'
        And the following topics:
        {bullet_points}

        CRITICAL LENGTH REQUIREMENT: 
        Your absolute main goal is to write a script that is approximately {target_words} words long. Expand on the psychology, use deep metaphors, and give actionable advice to reach this length naturally without sounding repetitive.

        STRICT TONE & TRANSITION RULES (CRITICAL!):
        - NO SLIDESHOW TRANSITIONS: You are FORBIDDEN from using robotic list phrases like Next up, Moving on to, Next we have, Finally we have, Let us talk about, or Another point is. 
        - Instead, transition naturally like a human telling a story. Use conversational bridges like: But that is just the start. Here is where it gets crazy. Now think about your own life. But here is the real trap.
        - NO YOUTUBE CLICHES in the intro: DO NOT say Today we will explore, Let us dive in, In this video, Welcome to, or Ready. 
        - Talk directly to the viewer as you. Be empathetic but direct.

        OUTRO REQUIREMENT (MANDATORY):
        You MUST end the script with a powerful outro. First, give a brief, motivating conclusion. Then, you MUST ask the viewers one specific, engaging question related to the topic to trigger them to comment. Finally, you MUST explicitly tell them to like the video and subscribe to the channel.

        CRITICAL ELEVENLABS FORMATTING RULES (IF YOU FAIL THIS, THE AUDIO BREAKS):
        - ABSOLUTELY NO QUOTATION MARKS OF ANY KIND. Do NOT use ", ', “, ”, ‘, or ’ anywhere in the script. Ever. Replace them with nothing or rephrase.
        - NO DASHES OR HYPHENS. Do not use - or —. 
        - NO NUMBERS. Spell out ALL numbers (e.g. write seven instead of 7, twenty four instead of 24).
        - NO CONTRACTIONS. Write out words fully: use do not instead of don't, it is instead of it's, you are instead of you're.
        - GRAMMAR FIX FOR CONTRACTIONS: When asking tag questions without contractions, use proper grammar. For example, write does it not? instead of the awkward does not it?. Write is it not? instead of is not it?.
        - NO ACRONYMS. Spell them out with spaces (e.g. write I Q, or U C L A).
        - Keep sentences relatively short, punchy, and conversational, but write a LOT of them.
        """
        
        with st.spinner(f"⏳ Writing a ~{target_words} word script... This may take a while!"):
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a master scriptwriter. You strictly follow formatting rules."},
                        {"role": "user", "content": system_prompt}
                    ],
                    temperature=0.7
                )
                script_content = response.choices[0].message.content
                
                # ELEVENLABS CLEANUP: Hier strippen we geforceerd alle overgebleven aanhalingstekens en streepjes eruit via Python
                script_content = script_content.replace('"', '').replace("'", "").replace("“", "").replace("”", "").replace("‘", "").replace("’", "").replace("-", " ")
                
                # Bereken het daadwerkelijke aantal woorden
                actual_word_count = len(script_content.split())
                
                st.success("BINGO! 🎉 Your script has been successfully written!")
                
                # Toon de woordenteller aan de editor
                st.info(f"📊 Final Script Length: **{actual_word_count} words** (Target was {target_words})")
                
                # Toon het script zodat de editor het makkelijk kan kopiëren
                st.text_area("Result (Copy this directly into ElevenLabs):", value=script_content, height=400)
                
                # Voeg direct een knop toe om het als .txt te downloaden
                st.download_button(
                    label="📥 Download as .txt file",
                    data=script_content,
                    file_name="New_Video_Script.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"Something went wrong with the API: {e}")


# ==========================================
# TOOL 2: DE STORYBOARD FABRIEK
# ==========================================
elif huidige_pagina == "🎬 Storyboard Fabriek":
    st.title("Generate Stickman Images For Your Videos")
    st.write("The factory is running! Enter your API key, paste your script, and let's create.")

    user_api_key = st.text_input("Paste your OpenAI API key here:", type="password", key="api_key_images")

    quality_map = {
        "Medium quality": "standard",
        "High quality (may cost more Openai tokes)": "hd"
    }
    selection = st.selectbox("Choose your Image Quality:", list(quality_map.keys()))
    kwaliteit = quality_map[selection]

    script_text = st.text_area("Paste here your script:", height=250)

    # Handige functie voor de ZIP file download
    def create_zip(images):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for i, img_bytes in enumerate(images):
                zip_file.writestr(f"scene_{i+1}.png", img_bytes)
        return zip_buffer.getvalue()

    if st.button("Generate"):
        if not user_api_key:
            st.error("Oops! Don't forget your API key.")
            st.stop()
        if not script_text:
            st.warning("Please paste your script in the box above.")
            st.stop()

        client = OpenAI(api_key=user_api_key)
        OUTPUT_DIR = "Gegeneerde_Film"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Reset of maak een nieuwe lijst aan voor de bytes van de afbeeldingen (voor de ZIP-knop)
        st.session_state.image_bytes_list = []
        
        with st.spinner("AI is analyzing script length to determine optimal scene count..."):
            try:
                word_count = len(script_text.split())
                target_scenes = max(15, min(100, word_count // 8)) 
                
                # Hier herstellen we de originele instructie om er een JSON lijst van te maken
                storyboard_prompt = (
                    f"Analyze the following script: {script_text}\n\n"
                    f"CRITICAL INSTRUCTION: Your target is to create approximately {target_scenes} scenes. "
                    "This is a dynamic ratio: you must maintain the pace of 1 scene per 8 words. "
                    "Break the script down into small, granular actions. "
                    "If the script is short, keep it punchy. If the script is long, keep the pace consistent. "
                    "Style: Minimalist stick figure illustration. "
                    "Return a JSON list of scenes. Format: {'scenes': [{'description': 'detailed visual prompt'}]}. "
                    "Do not include markdown formatting or extra text."
                )

                
                storyboard_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": storyboard_prompt}],
                    response_format={ "type": "json_object" }
                )
                data = json.loads(storyboard_response.choices[0].message.content)
                scenes = data['scenes']
                st.write(f"Storyboard created with {len(scenes)} scenes (Calculated for optimal pace).")
            except Exception as e:
                st.error(f"Error creating storyboard: {e}")
                st.stop()

        progress_bar = st.progress(0)
        
        # We maken even kolommen aan zodat de plaatjes mooi op het scherm passen
        cols = st.columns(3) 
        
        for i, scene in enumerate(scenes):
            actie_prompt = scene["description"]
            bestandsnaam = f"{i+1:03d}_youtube.jpg"
            
            # Voeg een st.spinner of status update toe
            st.write(f"🎨 Generating image {i+1}: {actie_prompt}")
            
            # De originele 'magische' prompt uit jouw lokale Filmfabriek!
            image_prompt = (
                "Generate a YouTube video illustration (16:9) . "
                "STYLE REQUIREMENTS: Simple 2D black line drawings, mostly white empty space . "
                "Pure white background, thick uneven black outlines, wobbly hand-drawn lines . "
                "Flat colors only . Very basic shapes and childish comic style . "
                "No realistic shading, no 3D, no cinematic lighting, no realistic cartoon style . "
                "Keep compositions extremely clear, simple, bold and centered . "
                f"OBJECTS AND ACTION TO DRAW: {actie_prompt}"
            )

            try:
                response = client.images.generate(
                    model="gpt-image-2", 
                    prompt=image_prompt, 
                    size="1792x1024", 
                    n=1
                )
                
                image_data = response.data[0]
                doel_pad = os.path.join(OUTPUT_DIR, bestandsnaam)
                
                if hasattr(image_data, 'url') and image_data.url:
                    img_data = requests.get(image_data.url).content
                elif hasattr(image_data, 'b64_json') and image_data.b64_json:
                    img_data = base64.b64decode(image_data.b64_json)
                else:
                    raise Exception("Geen afbeelding ontvangen van de API.")
                
                # Opslaan in de map (als backup)
                with open(doel_pad, 'wb') as handler:
                    handler.write(img_data)
                
                # Opslaan in het geheugen voor de ZIP download knop
                st.session_state.image_bytes_list.append(img_data)
                
                # Teken in een van de drie kolommen
                cols[i % 3].image(doel_pad, caption=f"Scene {i+1}")
                
            except Exception as e:
                st.error(f"Error generating image {i+1}: {e}")

            progress_bar.progress((i + 1) / len(scenes))

        st.success("Production Finished! 🎉")
        
        # De download-all ZIP knop verschijnt zodra alles klaar is
        if 'image_bytes_list' in st.session_state and len(st.session_state.image_bytes_list) > 0:
            zip_data = create_zip(st.session_state.image_bytes_list)
            st.download_button(
                label="📥 Download All Scenes as ZIP",
                data=zip_data,
                file_name="storyboard.zip",
                mime="application/zip"
            )

# ==========================================
# TOOL 3: THE VOICE-OVER STUDIO
# ==========================================
elif huidige_pagina == "🎙️ Voice-over Studio":
    st.title("🎙️ Voice-over Studio")
    st.write("Convert the generated script directly into an ElevenLabs voice-over.")
    
    # Haal de veilige sleutel op uit Streamlit Secrets
    try:
        elevenlabs_key = st.secrets["ELEVENLABS_API_KEY"]
    except:
        st.error("API key not found in Streamlit Secrets. Please contact the administrator.")
        st.stop()
        
    # Vul hier de Voice ID in van de stem die je altijd gebruikt voor je video's
    # (Je vindt deze ID op de website van ElevenLabs in de Voice Library/Lab)
    VOICE_ID = "VZcBEw9QXVSghzV5UKLN" 
    
    script_to_read = st.text_area("Paste the final script here:", height=300)
    
    if st.button("🎧 Generate Audio"):
        if not script_to_read:
            st.warning("Please paste a script first!")
            st.stop()
            
        with st.spinner("Generating professional voice-over... This takes a moment."):
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": elevenlabs_key
            }
            
            # Zorg dat de 'd' van data precies onder de 'h' van headers staat!
            data = {
                "text": script_to_read,
                "model_id": "eleven_multilingual_v2", 
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                audio_bytes = response.content
                st.success("BINGO! 🎉 Audio generated successfully!")
                
                # Laat de audio direct in de browser afspelen
                st.audio(audio_bytes, format="audio/mp3")
                
                # Voeg een downloadknop toe voor de editor
                st.download_button(
                    label="📥 Download Voice-over (MP3)",
                    data=audio_bytes,
                    file_name="Voiceover_Ready.mp3",
                    mime="audio/mpeg"
                )
            else:
                st.error(f"Something went wrong with ElevenLabs: {response.text}")

# ==========================================
# TOOL 4: DE BESCHRIJVING GENERATOR
# ==========================================
elif huidige_pagina == "📝 Beschrijving Generator":
    st.title("YouTube Beschrijving & Hoofdstukken")
    st.write("Upload de definitieve video en de AI genereert een perfecte beschrijving met timestamps en disclaimers.")

    # We gebruiken dezelfde API key input stijl als in je andere tools
    user_api_key = st.text_input("Paste your OpenAI API key here:", type="password", key="api_key_desc")
    
    st.info("Let op: OpenAI accepteert bestanden tot maximaal 25MB. Als de MP4 te groot is, laat je editor dan een .mp3 of lage-kwaliteit .mp4 exporteren voor deze tool.")
    uploaded_file = st.file_uploader("Upload je MP4 (of MP3) video bestand:", type=["mp4", "mp3", "m4a", "wav"])

    if st.button("📝 Genereer Beschrijving"):
        if not user_api_key:
            st.error("Please enter an API key!")
            st.stop()
        if not uploaded_file:
            st.warning("Upload eerst een bestand.")
            st.stop()

        # Check of het bestand niet groter is dan de 25MB limiet van OpenAI
        if uploaded_file.size > 25 * 1024 * 1024:
            st.error("Dit bestand is groter dan 25MB. Comprimeer de video of upload alleen het audiospoor (.mp3).")
            st.stop()

        client = OpenAI(api_key=user_api_key)

        with st.spinner("🎧 Video aan het scannen voor timestamps... (Dit kan even duren)"):
            try:
                # 1. Stuur de audio/video naar Whisper voor een transcriptie met timestamps (SRT)
                transcript_response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=uploaded_file,
                    response_format="srt"
                )
                
                st.success("Timestamps succesvol uitgelezen! Nu de beschrijving schrijven...")

                # 2. Geef de exacte structuur door aan GPT-4o
                system_prompt = f"""
                Act as an expert YouTube strategist. Here is the SRT transcription (including exact timestamps) of a YouTube video:

                {transcript_response}

                Based on this transcript, generate a YouTube description EXACTLY matching this structure:

                [Write a compelling 2-3 paragraph summary of the video here in English]

                👇 What you will learn in this video:
                [List 4-5 key takeaways based on the video content]

                ⏱️ Chapters:
                0:00 - [Catchy Intro Title]
                [Extract relevant chapters and their timestamps from the SRT data. Format exactly like 'M:SS - Title' or 'MM:SS - Title']

                [Add 5-7 relevant hashtags here, e.g., #Psychology #SelfImprovement]

                ⚠️ Disclaimer: I am not a licensed psychologist or medical professional. Everything in this video is based on psychological studies, behavioral research, and personal self-improvement experiments. If you are struggling with severe social anxiety or mental health issues, please consult a qualified therapist or doctor. The goal of this video is to inform, inspire, and help you build better communication habits safely and sustainably. Remember: It's not about faking intelligence to impress others; it's about developing real self-awareness to elevate your life.

                📜 Copyright Disclaimer:All content in this video is intended solely for educational and informational purposes. ItsAllGoodda does not claim ownership of any copyrighted material used in this content. All media, including images, videos, music, and clips, are used under the guidelines of Fair Use for commentary, criticism, teaching, research, and transformative use. If you are the copyright owner of any material used and believe it has been used improperly, please contact us directly. We will be happy to resolve the issue.
                """

                with st.spinner("✍️ Definitieve tekst aan het genereren..."):
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You strictly follow formatting rules and output English text."},
                            {"role": "user", "content": system_prompt}
                        ],
                        temperature=0.7
                    )
                    
                    final_description = response.choices[0].message.content
                    
                    st.success("BINGO! 🎉 Jouw YouTube beschrijving is klaar.")
                    
                    st.text_area("Resultaat (Kopieer dit direct naar YouTube):", value=final_description, height=500)
                    
                    st.download_button(
                        label="📥 Download als .txt",
                        data=final_description,
                        file_name="YouTube_Description.txt",
                        mime="text/plain"
                    )

            except Exception as e:
                st.error(f"Er ging iets mis met de API: {e}")

# Bovenaan in je document moet je deze extra import toevoegen (onder import io):
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# TOOL 5: DE THUMBNAIL COMPOSITOR
# ==========================================
elif huidige_pagina == "🖼️ Thumbnail Compositor":
    st.title("🖼️ Thumbnail Compositor")
    st.write("Bouw in 2 seconden een 100% consistente thumbnail.")

    # Maak automatisch de assets map aan als deze niet bestaat
    if not os.path.exists("assets"):
        os.makedirs("assets")

    # 1. De lijst met 15 specifieke emoties / houdingen
    emoties = [
        "Blij", "Verward", "Geschrokken", "Boos", "Huilend",
        "Rennend", "Wijzend", "Nadenkend", "Lachend", "Gefrustreerd",
        "Slapend", "Verbaasd", "Trots", "Zwaaiend", "Schouderophalend"
    ]
    gekozen_emotie = st.selectbox("1. Kies de houding/emotie van je Stickman:", emoties)

    st.markdown("---")
    
    # 2. Achtergrond instellingen
    bg_keuze = st.radio("2. Kies je achtergrond:", ["Effen Kleur (Snel & Opvallend)", "Upload een achtergrondafbeelding"])
    bg_color = "#FFCC00" # Standaard YouTube geel
    bg_image = None
    
    if bg_keuze == "Effen Kleur (Snel & Opvallend)":
        bg_color = st.color_picker("Kies de kleurcode:", "#FFD700")
    else:
        bg_image = st.file_uploader("Upload achtergrond (Ideaal 1280x720):", type=["jpg", "png", "jpeg"])

    st.markdown("---")

    # 3. Tekst Opties (Met mogelijkheid voor "Geen tekst")
    voeg_tekst_toe = st.checkbox("3. Voeg grote tekst toe aan de thumbnail", value=False)
    thumbnail_tekst = ""
    if voeg_tekst_toe:
        thumbnail_tekst = st.text_input("Typ je clickbait tekst hier:", "SHOCKING TRUTH")
        st.info("Tip: Upload een lettertype bestand genaamd 'impact.ttf' in je map voor het beste, dikke YouTube-effect.")

    if st.button("🖼️ Genereer Thumbnail"):
        with st.spinner("Thumbnail aan het bouwen..."):
            try:
                # A. Maak de achtergrond (1280 x 720 is de YouTube standaard)
                if bg_image:
                    bg = Image.open(bg_image).convert("RGBA")
                    bg = bg.resize((1280, 720))
                else:
                    bg = Image.new("RGBA", (1280, 720), bg_color)

                # B. Laad en plak de stickman
                stickman_pad = f"assets/{gekozen_emotie.lower()}.png"
                if os.path.exists(stickman_pad):
                    stickman = Image.open(stickman_pad).convert("RGBA")
                    
                    # Zorg dat de stickman mooi op maat is en zet hem rechts in beeld
                    stickman.thumbnail((700, 700))
                    
                    # Bereken positie: Rechts in het midden
                    y_pos = (720 - stickman.height) // 2
                    x_pos = 1200 - stickman.width 
                    
                    # Plak de stickman met behoud van transparantie
                    bg.paste(stickman, (x_pos, y_pos), stickman)
                else:
                    st.error(f"⚠️ Stickman niet gevonden! Upload eerst jouw bestand '{gekozen_emotie.lower()}.png' in de 'assets' map op je GitHub.")
                    st.stop()

                # C. Tekst toevoegen (Als de checkbox is aangevinkt)
                if voeg_tekst_toe and thumbnail_tekst:
                    draw = ImageDraw.Draw(bg)
                    
                    # Probeer Impact te laden, anders een standaard font
                    try:
                        font = ImageFont.truetype("impact.ttf", 90)
                    except:
                        font = ImageFont.load_default()
                        st.warning("Standaard lettertype gebruikt. Zet 'impact.ttf' in GitHub voor een dikkere tekst.")

                    # Voeg tekst toe met een strakke zwarte omlijning (stroke)
                    draw.text((70, 300), thumbnail_tekst, fill="white", font=font, stroke_width=4, stroke_fill="black")

                # D. Toon resultaat
                st.success("Thumbnail is klaar!")
                st.image(bg, caption=f"Thumbnail: {gekozen_emotie}")

                # E. Maak downloadbaar
                buf = io.BytesIO()
                bg_rgb = bg.convert("RGB")
                bg_rgb.save(buf, format="JPEG", quality=95)
                st.download_button(
                    label="📥 Download YouTube Thumbnail",
                    data=buf.getvalue(),
                    file_name=f"Thumbnail_{gekozen_emotie}.jpg",
                    mime="image/jpeg"
                )

            except Exception as e:
                st.error(f"Er ging iets mis tijdens het bouwen: {e}")