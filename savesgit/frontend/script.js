let objetsTrouvesCache = [];
let objetsPerdusCache = [];
let rechercheActuelle = '';

// Éléments du DOM pour le pop-up de correspondance
const modalCorrespondance = document.getElementById('modal-correspondance');
const listeCorrespondancesEl = document.getElementById('liste-correspondances');
const modalCorrespondanceCloseBtn = document.getElementById('modal-correspondance-close');
const modalCorrespondanceOkBtn = document.getElementById('modal-correspondance-ok');

// Fonction pour afficher le pop-up de correspondance
function afficherModalCorrespondance(matches) {
  if (!modalCorrespondance || !listeCorrespondancesEl || !matches || matches.length === 0) {
    return;
  }

  listeCorrespondancesEl.innerHTML = ''; // Vider les anciennes correspondances

  matches.forEach(match => {
    const itemDiv = document.createElement('div');
    itemDiv.className = 'correspondance-item';
    // Adapter les champs en fonction de la structure de vos objets 'match'
    // Ceci est un exemple, vous devrez l'ajuster à ce que votre API renvoie
    itemDiv.innerHTML = `
      <strong>Objet: ${escapeHTML(match.description)}</strong>
      <p>Type: ${match.type === 'trouve' ? 'Trouvé' : 'Perdu'}</p>
      ${match.date_rapport ? `<p class="date">Date: ${formatDate(match.date_rapport)}</p>` : ''}
      ${match.nom ? `<p>Déclaré par: ${escapeHTML(match.nom)} ${escapeHTML(match.prenom || '')}</p>` : ''}
      ${match.infos ? `<p>Infos: ${escapeHTML(match.infos)}</p>` : ''}
      <a href="listes.html#objet-${match.id}" target="_blank" style="font-weight:bold; color:#059669;">Voir détails</a>
    `;
    listeCorrespondancesEl.appendChild(itemDiv);
  });

  modalCorrespondance.style.display = 'flex';
}

// Cacher le pop-up de correspondance
function cacherModalCorrespondance() {
  if (modalCorrespondance) {
    modalCorrespondance.style.display = 'none';
  }
}

if (modalCorrespondanceCloseBtn) {
  modalCorrespondanceCloseBtn.addEventListener('click', cacherModalCorrespondance);
}
if (modalCorrespondanceOkBtn) {
  modalCorrespondanceOkBtn.addEventListener('click', cacherModalCorrespondance);
}

function filtrerCartes() {
  const q = rechercheActuelle.trim().toLowerCase();
  document.querySelectorAll('#liste-trouves .carte, #liste-perdus .carte').forEach(carte => {
    const txt = carte.textContent.toLowerCase();
    carte.style.display = (!q || txt.includes(q)) ? '' : 'none';
  });
}

