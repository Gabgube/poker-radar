// --- 1. Configuration initiale ---

const TYPES = {
  bar:       { nom: "Bar Red Cactus", couleur: "#dc2626" }, // Rouge jeton
  casino:    { nom: "Casino", couleur: "#18181b" },         // Noir jeton
  caritatif: { nom: "Tournoi caritatif", couleur: "#1d4ed8" } // Bleu jeton
};

const OFFRES_POKER = {
  cash: "Cash Game",
  tournois: "Tournois",
  les_deux: "Cash Game & Tournois",
  a_verifier: "À vérifier"
};

const esc = s => String(s || '').replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&quot;","'":"&#39;"}[c]));

let lieux = [];

// --- 2. Fonctions d'affichage HTML (Boutons et Détails) ---

// Utilitaire pour copier le téléphone tout en déclenchant l'appel
function composerOuCopier(e, tel) {
  // Copie dans le presse-papier en arrière-plan
  if (navigator.clipboard && tel) {
    navigator.clipboard.writeText(tel).catch(() => {});
  }
}

function boutonInscription(l) {
  let boutonsHtml = "";

  // 1. Cas particulier des Casinos : Gestion du Téléphone
  if (l.type === "casino" && l.telephone) {
    // Nettoyage du numéro pour l'attribut href (ex: "01 23 45 67 89" -> "0123456789")
    const telClean = String(l.telephone).replace(/[^\d+]/g, '');
    const telAffiche = esc(l.telephone);

    boutonsHtml += `<a class="btn btn-tel" href="tel:${telClean}" onclick="composerOuCopier(event, '${telClean}')" title="Appeler ou copier le numéro"> ${telAffiche}</a>`;
  }
  // 2. Bouton d'information / réservation standard
  else if (l.inscription && l.inscription.valeur) {
    const libelle = l.inscription.libelle || (l.type === "caritatif" ? "Voir le tournoi" : "En savoir plus");
    boutonsHtml += `<a class="btn" href="${esc(l.inscription.valeur)}" target="_blank" rel="noopener noreferrer">${esc(libelle)}</a>`;
  } 
  else if (l.url) {
    let libelle = "En savoir plus";
    if (l.type === "caritatif") libelle = "Voir le tournoi";
    else if (l.type === "bar") libelle = "Voir la page du bar";

    boutonsHtml += `<a class="btn" href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(libelle)}</a>`;
  } 
  else if (l.type === "bar") {
    const urlBase = "https://poker.redcactus.fr"; 
    const rawId = String(l.id).replace(/^rc_/, '');
    const url = rawId ? `${urlBase}/bar/${rawId}` : urlBase;
    boutonsHtml += `<a class="btn" href="${url}" target="_blank" rel="noopener noreferrer">Voir la page du bar</a>`;
  }

  // 3. Bouton GPS "Y aller" Google Maps
  if (typeof l.lat === "number" && typeof l.lng === "number") {
    const urlMaps = `https://www.google.com/maps/dir/?api=1&destination=${l.lat},${l.lng}`;
    boutonsHtml += ` <a class="btn btn-maps" href="${urlMaps}" target="_blank" rel="noopener noreferrer">Y aller</a>`;
  }

  return boutonsHtml;
}

function formerDateFr(dateIso) {
  if (!dateIso || typeof dateIso !== "string" || !dateIso.includes("-")) return dateIso || "";
  const [a, m, j] = dateIso.split('-');
  return `${j}/${m}/${a}`;
}

function details(l) {
  const t = TYPES[l.type] || TYPES.bar;
  let badges = `<span class="tag" style="--c:${t.couleur}">${esc(t.nom)}</span>`;
  
  if (l.isNew) {
    badges += ` <span class="tag" style="--c:#2563eb">Nouveau</span>`;
  }

  // Badge d'offre Poker
  if (l.poker && OFFRES_POKER[l.poker]) {
    badges += ` <span class="tag tag-poker" style="--c:#059669">${esc(OFFRES_POKER[l.poker])}</span>`;
  }

  // 1. Gestion de la date / calendrier
  let infoDate = "Tournois réguliers";
  if (l.type === "caritatif") {
    infoDate = l.date ? formerDateFr(l.date) : "Date inconnue";
  } else if (l.date) {
    infoDate = l.date;
  }
  if (l.type === "casino") {
    infoDate = "Voir les dates sur le site";
  }

  // 2. Gestion du prix
  let infoPrix = "";
  if (l.type === "caritatif") {
    infoPrix = l.prix || (l.gratuit ? "Gratuit" : "Payant");
  } else {
    // Red Cactus et Casinos : "Gratuit" ou "Payant" selon l.gratuit
    infoPrix = l.gratuit ? "Gratuit" : "Payant";
  }

  return `${badges}
    ${l.adresse ? `<p class="meta">${esc(l.adresse)}</p>` : ""}
    <p class="meta">${esc(infoDate)} · ${esc(infoPrix)}</p>
    ${boutonInscription(l)}`;
}

// --- 3. Initialisation Leaflet ---

const LIMITES_FRANCE = [[41.3, -5.2], [51.1, 9.6]];

const map = L.map("map").fitBounds(LIMITES_FRANCE);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const layer = L.markerClusterGroup({
  iconCreateFunction: function(cluster) {
    const count = cluster.getChildCount();
    return L.divIcon({
      html: `<div><span>${count}</span></div>`,
      className: 'custom-cluster',
      iconSize: [40, 40],
      iconAnchor: [20, 20]
    });
  }
}).addTo(map);

