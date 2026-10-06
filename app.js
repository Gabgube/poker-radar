// --- 1. Configuration initiale ---

const TYPES = {
  bar:        { nom: "Bar Red Cactus", couleur: "#c8372d" },
  casino:     { nom: "Casino", couleur: "#16211c" },
  caritatif:  { nom: "Tournoi caritatif", couleur: "#2e7d5b" }
};

const esc = s => String(s || '').replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

let lieux = [];

// --- 2. Fonctions d'affichage HTML (Bouton et Détails) ---

function boutonInscription(l) {
  // Lien spécifique (ex: billetterie caritatif)
  if (l.inscription && l.inscription.valeur) {
    return `<a class="btn" href="${esc(l.inscription.valeur)}" target="_blank" rel="noopener noreferrer">${esc(l.inscription.libelle || "En savoir plus")}</a>`;
  }
  
  // Lien par défaut pour Red Cactus
  const urlBase = "https://poker.redcactus.fr"; 
  const rawId = String(l.id).replace(/^rc_/, '');
  const url = rawId ? `${urlBase}/bar/${rawId}` : urlBase;
  return `<a class="btn" href="${url}" target="_blank" rel="noopener noreferrer">Voir la page du bar</a>`;
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

const map = L.map("map").setView([46.6, 2.5], 6);

L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 19,
  attribution: 'Tiles &copy; Esri &mdash; Source: Esri, HERE, Garmin, OpenStreetMap contributors'
}).addTo(map);

const layer = L.markerClusterGroup().addTo(map);

// --- 4. Fonction principale de filtrage et d'affichage ---

function afficher() {
  const typeSelect = document.getElementById("f-type");
  const prixSelect = document.getElementById("f-prix");

  const type = typeSelect ? typeSelect.value : "";
  const prix = prixSelect ? prixSelect.value : "";
  
  const filtres = lieux.filter(l => {
    let correspondType = true;
    if (type) {
      if (type === "bar") {
        correspondType = (l.type === "bar");
      } else {
        correspondType = (l.type === type);
      }
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
    map.fitBounds(L.latLngBounds(filtres.map(l => [l.lat, l.lng])), { padding: [50, 50], maxZoom: 10 });
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

  // 1. Red Cactus (GeoJSON conversion)
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
          adresse: props.adresse || "",
          quand: props.quand || "Tournois réguliers",
          prix: props.prix || "Gratuit",
          gratuit: true
        };
      }
      return null;
    })
    .filter(f => f && typeof f.lat === "number" && typeof f.lng === "number");

  // 2. Casinos & Caritatifs (filtrage des coordonnées uniquement)
  const casinosValides = dataCasinos.filter(c => typeof c.lat === "number" && typeof c.lng === "number");
  const caritatifsValides = dataCaritatifs.filter(c => typeof c.lat === "number" && typeof c.lng === "number");

  // Fusion globale
  lieux = [...redCactusFormates, ...casinosValides, ...caritatifsValides];

  afficher();
}).catch(err => {
  console.error("Erreur globale :", err);
});