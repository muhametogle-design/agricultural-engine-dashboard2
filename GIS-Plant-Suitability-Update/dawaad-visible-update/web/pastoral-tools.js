/* Reusable agro-hydrology widgets for the Dawaad Leaflet workspace. */
(function registerPastoralTools(global) {
  "use strict";

  if (!global || !global.L) throw new Error("PastoralTools requires Leaflet.");
  const L = global.L;
  const EARTH_RADIUS_M = 6371008.8;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function roundUp(value, increment) {
    return Math.ceil(value / increment) * increment;
  }

  function calculateSolarPump({ dailyWaterM3, totalDynamicHeadM }) {
    const dailyVolume = Number(dailyWaterM3);
    const head = Number(totalDynamicHeadM);
    if (!Number.isFinite(dailyVolume) || dailyVolume <= 0 || dailyVolume > 2000) {
      throw new RangeError("Daily water output must be between 0 and 2,000 m³/day.");
    }
    if (!Number.isFinite(head) || head <= 0 || head > 500) {
      throw new RangeError("Total dynamic head must be between 0 and 500 m.");
    }

    const wireToWaterEfficiency = 0.55;
    const motorReserve = 1.2;
    const designHours = 6;
    const peakSunHours = 5.5;
    const solarDerate = 0.75;
    const hydraulicEnergyKwh = (1000 * 9.81 * dailyVolume * head) / 3_600_000;
    const electricalEnergyKwh = hydraulicEnergyKwh / wireToWaterEfficiency;
    const operatingKw = electricalEnergyKwh / designHours;
    const pumpPowerKw = Math.max(0.75, roundUp(operatingKw * motorReserve, 0.25));
    const estimatedRuntimeHours = Math.min(24, electricalEnergyKwh / (pumpPowerKw / motorReserve));
    const solarForMotorKwp = pumpPowerKw / solarDerate;
    const solarForEnergyKwp = electricalEnergyKwh / (peakSunHours * solarDerate);
    const solarArrayKwp = roundUp(Math.max(solarForMotorKwp, solarForEnergyKwp), 0.1);

    return {
      pumpPowerKw: Number(pumpPowerKw.toFixed(2)),
      solarArrayKwp: Number(solarArrayKwp.toFixed(1)),
      estimatedRuntimeHours: Number(estimatedRuntimeHours.toFixed(1)),
      designFlowM3h: Number((dailyVolume / estimatedRuntimeHours).toFixed(1)),
      assumptions: {
        wireToWaterEfficiency,
        motorReserve,
        peakSunHours,
        solarDerate,
      },
    };
  }

  class SolarPumpWidget {
    constructor(root, options = {}) {
      this.root = typeof root === "string" ? document.querySelector(root) : root;
      if (!this.root) throw new Error("Solar pump widget root was not found.");
      this.options = options;
      this.dailyInput = this.root.querySelector('[data-pump-input="daily"]');
      this.headInput = this.root.querySelector('[data-pump-input="head"]');
      this.outputs = {
        pump: this.root.querySelector('[data-pump-output="pump"]'),
        solar: this.root.querySelector('[data-pump-output="solar"]'),
        runtime: this.root.querySelector('[data-pump-output="runtime"]'),
        flow: this.root.querySelector('[data-pump-output="flow"]'),
        error: this.root.querySelector('[data-pump-output="error"]'),
      };
      this._recalculate = this.recalculate.bind(this);
      this.dailyInput.addEventListener("input", this._recalculate);
      this.headInput.addEventListener("input", this._recalculate);
      this.recalculate();
    }

    recalculate() {
      try {
        const result = calculateSolarPump({
          dailyWaterM3: this.dailyInput.value,
          totalDynamicHeadM: this.headInput.value,
        });
        this.outputs.pump.textContent = `${result.pumpPowerKw.toFixed(2)} kW`;
        this.outputs.solar.textContent = `${result.solarArrayKwp.toFixed(1)} kWp`;
        this.outputs.runtime.textContent = `${result.estimatedRuntimeHours.toFixed(1)} h/day`;
        if (this.outputs.flow) this.outputs.flow.textContent = `${result.designFlowM3h.toFixed(1)} m³/h`;
        if (this.outputs.error) this.outputs.error.textContent = "";
        this.root.dispatchEvent(new CustomEvent("pastoral:pumpchange", { detail: result }));
        return result;
      } catch (error) {
        if (this.outputs.error) this.outputs.error.textContent = error.message;
        return null;
      }
    }

    destroy() {
      this.dailyInput.removeEventListener("input", this._recalculate);
      this.headInput.removeEventListener("input", this._recalculate);
    }
  }

  function haversineMeters(a, b) {
    const toRadians = (degrees) => (degrees * Math.PI) / 180;
    const lat1 = toRadians(a.lat);
    const lat2 = toRadians(b.lat);
    const deltaLat = lat2 - lat1;
    const deltaLng = toRadians(b.lng - a.lng);
    const value =
      Math.sin(deltaLat / 2) ** 2 +
      Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLng / 2) ** 2;
    return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(value)));
  }

  function ringPerimeterMeters(points, closeRing = true) {
    if (points.length < 2) return 0;
    let distance = 0;
    for (let index = 1; index < points.length; index += 1) {
      distance += haversineMeters(points[index - 1], points[index]);
    }
    if (closeRing && points.length > 2) distance += haversineMeters(points.at(-1), points[0]);
    return distance;
  }

  function sphericalAreaM2(points) {
    if (points.length < 3) return 0;
    const toRadians = (degrees) => (degrees * Math.PI) / 180;
    let sum = 0;
    for (let index = 0; index < points.length; index += 1) {
      const current = points[index];
      const next = points[(index + 1) % points.length];
      sum +=
        toRadians(next.lng - current.lng) *
        (2 + Math.sin(toRadians(current.lat)) + Math.sin(toRadians(next.lat)));
    }
    return Math.abs((sum * EARTH_RADIUS_M * EARTH_RADIUS_M) / 2);
  }

  class PastoralFencePlanner {
    constructor(map, root, options = {}) {
      this.map = map;
      this.root = typeof root === "string" ? document.querySelector(root) : root;
      if (!this.root) throw new Error("Fence planner root was not found.");
      this.options = options;
      this.points = [];
      this.active = false;
      this.finished = false;
      this.line = L.polyline([], { color: "#fbbf24", weight: 3, dashArray: "7 5" }).addTo(map);
      this.reserve = L.polygon([], {
        color: "#f59e0b",
        weight: 2,
        fillColor: "#fbbf24",
        fillOpacity: 0.12,
      }).addTo(map);
      this.vertices = L.layerGroup().addTo(map);
      this.perimeterNode = this.root.querySelector('[data-fence-output="perimeter"]');
      this.areaNode = this.root.querySelector('[data-fence-output="area"]');
      this.statusNode = this.root.querySelector('[data-fence-output="status"]');
      this._onMapClick = this._onMapClick.bind(this);
      this.map.on("click", this._onMapClick);
      this.root.querySelector('[data-fence-action="start"]').addEventListener("click", () => this.start());
      this.root.querySelector('[data-fence-action="finish"]').addEventListener("click", () => this.finish());
      this.root.querySelector('[data-fence-action="undo"]').addEventListener("click", () => this.undo());
      this.root.querySelector('[data-fence-action="clear"]').addEventListener("click", () => this.clear());
      this._update();
    }

    start() {
      this.clear();
      this.active = true;
      this.finished = false;
      this.map.getContainer().classList.add("dawaad-fence-drawing");
      this.statusNode.textContent = "Click map corners, then Finish & close.";
    }

    _onMapClick(event) {
      if (!this.active) return;
      this.points.push(event.latlng);
      this._update();
    }

    finish() {
      if (this.points.length < 3) {
        this.statusNode.textContent = "Add at least three corners.";
        return false;
      }
      this.active = false;
      this.finished = true;
      this.map.getContainer().classList.remove("dawaad-fence-drawing");
      this._update();
      this.statusNode.textContent = "Seasonal grazing reserve closed.";
      return true;
    }

    undo() {
      if (!this.points.length) return;
      this.points.pop();
      this.finished = false;
      this._update();
    }

    clear() {
      this.points = [];
      this.active = false;
      this.finished = false;
      this.map.getContainer().classList.remove("dawaad-fence-drawing");
      this._update();
      this.statusNode.textContent = "Start drawing a seasonal grazing reserve.";
    }

    _update() {
      const linePoints = this.finished && this.points.length > 2
        ? [...this.points, this.points[0]]
        : this.points;
      this.line.setLatLngs(linePoints);
      this.reserve.setLatLngs(this.points.length > 2 ? this.points : []);
      this.vertices.clearLayers();
      this.points.forEach((point) =>
        L.circleMarker(point, {
          radius: 4,
          color: "#fff",
          weight: 1,
          fillColor: "#f59e0b",
          fillOpacity: 1,
        }).addTo(this.vertices),
      );
      const perimeter = ringPerimeterMeters(this.points, this.points.length > 2);
      const areaM2 = sphericalAreaM2(this.points);
      this.perimeterNode.textContent = `${perimeter.toFixed(0)} m`;
      this.areaNode.textContent = `${(areaM2 / 10000).toFixed(2)} ha`;
      this.root.dispatchEvent(
        new CustomEvent("pastoral:fencechange", {
          detail: { perimeterMeters: perimeter, areaHectares: areaM2 / 10000, points: this.points.length },
        }),
      );
    }

    destroy() {
      this.map.off("click", this._onMapClick);
      this.line.remove();
      this.reserve.remove();
      this.vertices.remove();
    }
  }

  const AQUIFER_STYLES = Object.freeze({
    "High Yield": { color: "#16a34a", fillColor: "#22c55e" },
    Medium: { color: "#d97706", fillColor: "#f59e0b" },
    "Deep Saline": { color: "#7c3aed", fillColor: "#8b5cf6" },
  });

  class AquiferOverlayWidget {
    constructor(map, options = {}) {
      this.map = map;
      this.options = options;
      this.visible = options.visible !== false;
      this.layer = L.geoJSON(null, {
        pane: options.pane || "overlayPane",
        style: (feature) => ({
          ...(AQUIFER_STYLES[feature.properties?.potential] || AQUIFER_STYLES.Medium),
          weight: 2,
          opacity: 0.9,
          fillOpacity: 0.2,
          dashArray: feature.properties?.potential === "Deep Saline" ? "7 5" : null,
        }),
        onEachFeature: (feature, layer) => {
          const properties = feature.properties || {};
          layer.bindTooltip(
            `<b>${escapeHtml(properties.name)}</b><br>${escapeHtml(properties.potential)}`,
            { sticky: true, className: "dawaad-aquifer-tooltip" },
          );
          layer.bindPopup(
            `<div class="dawaad-popup"><strong>${escapeHtml(properties.name)}</strong>` +
              `<span>${escapeHtml(properties.potential)} groundwater potential</span>` +
              `<p>Typical depth <b>${escapeHtml(properties.typicalDepthM)} m</b><br>` +
              `Indicative yield <b>${escapeHtml(properties.indicativeYieldM3h)} m³/h</b><br>` +
              `Salinity risk <b>${escapeHtml(properties.salinityRisk)}</b></p></div>`,
          );
        },
      });
      if (this.visible) this.layer.addTo(map);
      this.toggle = options.toggle || null;
      if (this.toggle) {
        this.toggle.checked = this.visible;
        this.toggle.addEventListener("change", () => this.setVisible(this.toggle.checked));
      }
      this.ready = options.url ? this.load(options.url) : Promise.resolve(this);
    }

    async load(url) {
      try {
        const response = await fetch(url, { cache: "force-cache" });
        if (!response.ok) throw new Error(`Aquifer GeoJSON returned HTTP ${response.status}`);
        const data = await response.json();
        this.setData(data);
        if (this.options.onStatus) this.options.onStatus({ state: "ready", count: data.features.length });
        return this;
      } catch (error) {
        if (this.options.onStatus) this.options.onStatus({ state: "error", error: error.message });
        throw error;
      }
    }

    setData(data) {
      if (!data || data.type !== "FeatureCollection" || !Array.isArray(data.features)) {
        throw new TypeError("Aquifer data must be a GeoJSON FeatureCollection.");
      }
      this.layer.clearLayers();
      this.layer.addData(data);
      return this;
    }

    setVisible(visible) {
      this.visible = Boolean(visible);
      if (this.visible) this.layer.addTo(this.map);
      else this.layer.remove();
      if (this.toggle) this.toggle.checked = this.visible;
      return this;
    }

    destroy() {
      this.layer.remove();
    }
  }

  global.PastoralTools = Object.freeze({
    calculateSolarPump,
    SolarPumpWidget,
    PastoralFencePlanner,
    AquiferOverlayWidget,
    geometry: Object.freeze({ haversineMeters, ringPerimeterMeters, sphericalAreaM2 }),
  });
})(window);
