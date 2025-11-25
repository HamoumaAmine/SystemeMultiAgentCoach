import tempfile
import shutil


def save_temp_file(upload_file):
    """
    Sauvegarde un UploadFile FastAPI dans un fichier temporaire.
    Retourne le chemin complet.
    """
    suffix = "." + upload_file.filename.split(".")[-1]

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    shutil.copyfileobj(upload_file.file, temp)

    return temp.name