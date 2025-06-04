
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator
from typing import Optional
import uuid, os, json, shutil
from datetime import datetime
import cloudinary
import cloudinary.uploader
import aiohttp
from dotenv import load_dotenv
from backend.matching import find_matches_for_trouve, find_matches_for_perdu
from backend.db import AsyncSessionLocal, ObjetTrouve, ObjetPerdu
import asyncio

# Charger les variables d'environnement depuis un fichier .env si présent
load_dotenv()

# Configurer Cloudinary
cloudinary.config(
    cloudinary_url=os.getenv("CLOUDINARY_URL")
)

app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Créer les dossiers nécessaires
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads")
FRONTEND_DIR = os.getenv("FRONTEND_DIR", "frontend")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 20 * 1024 * 1024))  # 20 Mo par défaut (HD autorisé)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)


def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.post("/api/objets_trouves")
async def ajouter_objet_trouve(
    photo: UploadFile = File(...),
    description: str = Form(...),
    date_rapport: str = Form(...),
    infos: str = Form("")
):
    # Validation description
    if not description or len(description.strip()) < 3:
        raise HTTPException(status_code=400, detail="Description trop courte.")
    # Validation date
    try:
        datetime.fromisoformat(date_rapport)
    except Exception:
        raise HTTPException(status_code=400, detail="Date de découverte invalide.")
    # Validation fichier
    if not allowed_file(photo.filename):
        raise HTTPException(status_code=400, detail="Format de fichier non autorisé.")
    contents = await photo.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 2 Mo).")
    # Upload Cloudinary
    result = cloudinary.uploader.upload(contents, folder="objets-trouves", resource_type="image")
    url_cloudinary = result.get("secure_url")
    objet_trouve = {
        "id": str(uuid.uuid4()),
        "description": description.strip(),
        "date_rapport": date_rapport.strip(),
        "infos": infos.strip(),
        "image": url_cloudinary,
        "rendu": False
    }
    objets = load_json("objets_trouves.json")
    objets.append(objet_trouve)
    save_json("objets_trouves.json", objets)
    # Sauvegarde aussi dans PostgreSQL
    async def save_objet_trouve_db(objet_dict):
        async with AsyncSessionLocal() as session:
            obj = ObjetTrouve(**objet_dict)
            session.add(obj)
            await session.commit()
    asyncio.create_task(save_objet_trouve_db(objet_trouve))
    # Recherche de correspondances dans objets_perdus.json
    objets_perdus = load_json("objets_perdus.json")
    matches = find_matches_for_trouve(objets_perdus, objet_trouve["description"])
    # Construction du champ matches pour le frontend
    matches_out = [
        {
            "id": obj.get("id"),
            "description": obj.get("description"),
            "type": "perdu",
            "date_rapport": obj.get("date_rapport"),
            "nom": obj.get("nom", ""),
            "prenom": obj.get("prenom", ""),
            "infos": obj.get("infos", "")
        } for obj in matches
    ]
    response = objet_trouve.copy()
    response["matches"] = matches_out
    response["message"] = "Objet trouvé ajouté"
    return response