// --- 4. Fonction principale de filtrage et d'affichage ---

function afficher() {
  const typeSelect = document.getElementById("f-type");
  const prixSelect = document.getElementById("f-prix");
  const pokerSelect = document.getElementById("f-poker");

  const type = typeSelect ? typeSelect.value : "";
  const prix = prixSelect ? prixSelect.value : "";
  const poker = pokerSelect ? pokerSelect.value : "";

  const filtres = lieux.filter(l => {
    // 1. Filtre par type
    if (type && l.type !== type) {
      return false;
    }

    // 2. Filtre par tarif
    if (prix) {
      const estGratuit = (prix === "gratuit");
      if (Boolean(l.gratuit) !== estGratuit) {
        return false;
      }
    }

    // 3. Filtre universel par format de poker
    if (poker) {
      if (poker === "cash" && l.poker !== "cash" && l.poker !== "les_deux") {
        return false;
      }
      if (poker === "tournois" && l.poker !== "tournois" && l.poker !== "les_deux") {
        return false;
      }
      if (poker === "les_deux" && l.poker !== "les_deux") {
        return false;
      }
    }

    return true;
  });

  // Mise à jour de la carte et de la liste
  layer.clearLayers();
  const list = document.getElementById("list");
  if (list) list.innerHTML = "";

  const countEl = document.getElementById("count");
  if (countEl) {
    countEl.textContent = filtres.length + (filtres.length > 1 ? " lieux trouvés" : " lieu trouvé");
  }

  filtres.forEach(l => {
    const t = TYPES[l.type] || TYPES.bar;

    const icon = L.divIcon({
      className: "",
      html: `<div class="chip" style="--c:${t.couleur}"></div>`,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      popupAnchor: [0, -15]
    });

    const marker = L.marker([l.lat, l.lng], { icon, title: l.nom })
      .bindPopup(`<strong>${esc(l.nom)}</strong><br>${details(l)}`)
      .addTo(layer);

    if (list) {
      const card = document.createElement("div");
      card.className = "card";
      card.tabIndex = 0;
      card.style.setProperty("--c", t.couleur);
      card.innerHTML = `<h2>${esc(l.nom)}</h2>${details(l)}`;

      const ouvrir = () => { map.setView([l.lat, l.lng], 12); marker.openPopup(); };
      card.addEventListener("click", e => { if (!e.target.closest("a")) ouvrir(); });
      card.addEventListener("keydown", e => { if (e.key === "Enter" && !e.target.closest("a")) ouvrir(); });

      list.appendChild(card);
    }
  });

  if (filtres.length) {
    map.fitBounds(LIMITES_FRANCE, { padding: [20, 20] });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("f-type")?.addEventListener("change", afficher);
  document.getElementById("f-prix")?.addEventListener("change", afficher);
  document.getElementById("f-poker")?.addEventListener("change", afficher);
});

// --- 5. Chargement des données ---

const chargerJSON = async (url) => {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (err) {
    console.error(`Erreur sur ${url}:`, err);
    return [];
  }
};

Promise.all([
  chargerJSON("redcactus.json"),
  chargerJSON("casinos.json"),
  chargerJSON("caritatifs.json")
]).then(([dataRC, dataCasinos, dataCaritatifs]) => {

  const aujourdhui = new Date().toISOString().split('T')[0];

  // 1. Red Cactus
  const rawFeatures = dataRC.features || (Array.isArray(dataRC) ? dataRC : []);
  const redCactusFormates = rawFeatures
    .filter(f => f && typeof f.lat === "number" && typeof f.lng === "number");

  // 2. Casinos
  const casinosValides = dataCasinos
    .filter(c => typeof c.lat === "number" && typeof c.lng === "number");

  // 3. Tournois caritatifs
  const caritatifsValides = dataCaritatifs
    .filter(c => typeof c.lat === "number" && typeof c.lng === "number")
    .filter(c => !c.date || c.date >= aujourdhui)

  // Fusion globale
  lieux = [...redCactusFormates, ...casinosValides, ...caritatifsValides];

  afficher();
}).catch(err => {
  console.error("Erreur globale :", err);
});

// --- 6. Gestion de la modale "Proposer un tournoi" ---

document.addEventListener("DOMContentLoaded", () => {
  const URL_FORMULAIRE = "https://docs.google.com/forms/d/e/1FAIpQLSd1D3HN-joemrjvV5pYSA-wbXtF3-YDajahuXe4At9rseTJIA/viewform?usp=dialog";

  const dlg = document.getElementById("dlg-tournoi");
  const frame = document.getElementById("dlg-frame");
  const lien = document.getElementById("dlg-lien");
  const btnProposer = document.getElementById("btn-proposer");
  const btnClose = document.getElementById("dlg-close");

  const valide = /^https:\/\/(docs\.google\.com\/forms\/|tally\.so\/)/.test(URL_FORMULAIRE);

  if (btnProposer && dlg) {
    btnProposer.addEventListener("click", function () {
      if (valide) {
        if (frame) { frame.src = URL_FORMULAIRE; frame.hidden = false; }
        if (lien) { lien.href = URL_FORMULAIRE; }
      }
      dlg.showModal();
    });
  }

  if (btnClose && dlg) {
    btnClose.addEventListener("click", function () {
      dlg.close();
    });
  }
});