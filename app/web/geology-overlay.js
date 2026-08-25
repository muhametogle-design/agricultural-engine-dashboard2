/* Reusable Somalia geology overlay for GIS and SWALIM/Dawaad Leaflet maps. */
(function (global) {
  "use strict";
  const COLORS = { limestone: "#647f9f", sandstone: "#c58a45", basalt: "#8f3042", volcanic: "#8f3042", alluvium: "#b7a66a", basement: "#596579" };
  const colorFor = value => {
    const text = String(value || "").toLowerCase();
    for (const [key, color] of Object.entries(COLORS)) if (text.includes(key)) return color;
    return "#64748b";
  };
  async function addTo(map, options) {
    options = options || {};
    const urls = options.urls || ["/static/data/somalia_geology.geojson", "/somalia_geology.geojson"];
    let data;
    for (const url of urls) {
      try { const response = await fetch(url); if (response.ok) { data = await response.json(); break; } } catch (_) {}
    }
    if (!data) throw new Error("Somalia geology GeoJSON is unavailable");
    let selected = null;
    const baseStyle = feature => ({ color: "#334155", weight: 1, fillColor: colorFor(feature.properties && feature.properties.lithology), fillOpacity: 0.45 });
    const group = L.geoJSON(data, { style: baseStyle, onEachFeature(feature, layer) {
      const source = feature.properties || {};
      const properties = {
        formation_name: source.formation_name || source.formation || source.name || "Unnamed formation",
        lithology: source.lithology || "Not specified",
        era: source.era || source.stratigraphic_era || source.age || "Not specified",
        permeability_class: source.permeability_class || "Moderate",
        groundwater_potential: source.groundwater_potential || "Moderate"
      };
      layer.bindPopup(`<div style="font-family:system-ui;min-width:200px"><b>${properties.formation_name}</b><br>Lithology: ${properties.lithology}<br>Era: ${properties.era}<br>Permeability: ${properties.permeability_class}<br>Groundwater Potential: ${properties.groundwater_potential}</div>`);
      layer.on("mouseover", () => { if (layer !== selected) layer.setStyle({ color: "#94a3b8", weight: 2, fillOpacity: 0.55 }); });
      layer.on("mouseout", () => { if (layer !== selected) layer.setStyle(baseStyle(feature)); });
      layer.on("click", () => {
        if (selected) group.resetStyle(selected);
        selected = layer;
        layer.setStyle({ color: "#10b981", weight: 4, fillOpacity: 0.58 });
        layer.bringToFront();
        localStorage.setItem("gis_selected_geology", JSON.stringify(properties));
        global.dispatchEvent(new CustomEvent("gis:geology-selected", { detail: properties }));
        if (options.onSelect) options.onSelect(properties, layer);
      });
    }}).addTo(map);
    return group;
  }
  global.SomaliaGeology = { addTo, colorFor };
})(window);
