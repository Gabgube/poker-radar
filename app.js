// --- 1. Configuration initiale ---

const TYPES = {
  bar:       { nom: "Bar Red Cactus", couleur: "#c8372d" },
  casino:    { nom: "Casino", couleur: "#16211c" },
  caritatif: { nom: "Tournoi caritatif", couleur: "#2e7d5b" }
};

const esc = s => String(s || '').replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&quot;","'":"&#39;"}[c]));

let lieux = [];

// --- 2. Fonctions d'affichage HTML (Boutons et Détails) ---

function boutonInscription(l) {
  let boutonsHtml = "";

  // 1. Bouton principal d'information / réservation
  if (l.inscription && l.inscription.valeur) {
    const libelle = l.inscription.libelle || (l.type === "caritatif" ? "Voir le tournoi" : "En savoir plus");
    boutonsHtml += `<a class="btn" href="${esc(l.inscription.valeur)}" target="_blank" rel="noopener noreferrer">${esc(libelle)}</a>`;
  } else if (l.url) {
    let libelle = "En savoir plus";
    if (l.type === "casino") libelle = "Voir le casino";
    else if (l.type === "caritatif") libelle = "Voir le tournoi";
    else libelle = "Voir la page du bar";

    boutonsHtml += `<a class="btn" href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(libelle)}</a>`;
  } else if (l.type === "bar") {
    const urlBase = "https://poker.redcactus.fr"; 
    const rawId = String(l.id).replace(/^rc_/, '');
    const url = rawId ? `${urlBase}/bar/${rawId}` : urlBase;
    boutonsHtml += `<a class="btn" href="${url}" target="_blank" rel="noopener noreferrer">Voir la page du bar</a>`;
  }

  // 2. Bouton GPS "Y aller" Google Maps
  if (typeof l.lat === "number" && typeof l.lng === "number") {
    const urlMaps = `https://www.google.com/maps/dir/?api=1&destination=${l.lat},${l.lng}`;
    boutonsHtml += ` <a class="btn btn-maps" href="${urlMaps}" target="_blank" rel="noopener noreferrer"> Y aller</a>`;
  }

  return boutonsHtml;
}

function details(l) {
  const t = TYPES[l.type] || TYPES.bar;
  let badges = `<span class="tag" style="--c:${t.couleur}">${esc(t.nom)}</span>`;
  
  if (l.isNew) {
    badges += `<span class="tag" style="--c:#2563eb">Nouveau</span>`;
  }

  return `${badges}
    ${l.adresse ? `<p class="meta">${esc(l.adresse)}</p>` : ""}
    <p class="meta">${esc(l.quand || "Tournois réguliers")} · ${esc(l.prix || "Gratuit")}</p>
    ${boutonInscription(l)}`;
}

// --- 3. Initialisation Leaflet ---

// Coordonnées de cadrage pour la France métropolitaine
const LIMITES_FRANCE = [[41.3, -5.2], [51.1, 9.6]];

const map = L.map("map").fitBounds(LIMITES_FRANCE);

L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 19,
  attribution: 'Tiles &copy; Esri &mdash; Source: Esri, HERE, Garmin, OpenStreetMap contributors'
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

  const type = typeSelect ? typeSelect.value : "";
  const prix = prixSelect ? prixSelect.value : "";
  
  const filtres = lieux.filter(l => {
    let correspondType = true;
    if (type) {
      correspondType = (l.type === type);
    }

    let correspondPrix = true;
    if (prix) {
      correspondPrix = (prix === "gratuit") === Boolean(l.gratuit);
    }

    return correspondType && correspondPrix;
  });

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
      iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -15]
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
    .filter(f => {
      const t = f.properties ? f.properties.type : f.type;
      return t !== 'semi-final' && t !== 'pre-main-final';
    })
    .map(f => {
      if (f.geometry && f.geometry.coordinates) {
        const [lng, lat] = f.geometry.coordinates;
        const props = f.properties || {};
        return {
          id: `rc_${f.id || props.id}`,
          nom: props.name || props.nom || "Établissement",
          type: "bar",
          lat: lat,
          lng: lng,
          isNew: props.isNew || false,
          adresse: props.adresse || props.address || "",
          quand: props.quand || "Tournois réguliers",
          prix: props.prix || "Gratuit",
          gratuit: true,
          url: props.url || ""
        };
      }
      return null;
    })
    .filter(f => f && typeof f.lat === "number" && typeof f.lng === "number");

  // 2. Casinos
  const casinosValides = dataCasinos
    .filter(c => typeof c.lat === "number" && typeof c.lng === "number")
    .map(c => ({ ...c, type: "casino", gratuit: false }));

  // 3. Tournois caritatifs (avec filtre de date d'expiration)
  const caritatifsValides = dataCaritatifs
    .filter(c => typeof c.lat === "number" && typeof c.lng === "number")
    .filter(c => !c.date || c.date >= aujourdhui) // Élimine les tournois passés
    .map(c => ({ ...c, type: "caritatif" }));

  // Fusion globale
  lieux = [...redCactusFormates, ...casinosValides, ...caritatifsValides];

  afficher();
}).catch(err => {
  console.error("Erreur globale :", err);
});