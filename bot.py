import os
import asyncio
import requests
from urllib.parse import quote
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from faster_whisper import WhisperModel

# Carrega as variáveis do arquivo .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
NUM_IMAGENS = 8
MODELO_WHISPER = "small"  # tiny, base, small, medium

print("Carregando modelo Whisper... (pode demorar na primeira vez)")
model = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")

def gerar_prompts(texto: str) -> list[str]:
    """Cria 8 prompts no estilo TikTok a partir da transcrição"""
    estilo_base = "estilo TikTok viral, cores vibrantes, alta energia, cinematográfico, vertical 9:16, tendência, alta qualidade, detalhado"
    
    palavras = texto.split()
    partes = []
    
    if len(palavras) > 20:
        tamanho = len(palavras) // 4
        for i in range(4):
            parte = " ".join(palavras[i*tamanho:(i+1)*tamanho])
            partes.append(parte)
    else:
        partes = [texto] * 4

    variacoes = [
        "close-up emocional, expressão forte",
        "cena dinâmica com movimento",
        "plano aberto impactante",
        "estilo storytelling visual",
        "atmosfera intensa e dramática",
        "visual moderno e clean",
        "momento climáxico da história",
        "cena de impacto visual forte"
    ]

    prompts = []
    for i in range(NUM_IMAGENS):
        base = partes[i % len(partes)]
        prompt = f"{base}, {variacoes[i]}, {estilo_base}"
        prompts.append(prompt)
    
    return prompts

def baixar_imagem(prompt: str, indice: int) -> str | None:
    """Gera imagem grátis via Pollinations"""
    prompt_encoded = quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=768&height=1344&nologo=true&model=flux"
    
    print(f"Gerando imagem {indice+1}/{NUM_IMAGENS}...")
    try:
        response = requests.get(url, timeout=90)
        if response.status_code == 200:
            caminho = f"imagem_{indice+1}.jpg"
            with open(caminho, "wb") as f:
                f.write(response.content)
            return caminho
    except Exception as e:
        print(f"Erro na imagem {indice+1}: {e}")
    return None

async def processar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🎧 Recebi o áudio! Transcrevendo...")

    # Baixa o áudio
    if update.message.voice:
        arquivo = await update.message.voice.get_file()
    else:
        arquivo = await update.message.audio.get_file()

    caminho_audio = "audio_temp.ogg"
    await arquivo.download_to_drive(caminho_audio)

    # Transcreve
    await msg.edit_text("📝 Transcrevendo o áudio...")
    segmentos, _ = model.transcribe(caminho_audio, language="pt")
    texto = " ".join([seg.text for seg in segmentos]).strip()

    if not texto:
        await msg.edit_text("Não consegui entender o áudio 😕")
        os.remove(caminho_audio)
        return

    await msg.edit_text(f"✅ Transcrição pronta!\n\n{texto[:250]}...\n\n🎨 Gerando {NUM_IMAGENS} imagens no estilo TikTok...")

    prompts = gerar_prompts(texto)
    caminhos = []

    for i, prompt in enumerate(prompts):
        caminho = baixar_imagem(prompt, i)
        if caminho:
            caminhos.append(caminho)
        await asyncio.sleep(16)  # Respeita o limite gratuito

    await msg.edit_text(f"🚀 Enviando {len(caminhos)} imagens...")

    for caminho in caminhos:
        with open(caminho, "rb") as f:
            await update.message.reply_photo(photo=f)
        os.remove(caminho)

    await update.message.reply_text("✅ Pronto! Aqui estão suas imagens.\nAgora é só montar no CapCut 🔥")

    if os.path.exists(caminho_audio):
        os.remove(caminho_audio)

def main():
    if not TOKEN:
        print("❌ Erro: TELEGRAM_TOKEN não encontrado. Verifique o arquivo .env")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, processar_audio))
    
    print("✅ Bot rodando! Manda um áudio no Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
