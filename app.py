import os
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import whisper
from mistralai import Mistral

# Charger les variables d'environnement
load_dotenv()

# Configuration du projet
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['OUTPUT_FOLDER'] = 'static/outputs'
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav', 'ogg', 'flac'}

# Charger le modèle Whisper
model = whisper.load_model("base")

# Mistral API client pour la traduction
def mistral_translate(text, lang):
    api_key = os.environ["MISTRAL_API_KEY"]
    client = Mistral(api_key=api_key)

    chat_response = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {
                "role": "user",
                "content": f"Translate this sentence into {lang} without adding any explanations or extra elements: {text}",
            },
        ]
    )
    return chat_response.choices[0].message.content

# Vérifier les extensions de fichier
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Fonction de transcription et de génération de notes de réunion
def generate_meeting_notes(audio_file_path, target_language="default"):
    try:
        # Transcrire l'audio
        result = model.transcribe(audio_file_path)
        meeting_notes = result["text"]

        # Traduire si nécessaire
        if target_language == "default":
            translated_notes = meeting_notes  # Pas de traduction, on garde la version originale
        else:
            translated_notes = mistral_translate(meeting_notes, target_language)

        # Sauvegarder les notes dans un fichier
        output_file_path = os.path.join(app.config['OUTPUT_FOLDER'], f"meeting_notes_{target_language}.txt")
        with open(output_file_path, 'w') as f:
            f.write(f"Notes de réunion : \n{meeting_notes}\n\nTraduction : \n{translated_notes}")

        return meeting_notes, translated_notes, output_file_path
    except Exception as e:
        print(f"Erreur lors de la génération des notes : {e}")
        return "Erreur lors de la génération des notes.", "", ""

# Liste des langues disponibles
LANGUAGES = {
    'default': 'Version originale',
    'en': 'Anglais',
    'fr': 'Français'
}

# Route principale (Page d'accueil)
@app.route('/')
def index():
    return render_template('index.html', languages=LANGUAGES)

# Route pour uploader un fichier audio
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return redirect(request.url)

        # Utiliser directement le nom du fichier sans sécurisation
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Récupérer la langue choisie pour la traduction
        target_language = request.form.get('language', 'default')

        # Appeler la fonction pour générer les notes de réunion et les traduire
        meeting_notes, translated_notes, output_file_path = generate_meeting_notes(file_path, target_language)

        # Vérifier si le fichier de sortie existe
        file_exists = os.path.exists(output_file_path)

        return render_template('index.html', meeting_notes=meeting_notes, translated_notes=translated_notes,
                               file_exists=file_exists, output_file_path=output_file_path, target_language=target_language, languages=LANGUAGES)
    except Exception as e:
        print(f"Erreur lors de l'upload du fichier ou du traitement : {e}")
        return "Une erreur est survenue pendant le traitement de votre fichier."

if __name__ == '__main__':
    app.run(debug=True)