async function chargerListes() {
  const lt = document.getElementById('liste-trouves');
  const lp = document.getElementById('liste-perdus');
  lt.innerHTML = '<div class="loader">Chargement...</div>';
  lp.innerHTML = '<div class="loader">Chargement...</div>';
  try {
    const [trouves, perdus] = await Promise.all([
      fetch('/api/objets_trouves').then(res => res.json()),
      fetch('/api/objets_perdus').then(res => res.json())
    ]);
    objetsTrouvesCache = trouves;
    objetsPerdusCache = perdus;
    lt.innerHTML = '';
    lp.innerHTML = '';
    // Appliquer le filtre de recherche
    const filtre = (obj, type) => {
      const q = rechercheActuelle.trim().toLowerCase();
      if (!q) return true;
      let champs = [obj.description, obj.infos];
      if (type === 'perdu') champs = champs.concat([obj.nom, obj.prenom, obj.telephone, obj.email]);
      return champs.filter(Boolean).some(v => v.toLowerCase().includes(q));
    };
    const trouvesFiltres = trouves.filter(obj => filtre(obj, 'trouve'));
    const perdusFiltres = perdus.filter(obj => filtre(obj, 'perdu'));

    if (trouvesFiltres.length === 0) {
      lt.innerHTML = '<div class="empty">Aucune déclaration d’objet trouvé pour le moment.</div>';
    } else {
      trouvesFiltres.forEach(obj => {
        lt.innerHTML += `
          <div class="carte" tabindex="0">
            ${obj.image ? `<img src="${obj.image}" alt="Photo de l'objet trouvé">` : ''}
            <strong>${escapeHTML(obj.description)}</strong>
            <div class="date">${formatDate(obj.date_rapport)}</div>
            <div class="infos">${escapeHTML(obj.infos || '')}</div>
            <div class="statut-rendu">
              ${obj.rendu ? '<span class="badge-rendu">Rendu au propriétaire</span>' : `<button class="btn-rendu" data-id="${obj.id}">Objet rendu</button>`}
            </div>
            <button class="btn-supprimer" data-type="trouve" data-id="${obj.id}" style="margin-top:8px;background:#e11d48;color:#fff;">Supprimer</button>
          </div>`;
      });
      // Gestion des boutons "Supprimer"
      document.querySelectorAll('.btn-supprimer').forEach(btn => {
        btn.addEventListener('click', async e => {
          const id = btn.getAttribute('data-id');
          const type = btn.getAttribute('data-type');
          const code = prompt('Entrez le mot-clé de suppression :');
          if (code !== '7120') {
            alert('Mot-clé incorrect.');
            return;
          }
          btn.disabled = true;
          btn.textContent = 'Suppression...';
          try {
            const resp = await fetch(`/api/objets_${type === 'trouve' ? 'trouves' : 'perdus'}/${id}`, {
              method: 'DELETE',
              headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
              },
              body: JSON.stringify({ code })
            });
            if (!resp.ok) throw new Error('Erreur API');
            await chargerListes();
          } catch (err) {
            btn.disabled = false;
            btn.textContent = 'Erreur';
          }
        });
      });
      // Gestion du bouton "Objet rendu" (ouvre la modal)
      lt.querySelectorAll('.btn-rendu').forEach(btn => {
        btn.addEventListener('click', e => {
          const id = btn.getAttribute('data-id');
          ouvrirModalRendu(id);
        });
      });

// --- Modal rendu objet ---
let modalRendu = null;
let currentRenduId = null;
let renduStream = null;

function ouvrirModalRendu(objetId) {
  currentRenduId = objetId;
  if (!modalRendu) modalRendu = document.getElementById('modal-rendu');
  if (modalRendu) {
    modalRendu.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    // Reset form
    const form = document.getElementById('form-rendu');
    if (form) form.reset();
    document.getElementById('rendu-photo-preview').src = '';
    document.getElementById('rendu-photo-preview').style.display = 'none';
  }
}
function fermerModalRendu() {
  if (modalRendu) {
    modalRendu.style.display = 'none';
    document.body.style.overflow = '';
    arreterWebcam();
  }
}
document.addEventListener('DOMContentLoaded', () => {
  // Fermer modal sur clic croix ou fond
  document.getElementById('modal-close-rendu').onclick = fermerModalRendu;
  document.getElementById('modal-rendu').onclick = e => { if (e.target.id === 'modal-rendu') fermerModalRendu(); };
  // Aperçu photo bénéficiaire (input file)
  const inputPhoto = document.getElementById('rendu-photo-file');
  const previewPhoto = document.getElementById('rendu-photo-preview');
  if (inputPhoto && previewPhoto) {
    inputPhoto.addEventListener('change', () => {
      const file = inputPhoto.files && inputPhoto.files[0];
      if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = e => {
          previewPhoto.src = e.target.result;
          previewPhoto.style.display = 'block';
        };
        reader.readAsDataURL(file);
      } else {
        previewPhoto.src = '';
        previewPhoto.style.display = 'none';
      }
    });
  }
  // Soumission formulaire
  document.getElementById('form-rendu').onsubmit = async function(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    formData.append('objet_id', currentRenduId);
    // Ajoute la photo si présente (input file)
    const inputPhoto = document.getElementById('rendu-photo-file');
    if (inputPhoto && inputPhoto.files && inputPhoto.files[0]) {
      formData.set('photo', inputPhoto.files[0]);
    }
    try {
      const resp = await fetch('/api/objets_trouves/rendu', { method: 'POST', body: formData });
      if (!resp.ok) throw new Error('Erreur API');
      fermerModalRendu();
      chargerListes();
    } catch (err) {
      alert('Erreur lors de l\'enregistrement : ' + err.message);
    }
  };
});
// (Suppression de la fonction demarrerWebcam car plus utilisée)
function arreterWebcam() {
  const video = document.getElementById('webcam-rendu');
  if (renduStream) {
    renduStream.getTracks().forEach(track => track.stop());
    renduStream = null;
  }
  if (video) video.style.display = 'none';
}
function prendrePhotoWebcam() {
  const video = document.getElementById('webcam-rendu');
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const dataUrl = canvas.toDataURL('image/png');
  document.getElementById('rendu-photo-preview').src = dataUrl;
  document.getElementById('rendu-photo-preview').style.display = 'block';
}
function dataURLtoBlob(dataurl) {
  var arr = dataurl.split(','), mime = arr[0].match(/:(.*?);/)[1], bstr = atob(arr[1]), n = bstr.length, u8arr = new Uint8Array(n);
  while(n--){ u8arr[n] = bstr.charCodeAt(n); }
  return new Blob([u8arr], {type:mime});
}

    }
    if (perdusFiltres.length === 0) {
      lp.innerHTML = '<div class="empty">Aucune déclaration d’objet perdu pour le moment.</div>';
    } else {
      perdusFiltres.forEach(obj => {
        const carte = document.createElement('div');
        carte.className = 'carte';
        carte.tabIndex = 0;
        if (!filtre(obj, 'perdu')) {
          carte.style.display = 'none';
        }
        lp.appendChild(carte);
        carte.innerHTML = `
          <strong>${escapeHTML(obj.description)}</strong>
          <div class="date">${formatDate(obj.date_rapport)}</div>
          <div class="infos">${escapeHTML(obj.infos || '')}</div>
          <div class="contact-perdu">
            <span><b>Nom:</b> ${escapeHTML(obj.nom || '')}</span><br/>
            <span><b>Prénom:</b> ${escapeHTML(obj.prenom || '')}</span><br/>
            <span><b>Téléphone:</b> <a href="tel:${escapeHTML(obj.telephone || '')}">${escapeHTML(obj.telephone || '')}</a></span><br/>
            <span><b>Email:</b> <a href="mailto:${escapeHTML(obj.email || '')}">${escapeHTML(obj.email || '')}</a></span>
          </div>
          <button class="btn-supprimer" data-type="perdu" data-id="${obj.id}" style="margin-top:8px;background:#e11d48;color:#fff;">Supprimer</button>
        `;
      });
    }
  } catch (e) {
    lt.innerHTML = '<div class="feedback">Erreur lors du chargement.</div>';
    lp.innerHTML = '<div class="feedback">Erreur lors du chargement.</div>';
  }
}