class ObjetPerduForm(BaseModel):
    description: str
    date_rapport: str
    infos: Optional[str] = ""
    nom: str
    prenom: str
    telephone: str
    email: str

    @validator('description')
    def description_valide(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Description trop courte.')
        return v.strip()

    @validator('date_rapport')
    def date_valide(cls, v):
        try:
            datetime.fromisoformat(v)
        except Exception:
            raise ValueError('Date estimée invalide.')
        return v

    @validator('email')
    def email_valide(cls, v):
        if '@' not in v or '.' not in v:
            raise ValueError('Email invalide.')
        return v.strip()

    @validator('telephone')
    def tel_valide(cls, v):
        if not v or len(v.strip()) < 6:
            raise ValueError('Numéro de téléphone invalide.')
        return v.strip()

@app.post("/api/objets_perdus")
async def ajouter_objet_perdu(objet: ObjetPerduForm):
    objets = load_json("objets_perdus.json")
    data = objet.dict()
    data["id"] = str(uuid.uuid4())
    objets.append(data)
    save_json("objets_perdus.json", objets)
    # Sauvegarde aussi dans PostgreSQL
    async with AsyncSessionLocal() as session:
        obj = ObjetPerdu(**data)
        session.add(obj)
        await session.commit()
    # Recherche de correspondances dans la base (objets trouvés)
    async with AsyncSessionLocal() as session:
        result = await session.execute(ObjetTrouve.__table__.select())
        objets_trouves = [dict(row._mapping) for row in result]
    matches = find_matches_for_perdu(objets_trouves, data["description"])
    matches_out = [
        {
            "id": obj.get("id"),
            "description": obj.get("description"),
            "type": "trouve",
            "date_rapport": obj.get("date_rapport"),
            "infos": obj.get("infos", "")
        } for obj in matches
    ]
    response = data.copy()
    response["matches"] = matches_out
    response["message"] = "Objet perdu ajouté"
    return response

@app.get("/api/objets_trouves")
async def get_objets_trouves():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            ObjetTrouve.__table__.select()
        )
        objets = [dict(row._mapping) for row in result]
    return objets

from fastapi import Body

from typing import Optional
from fastapi import Query
from pydantic import BaseModel

class SuppressionCode(BaseModel):
    code: str

@app.delete("/api/objets_trouves/{objet_id}")
async def supprimer_objet_trouve(objet_id: str, code: Optional[str] = Query(None), body: Optional[SuppressionCode] = Body(None)):
    code_final = code
    if body and hasattr(body, 'code'):
        code_final = body.code
    print('Body reçu:', body, 'Code reçu:', code_final)
    if code_final != "7120":
        raise HTTPException(status_code=403, detail="Code de suppression incorrect.")
    objets = load_json("objets_trouves.json")
    nouveaux = [obj for obj in objets if obj.get("id") != objet_id]
    if len(objets) == len(nouveaux):
        raise HTTPException(status_code=404, detail="Objet non trouvé.")
    save_json("objets_trouves.json", nouveaux)
    # Suppression dans la base PostgreSQL
    async with AsyncSessionLocal() as session:
        await session.execute(
            ObjetTrouve.__table__.delete().where(ObjetTrouve.__table__.c.id == objet_id)
        )
        await session.commit()
    return {"message": "Objet supprimé", "id": objet_id}

@app.delete("/api/objets_perdus/{objet_id}")
async def supprimer_objet_perdu(objet_id: str, code: str = Body(...)):
    if code != "7120":
        raise HTTPException(status_code=403, detail="Code de suppression incorrect.")
    objets = load_json("objets_perdus.json")
    nouveaux = [obj for obj in objets if obj.get("id") != objet_id]
    if len(objets) == len(nouveaux):
        raise HTTPException(status_code=404, detail="Objet non trouvé.")
    save_json("objets_perdus.json", nouveaux)
    # Suppression dans la base PostgreSQL
    async with AsyncSessionLocal() as session:
        await session.execute(
            ObjetPerdu.__table__.delete().where(ObjetPerdu.__table__.c.id == objet_id)
        )
        await session.commit()
    return {"message": "Objet supprimé", "id": objet_id}

