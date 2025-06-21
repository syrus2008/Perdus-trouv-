
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Body, Depends
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
from backend.db import AsyncSessionLocal, ObjetTrouve, ObjetPerdu, ComparaisonIgnoree, User, engine
from backend.schemas import UserCreate, UserInDB, UserPublic, Token
from backend.auth import get_password_hash, verify_password, create_access_token
from backend.dependencies import get_current_active_user, get_current_admin_user
from backend.db import ActionLog
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
import asyncio
import logging

app = FastAPI()
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# COMPARAISONS_IGNOREES_PATH = os.path.join(os.path.dirname(__file__), "comparaisons_ignorees.json")
# (plus utilisé, remplacé par la base PostgreSQL)

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.get("/api/comparaisons/ignorees")
async def get_comparaisons_ignorees(current_user=Depends(get_current_active_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(ComparaisonIgnoree.__table__.select())
        couples = [dict(row._mapping) for row in result]
    return couples

from uuid import uuid4

@app.get("/api/matchs_auto")
async def matchs_auto():
    objets_trouves = load_json("objets_trouves.json")
    objets_perdus = load_json("objets_perdus.json")
    matches = []
    for obj_t in objets_trouves:
        if obj_t.get("rendu"):
            continue
        for obj_p in find_matches_for_trouve(objets_perdus, obj_t["description"]):
            matches.append({
                "id_trouve": obj_t["id"],
                "id_perdu": obj_p["id"],
                "description": obj_p["description"],
                "type": "perdu",
                "date_rapport": obj_p.get("date_rapport"),
                "nom": obj_p.get("nom"),
                "prenom": obj_p.get("prenom"),
                "infos": obj_p.get("infos")
            })
    return matches

@app.post("/api/comparaisons/ignorer")
async def post_comparaison_ignorer(data: dict = Body(...), current_user=Depends(get_current_active_user)):
    """Body: {"id_trouve":..., "id_perdu":...}"""
    if "id_trouve" not in data or "id_perdu" not in data:
        raise HTTPException(status_code=400, detail="id_trouve et id_perdu requis")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            ComparaisonIgnoree.__table__.select().where(
                (ComparaisonIgnoree.id_trouve == data["id_trouve"]) &
                (ComparaisonIgnoree.id_perdu == data["id_perdu"])
            )
        )
        if result.first():
            return {"message": "Déjà ignoré"}
        new_ignore = ComparaisonIgnoree(
            id=str(uuid4()),
            id_trouve=data["id_trouve"],
            id_perdu=data["id_perdu"]
        )
        session.add(new_ignore)
        await session.commit()
    return {"message": "Ajouté"}

# Configuration du logging structuré
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Charger les variables d'environnement depuis un fichier .env si présent
load_dotenv()
# Configurer Cloudinary
cloudinary.config(
    cloudinary_url=os.getenv("CLOUDINARY_URL")
)

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

# Code de suppression externalisé
SUPPRESSION_CODE = os.getenv("SUPPRESSION_CODE", "7120")


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
    try:
        result = cloudinary.uploader.upload(contents, folder="objets-trouves", resource_type="image")
        url_cloudinary = result.get("secure_url")
        logging.info(f"Upload Cloudinary réussi pour {photo.filename} : {url_cloudinary}")
    except Exception as e:
        logging.error(f"Erreur upload Cloudinary : {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'upload de l'image sur Cloudinary.")
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
    logging.info(f"Objet trouvé ajouté (JSON et DB) : {objet_trouve['id']}")
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
async def ajouter_objet_perdu(objet: ObjetPerduForm, current_user=Depends(get_current_active_user)):
    objets = load_json("objets_perdus.json")
    data = objet.dict()
    data["id"] = str(uuid.uuid4())
    objets.append(data)
    save_json("objets_perdus.json", objets)
    logging.info(f"Objet perdu ajouté par {current_user.username}")
    # Sauvegarde aussi dans PostgreSQL
    async with AsyncSessionLocal() as session:
        obj = ObjetPerdu(**data)
        session.add(obj)
        await session.commit()
        # Log action
        action_log = ActionLog(
            user_id=current_user.id,
            action="create",
            object_type="objet_perdu",
            object_id=obj.id
        )
        session.add(action_log)
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
async def get_objets_trouves(current_user=Depends(get_current_active_user)):
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
async def supprimer_objet_trouve(objet_id: str, code: Optional[str] = Query(None), body: Optional[SuppressionCode] = Body(None), current_user=Depends(get_current_active_user)):
    code_final = code
    if body and hasattr(body, 'code'):
        code_final = body.code
    print('Body reçu:', body, 'Code reçu:', code_final)
    if code_final != "7120":
        raise HTTPException(status_code=403, detail="Code de suppression incorrect.")
    # Suppression dans la base PostgreSQL d'abord
    deleted_in_db = False
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            ObjetTrouve.__table__.select().where(ObjetTrouve.__table__.c.id == objet_id)
        )
        row = result.first()
        if row:
            await session.execute(
                ObjetTrouve.__table__.delete().where(ObjetTrouve.__table__.c.id == objet_id)
            )
            await session.commit()
            deleted_in_db = True
    # Suppression dans le JSON si présent
    objets = load_json("objets_trouves.json")
    nouveaux = [obj for obj in objets if obj.get("id") != objet_id]
    if len(objets) != len(nouveaux):
        save_json("objets_trouves.json", nouveaux)
    # Log action
    async with AsyncSessionLocal() as session:
        action_log = ActionLog(
            user_id=current_user.id,
            action="delete",
            object_type="objet_trouve",
            object_id=objet_id
        )
        session.add(action_log)
        await session.commit()
    # Retourne succès si supprimé en base OU dans le JSON