function escapeHTML(str) {
  return (str || '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&#39;'
  }[c]));
}

function formatDate(dt) {
  if (!dt) return '';
  try {
    const d = new Date(dt);
    return d.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return dt;
  }
}

const feedbackTrouve = document.getElementById('feedback-trouve');
const feedbackPerdu = document.getElementById('feedback-perdu');

function showFeedback(el, msg, success = false) {
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle('success', success);
  if (!success) el.focus();
}

// Validation objets trouvés
const formTrouve = document.getElementById('form-trouve');
const inputPhoto = document.getElementById('photo');
const previewPhoto = document.getElementById('preview-photo');
if (inputPhoto && previewPhoto) {
  inputPhoto.addEventListener('change', () => {
    const file = inputPhoto.files && inputPhoto.files[0];
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = e => {
        previewPhoto.src = e.target.result;
        previewPhoto.style.display = 'block';
      };
      reader.readAsDataURL(file);
    } else {
      previewPhoto.src = '';
      previewPhoto.style.display = 'none';
    }
  });
}

if (formTrouve) {
  formTrouve.addEventListener('submit', async (e) => {
    e.preventDefault();
    feedbackTrouve.textContent = '';
    const formData = new FormData(e.target);
    const desc = formData.get('description')?.trim();
    if (!desc || desc.length < 3) {
      showFeedback(feedbackTrouve, 'Description trop courte.');
      return;
    }
    const file = formData.get('photo');
    if (!file || !file.name.match(/\.(jpg|jpeg|png|gif)$/i)) {
      showFeedback(feedbackTrouve, 'Format de photo non autorisé.');
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      showFeedback(feedbackTrouve, 'Photo trop volumineuse (max 20 Mo, HD autorisé).');
      return;
    }
    try {
      const resp = await fetch('/api/objets_trouves', { method: 'POST', body: formData });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Erreur inconnue');
      showFeedback(feedbackTrouve, 'Objet trouvé déclaré avec succès !', true);
      e.target.reset();
      previewPhoto.style.display = 'none';
      const responseData = data; // resp.json() est déjà assigné à data ici
      // Vérifier les correspondances potentielles
      if (responseData.matches && responseData.matches.length > 0) {
        afficherModalCorrespondance(responseData.matches);
      }
      chargerListes();
    } catch (err) {
      showFeedback(feedbackTrouve, err.message || 'Erreur lors de la déclaration.');
    }
  });
}

