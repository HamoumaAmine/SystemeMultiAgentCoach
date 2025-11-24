# main.py
import os

def main():
    # Dossier où se trouve le mp3 et où sera créé le fichier texte
    mp3_folder = "mp3"
    os.makedirs(mp3_folder, exist_ok=True)

    # Chemin complet du fichier texte
    output_txt_file = os.path.join(mp3_folder, "mp3_transcription.txt")

    # Texte de la transcription
    transcription_text = """Python, c'est quoi ? Salut, je suis Thierry de l'informatique sans complexe. Bienvenue dans cette nouvelle vidéo. Cette semaine, on change un peu et on parle de programmation avec Python. Qu'est-ce que c'est vraiment ? Que peut-on faire avec ? ...
    (Ajoute ici le reste du texte de ta transcription)"""

    # Création du fichier texte
    with open(output_txt_file, "w", encoding="utf-8") as f:
        f.write(transcription_text)

    print(f"Fichier texte créé avec succès : {output_txt_file}")

if __name__ == "__main__":
    main()