@app.delete("/api/objets_perdus/{objet_id}")
async def supprimer_objet_perdu(objet_id: str, code: str = Body(...), current_user=Depends(get_current_active_user)):
    if code != SUPPRESSION_CODE:
        logging.warning(f"Tentative de suppression avec code invalide pour {objet_id}")
        raise HTTPException(status_code=403, detail="Code de suppression invalide.")
    objets = load_json("objets_perdus.json")
    objets_new = [o for o in objets if o.get("id") != objet_id]
    if len(objets_new) == len(objets):
        logging.warning(f"Suppression échouée : objet {objet_id} non trouvé.")
        raise HTTPException(status_code=404, detail="Objet perdu non trouvé.")
    save_json("objets_perdus.json", objets_new)
    logging.info(f"Objet perdu supprimé (JSON) : {objet_id}")
    # Suppression dans la base
    async with AsyncSessionLocal() as session:
        obj = await session.get(ObjetPerdu, objet_id)
        if obj:
            await session.delete(obj)
            await session.commit()
            logging.info(f"Objet perdu supprimé (DB) : {objet_id}")
        # Log action
        action_log = ActionLog(
            user_id=current_user.id,
            action="delete",
            object_type="objet_perdu",
            object_id=objet_id
        )
        session.add(action_log)
        await session.commit()
    return {"message": "Objet perdu supprimé."}

@app.post("/api/objets_trouves/rendu")
async def rendre_objet_trouve(
    objet_id: str = Form(...),
    nom: str = Form(...),
    prenom: str = Form(...),
    telephone: str = Form(...),
    email: str = Form(...),
    photo: UploadFile = File(None),
    current_user=Depends(get_current_active_user)
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
        if photo:
            update_data["photo_rendu"] = url_cloudinary
        await session.execute(
            ObjetTrouve.__table__.update().where(ObjetTrouve.__table__.c.id == objet_id).values(**update_data)
        )
        await session.commit()
        # Log action
        action_log = ActionLog(
            user_id=current_user.id,
            action="rendu",
            object_type="objet_trouve",
            object_id=objet_id
        )
        session.add(action_log)
        await session.commit()

    return {"message": "Objet marqué comme rendu", "id": objet_id}

# Route legacy pour compatibilité (clic direct, sans modal)
@app.post("/api/objets_trouves/{objet_id}/rendu")
async def marquer_objet_rendu(objet_id: str, current_user=Depends(get_current_active_user)):
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
        # Log action
        action_log = ActionLog(
            user_id=current_user.id,
            action="rendu",
            object_type="objet_trouve",
            object_id=objet_id
        )
        session.add(action_log)
        await session.commit()
    return {"message": "Statut mis à jour", "id": objet_id}


@app.get("/api/objets_perdus")
async def get_objets_perdus(current_user=Depends(get_current_active_user)):
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
        html.append(f'<tr><td>{escape(obj.get("id",""))}</td><td>{escape(obj.get("description",""))}</td><td>{escape(obj.get("date_rapport",""))}</td><td>{escape(obj.get("infos",""))}</td><td>{img_tag}</td><td>{statut}</td><td>{benef}</td><td>{photo_rendu}</td></tr>')
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
    logging.info("Export HTML généré et envoyé à l'utilisateur.")
    return HTMLResponse(content=content, headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

# --- ADMIN ENDPOINTS ---

from backend.schemas import UserPublic
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import status

@app.get("/api/admin/users", dependencies=[Depends(get_current_admin_user)])
async def list_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        return [UserPublic(
            id=str(u.id),
            username=u.username,
            first_name=u.first_name,
            last_name=u.last_name,
            role=u.role
        ) for u in users]

@app.delete("/api/admin/users/{user_id}", dependencies=[Depends(get_current_admin_user)])
async def delete_user(user_id: str):
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await session.delete(user)
        await session.commit()
        return {"message": "User deleted"}

@app.post("/api/admin/users/{user_id}/role", dependencies=[Depends(get_current_admin_user)])
async def change_user_role(user_id: str, role: str = Body(...)):
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.role = role
        await session.commit()
        return {"message": "Role updated"}

@app.get("/api/admin/logs", dependencies=[Depends(get_current_admin_user)])
async def get_action_logs():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ActionLog))
        logs = result.scalars().all()
        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "action": log.action,
                "object_type": log.object_type,
                "object_id": log.object_id,
                "timestamp": str(log.timestamp)
            }
            for log in logs
        ]

# Servir les images uploadées
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Servir frontend APRÈS les routes API
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")