@app.post("/api/objets_trouves/rendu")
async def rendre_objet_trouve(
    objet_id: str = Form(...),
    nom: str = Form(...),
    prenom: str = Form(...),
    telephone: str = Form(...),
    email: str = Form(...),
    photo: UploadFile = File(None)
):
    objets = load_json("objets_trouves.json")
    trouve = False
    for obj in objets:
        if obj.get("id") == objet_id:
            obj["rendu"] = True
            obj["nom_beneficiaire"] = nom.strip()
            obj["prenom_beneficiaire"] = prenom.strip()
            obj["telephone_beneficiaire"] = telephone.strip()
            obj["email_beneficiaire"] = email.strip()
            if photo:
                if not allowed_file(photo.filename):
                    raise HTTPException(status_code=400, detail="Format de fichier non autorisé.")
                contents = await photo.read()
                if len(contents) > MAX_UPLOAD_SIZE:
                    raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 2 Mo).")
                # Upload Cloudinary
                result = cloudinary.uploader.upload(contents, folder="objets-trouves/rendus", resource_type="image")
                url_cloudinary = result.get("secure_url")
                obj["photo_rendu"] = url_cloudinary
            trouve = True
            break
    if not trouve:
        raise HTTPException(status_code=404, detail="Objet non trouvé")
    save_json("objets_trouves.json", objets)

    # Mise à jour dans la base PostgreSQL
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            ObjetTrouve.__table__.select().where(ObjetTrouve.__table__.c.id == objet_id)
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Objet non trouvé en base")
        update_data = {
            "rendu": True,
            "nom_beneficiaire": nom.strip(),
            "prenom_beneficiaire": prenom.strip(),
            "telephone_beneficiaire": telephone.strip(),
            "email_beneficiaire": email.strip(),
        }
        if chemin_photo:
            update_data["photo_rendu"] = chemin_photo
        await session.execute(
            ObjetTrouve.__table__.update().where(ObjetTrouve.__table__.c.id == objet_id).values(**update_data)
        )
        await session.commit()

    return {"message": "Objet marqué comme rendu", "id": objet_id}

# Route legacy pour compatibilité (clic direct, sans modal)
@app.post("/api/objets_trouves/{objet_id}/rendu")
async def marquer_objet_rendu(objet_id: str):
    objets = load_json("objets_trouves.json")
    trouve = False
    for obj in objets:
        if obj.get("id") == objet_id:
            obj["rendu"] = True
            trouve = True
            break
    if not trouve:
        raise HTTPException(status_code=404, detail="Objet non trouvé")
    save_json("objets_trouves.json", objets)
    # Mise à jour dans la base PostgreSQL
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            ObjetTrouve.__table__.select().where(ObjetTrouve.__table__.c.id == objet_id)
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Objet non trouvé en base")
        await session.execute(
            ObjetTrouve.__table__.update().where(ObjetTrouve.__table__.c.id == objet_id).values(rendu=True)
        )
        await session.commit()
    return {"message": "Statut mis à jour", "id": objet_id}


@app.get("/api/objets_perdus")
async def get_objets_perdus():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            ObjetPerdu.__table__.select()
        )
        objets = [dict(row._mapping) for row in result]
    return objets

from fastapi.responses import StreamingResponse
import csv
from io import StringIO

import base64