// Validation objets perdus
const formPerdu = document.getElementById('form-perdu');
if (formPerdu) {
  formPerdu.addEventListener('submit', async (e) => {
    e.preventDefault();
    feedbackPerdu.textContent = '';
    const data = Object.fromEntries(new FormData(e.target).entries());
    // Vérification basique des champs obligatoires
    if (!data.description || data.description.trim().length < 3) {
      showFeedback(feedbackPerdu, 'Description trop courte.');
      return;
    }
    if (!data.nom || !data.prenom || !data.telephone || !data.email) {
      showFeedback(feedbackPerdu, 'Tous les champs de contact sont obligatoires.');
      return;
    }
    try {
      const resp = await fetch('/api/objets_perdus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      const res = await resp.json();
      if (!resp.ok) throw new Error(res.detail || 'Erreur inconnue');
      showFeedback(feedbackPerdu, 'Objet perdu déclaré avec succès !', true);
      e.target.reset();
      // Vérifier les correspondances potentielles
      const responseData = res; // resp.json() est déjà assigné à res ici
      if (responseData.matches && responseData.matches.length > 0) {
        afficherModalCorrespondance(responseData.matches);
      }
      chargerListes();
    } catch (err) {
      showFeedback(feedbackPerdu, err.message || 'Erreur lors de la déclaration.');
    }
  });
}

// Gestion des onglets
const tabTrouves = document.getElementById('tab-trouves');
const tabPerdus = document.getElementById('tab-perdus');
const panelTrouves = document.getElementById('tabpanel-trouves');
const panelPerdus = document.getElementById('tabpanel-perdus');

function switchSubTab(tab) {
  if (!tabTrouves || !tabPerdus || !panelTrouves || !panelPerdus) return;
  if (tab === 'trouves') {
    tabTrouves.classList.add('active');
    tabTrouves.setAttribute('aria-selected', 'true');
    panelTrouves.classList.add('active');
    panelTrouves.style.display = '';
    tabPerdus.classList.remove('active');
    tabPerdus.setAttribute('aria-selected', 'false');
    panelPerdus.classList.remove('active');
    panelPerdus.style.display = 'none';
    tabTrouves.focus();
  } else {
    tabPerdus.classList.add('active');
    tabPerdus.setAttribute('aria-selected', 'true');
    panelPerdus.classList.add('active');
    panelPerdus.style.display = '';
    tabTrouves.classList.remove('active');
    tabTrouves.setAttribute('aria-selected', 'false');
    panelTrouves.classList.remove('active');
    panelTrouves.style.display = 'none';
    tabPerdus.focus();
  }
}

if (tabTrouves && tabPerdus) {
  tabTrouves.addEventListener('click', () => switchSubTab('trouves'));
  tabPerdus.addEventListener('click', () => switchSubTab('perdus'));
}

window.onload = () => {
  if (document.getElementById('liste-trouves') && document.getElementById('liste-perdus')) {
    chargerListes();
  }
  if (tabTrouves && tabPerdus) switchSubTab('trouves');

  // Recherche dynamique : masque les cartes non correspondantes
  const inputRecherche = document.getElementById('search-objets');
  if (inputRecherche) {
    inputRecherche.addEventListener('input', e => {
      rechercheActuelle = inputRecherche.value;
      filtrerCartes();
    });
  }

  // Export PDF
  const btnExport = document.getElementById('btn-export-pdf');
  if (btnExport) {
    btnExport.addEventListener('click', () => {
      const section = document.querySelector('.tab-section');
      if (!section) return;
      html2pdf().from(section).set({
        margin: 0.5,
        filename: 'objets-festival.pdf',
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
      }).save();
    });
  }

  // Export CSV
  const btnExportCsv = document.getElementById('btn-export-csv');
  if (btnExportCsv) {
    btnExportCsv.addEventListener('click', async () => {
      btnExportCsv.disabled = true;
      btnExportCsv.textContent = 'Export...';
      try {
        const resp = await fetch('/api/export');
        if (!resp.ok) throw new Error('Erreur lors de l’export');
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        // Récupère le nom du fichier depuis l’en-tête si possible
        const dispo = resp.headers.get('Content-Disposition');
        let filename = 'export_objets.csv';
        if (dispo) {
          const match = dispo.match(/filename=([^;]+)/);
          if (match) filename = match[1];
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
          window.URL.revokeObjectURL(url);
          a.remove();
        }, 100);
      } catch (e) {
        alert('Erreur lors de l’export CSV');
      } finally {
        btnExportCsv.disabled = false;
        btnExportCsv.textContent = 'Exporter (CSV)';
      }
    });
  }
};

