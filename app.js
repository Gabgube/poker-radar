// --- 1. Configuration initiale ---

// Dictionnaire des types de lieux et leurs couleurs
const TYPES = {
  bar:       { nom: "Bar Red Cactus", couleur: "#c8372d" },
  redcactus: { nom: "Bar Red Cactus", couleur: "#c8372d" },
  casino:    { nom: "Casino", couleur: "#16211c" },
  caritatif: { nom: "Tournoi caritatif", couleur: "#2e7d5b" }
};

// Fonction de sécurité pour éviter les failles XSS
const esc = s => String(s || '').replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

// Tableau global qui stockera nos données JSON
let lieux = [];

// --- 2. Fonctions d'affichage HTML (Bouton et Détails) ---

function boutonInscription(l) {
  // Remets ton vrai lien Red Cactus à la place des points de suspension
  const urlBase = "..."; 
  const url = l.id ? `${urlBase}/bar/${l.id}` : urlBase;
  return `<a class="btn" href="${url}" target="_blank" rel="noopener noreferrer">Voir la page du bar</a>`;
}

function details(l) {
  const t = TYPES[l.type] || { nom: "Bar Red Cactus", couleur: "#c8372d" };
  let badges = `<span class="tag" style="--c:${t.couleur}">${esc(t.nom)}</span>`;
  
  // Badge Nouveau uniquement (le Premium a été retiré)
  if (l.isNew) {
    badges += `<span class="tag" style="--c:#2563eb">Nouveau</span>`;
  }

  return `${badges}
    ${l.adresse ? `<p class="meta">${esc(l.adresse)}</p>` : ""}
    <p class="meta">${esc(l.quand || "Tournois réguliers")} · ${esc(l.prix || "Gratuit")}</p>
    ${boutonInscription(l)}`;
}

// --- 3. Initialisation de la carte Leaflet ---

// Centrage sur la France
const map = L.map("map").setView([46.6, 2.5], 6);

// Fond de carte
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 19,
  attribution: 'Tiles &copy; Esri &mdash; Source: Esri, HERE, Garmin, OpenStreetMap contributors'
}).addTo(map);

// CRÉATION DU GROUPE DE CLUSTERS (Regroupement des points)
const layer = L.markerClusterGroup().addTo(map);

// --- 4. Fonction principale de filtrage et d'affichage ---

function afficher() {
  // Récupération de la valeur des filtres
  const type = document.getElementById("f-type").value;
  const prix = document.getElementById("f-prix").value;
  
  // Filtrage des données
  const filtres = lieux.filter(l =>
    typeof l.lat === "number" && typeof l.lng === "number" &&
    (!type || l.type === type) &&
    (!prix || (prix === "gratuit") === l.gratuit)
  );

  // Nettoyage de la carte et de la liste avant mise à jour
  layer.clearLayers();
  const list = document.getElementById("list");
  list.innerHTML = "";
  document.getElementById("count").textContent =
    filtres.length + (filtres.length > 1 ? " lieux trouvés" : " lieu trouvé");

  // Création des marqueurs et des cartes
  filtres.forEach(l => {
    const t = TYPES[l.type] || { couleur: "#c8372d" };
    
    // Création de l'icône personnalisée
    const icon = L.divIcon({
      className: "",
      html: `<div class="chip" style="--c:${t.couleur}"></div>`,
      iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -15]
    });
    
    // Ajout du marqueur au groupe de clusters
    const marker = L.marker([l.lat, l.lng], { icon, title: l.nom })
      .bindPopup(`<strong>${esc(l.nom)}</strong><br>${details(l)}`)
      .addTo(layer);

    // Création de la carte dans le panneau latéral
    const card = document.createElement("div");
    card.className = "card";
    card.tabIndex = 0;
    card.style.setProperty("--c", t.couleur);
    card.innerHTML = `<h2>${esc(l.nom)}</h2>${details(l)}`;
    
    // Action au clic sur une carte : zoomer et ouvrir la popup
    const ouvrir = () => { map.setView([l.lat, l.lng], 12); marker.openPopup(); };
    card.addEventListener("click", e => { if (!e.target.closest("a")) ouvrir(); });
    card.addEventListener("keydown", e => { if (e.key === "Enter" && !e.target.closest("a")) ouvrir(); });
    
    list.appendChild(card);
  });

  // Ajustement automatique de la vue de la carte pour tout englober
  if (filtres.length) {
    map.fitBounds(L.latLngBounds(filtres.map(l => [l.lat, l.lng])), { padding: [50, 50], maxZoom: 10 });
  }
}

// --- 5. Écouteurs d'événements et chargement des données ---

document.getElementById("f-type").addEventListener("change", afficher);
document.getElementById("f-prix").addEventListener("change", afficher);

// Récupération du fichier JSON
// Fonction pour charger et formater le GeoJSON complexe de Red Cactus
const fetchRedCactus = () => 
  fetch("markers.json")
    .then(r => r.ok ? r.json() : { features: [] })
    .then(data => {
      const rawFeatures = data.features || (Array.isArray(data) ? data : []);
      return rawFeatures
        .filter(f => {
          const t = f.properties ? f.properties.type : f.type;
          return t !== 'semi-final' && t !== 'pre-main-final';
        })
        .map(f => {
          if (f.geometry && f.geometry.coordinates) {
            const [lng, lat] = f.geometry.coordinates;
            const props = f.properties || {};
            return {
              id: f.id || props.id,
              nom: props.name || props.nom || "Établissement",
              type: props.type || "bar",
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
        }).filter(Boolean);
    })
    .catch(() => []);

// Fonction pour charger tes propres fichiers simples (casinos, caritatifs)
const fetchFichierSimple = (fichier) =>
  fetch(fichier)
    .then(r => r.ok ? r.json() : [])
    .catch(() => []);

// Chargement simultané de toutes les sources
Promise.all([
  fetchRedCactus(),
  fetchFichierSimple("casinos.json"),
  fetchFichierSimple("caritatifs.json")
]).then(([lieuxRedCactus, lieuxCasinos,lieuxCaritatifs]) => {
  
  // Fusion de tous les tableaux en un seul
  lieux = [...lieuxRedCactus, ...lieuxCasinos,...lieuxCaritatifs];
  
  // Affichage sur la carte
  afficher();

}).catch(err => {
  console.error(err);
  document.getElementById("count").textContent = "Erreur lors du chargement des données.";
});