@app.get("/api/export")
async def exporter_objets():
    async with AsyncSessionLocal() as session:
        result_trouves = await session.execute(ObjetTrouve.__table__.select())
        objets_trouves = [dict(row._mapping) for row in result_trouves]
        result_perdus = await session.execute(ObjetPerdu.__table__.select())
        objets_perdus = [dict(row._mapping) for row in result_perdus]
    from fastapi.responses import HTMLResponse
    from markupsafe import escape
    html = [
        '<!DOCTYPE html>',
        '<html lang="fr"><head><meta charset="utf-8" />',
        '<title>Export Objets trouvés & perdus</title>',
        '<style>body{font-family:sans-serif;background:#f8fafc;}h1{color:#3b82f6;}table{border-collapse:collapse;width:100%;margin:20px 0;}th,td{border:1px solid #d1d5db;padding:8px;}th{background:#3b82f6;color:#fff;}tr:nth-child(even){background:#f1f5f9;}img{max-width:130px;max-height:130px;border-radius:8px;}caption{font-weight:bold;font-size:1.2em;margin-bottom:5px;}hr{margin:30px 0;}</style>',
        '</head><body>',
        f'<h1>Export des objets trouvés et perdus ({datetime.now().strftime("%d/%m/%Y %H:%M")})</h1>'
    ]
    # Objets trouvés
    html.append('<table><caption>Objets trouvés</caption><tr>'
        '<th>ID</th><th>Description</th><th>Date</th><th>Infos</th><th>Image</th><th>Statut</th><th>Bénéficiaire</th><th>Photo rendu</th></tr>')
    for obj in objets_trouves:
        image_path = obj.get('image')
        img_tag = ''
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()
            b64 = base64.b64encode(img_data).decode()
            ext = image_path.rsplit('.', 1)[-1].lower()
            img_tag = f'<img src="data:image/{ext};base64,{b64}" alt="image" />'
        elif image_path:
            # Si c'est une URL Cloudinary, essayer de la télécharger et encoder
            if image_path.startswith("http"):
                try:
                    async with aiohttp.ClientSession() as session_img:
                        async with session_img.get(image_path) as resp:
                            if resp.status == 200:
                                img_data = await resp.read()
                                # Déduire l'extension depuis l'URL ou le header
                                ext = image_path.split('.')[-1].split('?')[0].lower()
                                if ext not in ["jpg", "jpeg", "png", "gif"]:
                                    ext = resp.headers.get("Content-Type", "image/jpeg").split("/")[-1]
                                b64 = base64.b64encode(img_data).decode()
                                img_tag = f'<img src="data:image/{ext};base64,{b64}" alt="image" />'
                            else:
                                img_tag = f'<span>Image non dispo</span>'
                except Exception:
                    img_tag = f'<span>Image non dispo</span>'
            else:
                img_tag = f'<span>Image non dispo</span>'
        else:
            img_tag = ''
        statut = 'Rendu' if obj.get('rendu') else 'Non rendu'
        benef = ''
        photo_rendu = ''
        if obj.get('rendu'):
            benef = f"{escape(obj.get('nom_beneficiaire',''))} {escape(obj.get('prenom_beneficiaire',''))}<br>Tél: {escape(obj.get('telephone_beneficiaire',''))}<br>Email: {escape(obj.get('email_beneficiaire',''))}"
            if obj.get('photo_rendu'):
                photo_path = obj['photo_rendu']
                try:
                    ext = photo_path.rsplit('.', 1)[-1].lower()
                    mime = 'image/jpeg' if ext in ['jpg', 'jpeg'] else ('image/png' if ext == 'png' else ('image/gif' if ext == 'gif' else 'application/octet-stream'))
                    with open(photo_path, 'rb') as imgf:
                        img_b64 = base64.b64encode(imgf.read()).decode('utf-8')
                    photo_rendu = f'<img src="data:{mime};base64,{img_b64}" alt="photo rendu" />'
                except Exception as e:
                    photo_rendu = f'<span style="color:red">(photo non disponible)</span>'
        html.append(f'<tr><td>{escape(obj.get("id",""))}</td><td>{escape(obj.get("description",""))}</td><td>{escape(obj.get("date_rapport",""))}</td><td>{escape(obj.get("infos",""))}</td><td>{img_html}</td><td>{statut}</td><td>{benef}</td><td>{photo_rendu}</td></tr>')
    html.append('</table><hr>')
    # Objets perdus
    html.append('<table><caption>Objets perdus</caption><tr>'
        '<th>ID</th><th>Description</th><th>Date</th><th>Infos</th><th>Nom</th><th>Prénom</th><th>Téléphone</th><th>Email</th></tr>')
    for obj in objets_perdus:
        html.append(f'<tr><td>{escape(obj.get("id",""))}</td><td>{escape(obj.get("description",""))}</td><td>{escape(obj.get("date_rapport",""))}</td><td>{escape(obj.get("infos",""))}</td><td>{escape(obj.get("nom",""))}</td><td>{escape(obj.get("prenom",""))}</td><td>{escape(obj.get("telephone",""))}</td><td>{escape(obj.get("email",""))}</td></tr>')
    html.append('</table>')
    html.append('</body></html>')
    content = '\n'.join(html)
    filename = f"export_objets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    return HTMLResponse(content=content, headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

# Servir les images uploadées
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Servir frontend APRÈS les routes API
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")