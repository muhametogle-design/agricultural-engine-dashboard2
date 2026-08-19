/*
 * Dawaad / Abaar Alert map component.
 * Vanilla JavaScript + Leaflet; no bundler required.
 */
(function registerDawaadMap(global) {
  "use strict";

  if (!global || !global.L) {
    throw new Error("DawaadMapComponent requires Leaflet to be loaded first.");
  }

  const L = global.L;
  const DEFAULT_OPTIONS = Object.freeze({
    center: [8.4167, 47.3667],
    zoom: 8,
    minZoom: 3,
    maxZoom: 19,
    defaultBasemap: "esri",
    boundaryTimeoutMs: 20000,
    monitoringTimeoutMs: 8000,
    monitoringApiBase: "",
    monitoringFallbackUrl: "/web/drought.mock.json",
    initialRegion: "Sool",
    boundarySources: Object.freeze({
      regions:
        "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/SOM/ADM1/geoBoundaries-SOM-ADM1_simplified.geojson",
      districts:
        "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/SOM/ADM2/geoBoundaries-SOM-ADM2_simplified.geojson",
    }),
  });

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function boundaryName(properties = {}) {
    return (
      properties.shapeName ||
      properties.ADM2_EN ||
      properties.ADM1_EN ||
      properties.adm2_name ||
      properties.adm1_name ||
      properties.name ||
      properties.NAME_2 ||
      properties.NAME_1 ||
      "Unnamed administrative area"
    );
  }

  class FullscreenControl extends L.Control {
    constructor(options = {}) {
      super({ position: "topleft", ...options });
      this._onFullscreenChange = this._onFullscreenChange.bind(this);
    }

    onAdd(map) {
      this._map = map;
      const wrapper = L.DomUtil.create("div", "leaflet-bar leaflet-control dawaad-fullscreen");
      const button = L.DomUtil.create("a", "dawaad-fullscreen-button", wrapper);
      button.href = "#";
      button.title = "Toggle full screen";
      button.setAttribute("role", "button");
      button.setAttribute("aria-label", "Enter full screen map");
      button.setAttribute("aria-pressed", "false");
      button.innerHTML = "&#x26F6;";
      this._button = button;

      L.DomEvent.disableClickPropagation(wrapper);
      L.DomEvent.on(button, "click", L.DomEvent.stop);
      L.DomEvent.on(button, "click", this._toggle, this);
      document.addEventListener("fullscreenchange", this._onFullscreenChange);
      return wrapper;
    }

    onRemove() {
      document.removeEventListener("fullscreenchange", this._onFullscreenChange);
    }

    _toggle() {
      const mapContainer = this._map.getContainer();
      const container = mapContainer.parentElement || mapContainer;
      this._fullscreenContainer = container;
      if (!document.fullscreenElement) {
        const request = container.requestFullscreen || container.webkitRequestFullscreen;
        if (request) request.call(container);
      } else {
        const exit = document.exitFullscreen || document.webkitExitFullscreen;
        if (exit) exit.call(document);
      }
    }

    _onFullscreenChange() {
      const active = document.fullscreenElement === (this._fullscreenContainer || this._map.getContainer());
      this._button.setAttribute("aria-pressed", String(active));
      this._button.setAttribute("aria-label", active ? "Exit full screen map" : "Enter full screen map");
      this._button.title = active ? "Exit full screen" : "Enter full screen";
      global.setTimeout(() => this._map.invalidateSize({ pan: false }), 80);
    }
  }

  class DawaadMapComponent {
    constructor(target, options = {}) {
      const container = typeof target === "string" ? document.getElementById(target) : target;
      if (!container) throw new Error(`Map container not found: ${target}`);

      this.container = container;
      this.options = {
        ...DEFAULT_OPTIONS,
        ...options,
        boundarySources: {
          ...DEFAULT_OPTIONS.boundarySources,
          ...(options.boundarySources || {}),
        },
      };
      this.map = null;
      this.baseLayers = {};
      this.boundaryLayers = {};
      this.monitoringLayers = {};
      this.monitoringState = { state: "idle", region: this.options.initialRegion, source: null };
      this.monitoringFallback = null;
      this.controls = {};
      this.layerState = {
        regions: { state: "idle", count: 0, error: null },
        districts: { state: "idle", count: 0, error: null },
      };
      this.ready = Promise.resolve([]);
    }

    init() {
      if (this.map) return this;

      this.map = L.map(this.container, {
        center: this.options.center,
        zoom: this.options.zoom,
        minZoom: this.options.minZoom,
        maxZoom: this.options.maxZoom,
        zoomControl: true,
        attributionControl: true,
      });

      this._createPanes();
      this._createBasemaps();
      this._createBoundaryLayers();
      this._createMonitoringLayers();
      this._createControls();
      this._bindEvents();
      this.boundariesReady = this.reloadBoundaries();
      this.monitoringReady = this.loadMonitoring(this.options.initialRegion);
      this.ready = Promise.allSettled([this.boundariesReady, this.monitoringReady]);
      return this;
    }

    _createPanes() {
      this.map.createPane("dawaadRegions");
      this.map.getPane("dawaadRegions").style.zIndex = "430";
      this.map.createPane("dawaadDistricts");
      this.map.getPane("dawaadDistricts").style.zIndex = "440";
      this.map.createPane("dawaadClimateStations");
      this.map.getPane("dawaadClimateStations").style.zIndex = "460";
      this.map.createPane("dawaadWaterPoints");
      this.map.getPane("dawaadWaterPoints").style.zIndex = "470";
    }

    _createBasemaps() {
      this.baseLayers.osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        minZoom: this.options.minZoom,
        maxZoom: 19,
        maxNativeZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>',
      });

      this.baseLayers.esriImagery = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          minZoom: this.options.minZoom,
          maxZoom: this.options.maxZoom,
          maxNativeZoom: 19,
          zIndex: 1,
          attribution:
            'Tiles &copy; <a href="https://www.esri.com/" target="_blank" rel="noopener">Esri</a> &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
        },
      );
      this.baseLayers.esriLabels = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        {
          minZoom: this.options.minZoom,
          maxZoom: this.options.maxZoom,
          maxNativeZoom: 19,
          zIndex: 2,
          attribution: 'Labels &copy; <a href="https://www.esri.com/" target="_blank" rel="noopener">Esri</a>',
        },
      );
      this.baseLayers.esri = L.layerGroup([
        this.baseLayers.esriImagery,
        this.baseLayers.esriLabels,
      ]);

      (this.options.defaultBasemap === "osm" ? this.baseLayers.osm : this.baseLayers.esri).addTo(
        this.map,
      );
    }

    _createBoundaryLayers() {
      this.boundaryLayers.regions = L.geoJSON(null, {
        pane: "dawaadRegions",
        style: () => ({
          color: "#f59e0b",
          weight: 2.4,
          opacity: 0.95,
          fillColor: "#fbbf24",
          fillOpacity: 0.035,
        }),
        onEachFeature: (feature, layer) => this._bindBoundaryFeature("Gobol", feature, layer),
      });

      this.boundaryLayers.districts = L.geoJSON(null, {
        pane: "dawaadDistricts",
        style: () => ({
          color: "#22d3ee",
          weight: 1.15,
          dashArray: "5 4",
          opacity: 0.88,
          fillOpacity: 0,
        }),
        onEachFeature: (feature, layer) => this._bindBoundaryFeature("Degmo", feature, layer),
      });

      this.boundaryLayers.regions.addTo(this.map);
    }

    _createMonitoringLayers() {
      this.monitoringLayers.climateStations = L.featureGroup().addTo(this.map);
      this.monitoringLayers.waterPoints = L.featureGroup().addTo(this.map);
    }

    _bindBoundaryFeature(levelLabel, feature, layer) {
      const name = boundaryName(feature.properties);
      layer.bindTooltip(`${escapeHtml(levelLabel)} · ${escapeHtml(name)}`, {
        sticky: true,
        direction: "auto",
        className: "dawaad-boundary-tooltip",
      });
      layer.bindPopup(
        `<div class="dawaad-popup"><strong>${escapeHtml(name)}</strong>` +
          `<span>${escapeHtml(levelLabel)} administrative boundary</span></div>`,
      );
      layer.on({
        mouseover: () => layer.setStyle({ weight: levelLabel === "Gobol" ? 3.4 : 2.1, fillOpacity: 0.08 }),
        mouseout: () =>
          layer.setStyle({
            weight: levelLabel === "Gobol" ? 2.4 : 1.15,
            fillOpacity: levelLabel === "Gobol" ? 0.035 : 0,
          }),
      });
    }

    _createControls() {
      this.controls.layers = L.control
        .layers(
          {
            "Esri Satellite + Labels": this.baseLayers.esri,
            "OpenStreetMap Standard": this.baseLayers.osm,
          },
          {
            "Climate stations": this.monitoringLayers.climateStations,
            "Pastoral water points": this.monitoringLayers.waterPoints,
            "Gobol boundaries": this.boundaryLayers.regions,
            "Degmo boundaries": this.boundaryLayers.districts,
          },
          { position: "topright", collapsed: false },
        )
        .addTo(this.map);

      this.controls.scale = L.control
        .scale({ position: "bottomleft", metric: true, imperial: false, maxWidth: 150 })
        .addTo(this.map);
      this.controls.fullscreen = new FullscreenControl({ position: "topleft" }).addTo(this.map);
    }

    _bindEvents() {
      this.map.on("moveend zoomend", () => {
        const center = this.map.getCenter();
        this._emit("dawaad:viewchange", {
          center: [Number(center.lat.toFixed(6)), Number(center.lng.toFixed(6))],
          zoom: this.map.getZoom(),
        });
      });
    }

    async loadMonitoring(region = this.options.initialRegion) {
      const requestedRegion = String(region || this.options.initialRegion).trim();
      this._setMonitoringState({ state: "loading", region: requestedRegion, source: null });
      try {
        let metrics;
        let waterPoints;
        let source = "mock API";
        try {
          const base = String(this.options.monitoringApiBase || "").replace(/\/$/, "");
          [metrics, waterPoints] = await Promise.all([
            this._fetchMonitoringJson(
              `${base}/api/v1/drought-metrics?region=${encodeURIComponent(requestedRegion)}`,
            ),
            this._fetchMonitoringJson(`${base}/api/v1/water-points`),
          ]);
        } catch (apiError) {
          const fallback = await this._loadMonitoringFallback();
          metrics = fallback.droughtMetrics[requestedRegion.toLowerCase()];
          waterPoints = fallback.waterPoints;
          source = "local standalone mock";
          if (!metrics) throw apiError;
        }

        this._renderClimateStations(metrics);
        this._renderWaterPoints(waterPoints);
        const rainfall = metrics.rainfallRecords || [];
        const vegetation = (metrics.vegetationIndices || [])[0] || {};
        const average = (items, key) =>
          items.length ? items.reduce((sum, item) => sum + Number(item[key] || 0), 0) / items.length : 0;
        const summary = {
          state: "ready",
          region: metrics.region,
          period: metrics.period,
          averageRainfallMm: Number(average(rainfall, "rainfallMm").toFixed(1)),
          averageAnomalyPct: Number(average(rainfall, "anomalyPct").toFixed(1)),
          vciScore: vegetation.vciScore,
          vegetationStatus: vegetation.status,
          stationCount: (metrics.stations || []).length,
          waterPointCount: (waterPoints.features || []).length,
          dataMode: metrics.dataMode || "mock",
          source,
          disclaimer: metrics.disclaimer,
        };
        this._setMonitoringState(summary);
        this._emit("dawaad:monitoringload", summary);
        return summary;
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const failure = { state: "error", region: requestedRegion, source: null, error: message };
        this._setMonitoringState(failure);
        this._emit("dawaad:monitoringerror", failure);
        throw error;
      }
    }

    focusMonitoringRegion(options = {}) {
      const layer = this.monitoringLayers.climateStations;
      if (!layer || !layer.getLayers().length) return false;
      this.map.fitBounds(layer.getBounds(), { padding: [36, 36], maxZoom: 9, ...options });
      return true;
    }

    async _fetchMonitoringJson(url) {
      const controller = new AbortController();
      const timeout = global.setTimeout(() => controller.abort(), this.options.monitoringTimeoutMs);
      try {
        const response = await fetch(url, {
          signal: controller.signal,
          headers: { Accept: "application/json" },
          cache: "no-store",
        });
        if (!response.ok) throw new Error(`Monitoring API returned HTTP ${response.status}`);
        return await response.json();
      } finally {
        global.clearTimeout(timeout);
      }
    }

    async _loadMonitoringFallback() {
      if (this.monitoringFallback) return this.monitoringFallback;
      const response = await fetch(this.options.monitoringFallbackUrl, { cache: "force-cache" });
      if (!response.ok) throw new Error(`Monitoring fallback returned HTTP ${response.status}`);
      this.monitoringFallback = await response.json();
      return this.monitoringFallback;
    }

    _renderClimateStations(metrics) {
      const layer = this.monitoringLayers.climateStations;
      layer.clearLayers();
      const rainfallByStation = new Map(
        (metrics.rainfallRecords || []).map((record) => [record.stationId, record]),
      );
      (metrics.stations || []).forEach((station) => {
        const rainfall = rainfallByStation.get(station.id);
        const anomaly = Number(rainfall?.anomalyPct || 0);
        const color = anomaly <= -50 ? "#ef4444" : anomaly <= -20 ? "#f59e0b" : "#22c55e";
        const marker = L.circleMarker([station.lat, station.lng], {
          pane: "dawaadClimateStations",
          radius: 8,
          color: "#fff",
          weight: 2,
          fillColor: color,
          fillOpacity: 0.95,
        });
        marker.bindTooltip(
          `<b>${escapeHtml(station.name)}</b><br>${rainfall?.rainfallMm ?? "—"} mm · ${anomaly}%`,
          { direction: "top", className: "dawaad-monitoring-tooltip" },
        );
        marker.bindPopup(
          `<div class="dawaad-popup"><strong>${escapeHtml(station.name)}</strong>` +
            `<span>${escapeHtml(station.region)} · ${escapeHtml(metrics.period?.dekad || "")}</span>` +
            `<p>Rainfall <b>${rainfall?.rainfallMm ?? "—"} mm</b><br>` +
            `Historical mean <b>${rainfall?.historicalMeanMm ?? "—"} mm</b><br>` +
            `Anomaly <b>${anomaly}%</b></p></div>`,
        );
        marker.addTo(layer);
      });
    }

    _renderWaterPoints(collection) {
      const layer = this.monitoringLayers.waterPoints;
      layer.clearLayers();
      const colors = { Functional: "#22c55e", Stressed: "#f59e0b", Dry: "#ef4444" };
      (collection.features || []).forEach((feature) => {
        const properties = feature.properties || {};
        const coordinates = feature.geometry?.coordinates || [properties.lng, properties.lat];
        const radius = properties.type === "Borehole" ? 8 : properties.type === "Berkad" ? 7 : 6;
        const marker = L.circleMarker([coordinates[1], coordinates[0]], {
          pane: "dawaadWaterPoints",
          radius,
          color: "#fff",
          weight: 2,
          fillColor: colors[properties.status] || "#94a3b8",
          fillOpacity: 0.95,
        });
        marker.bindTooltip(
          `<b>${escapeHtml(properties.name)}</b><br>${escapeHtml(properties.type)} · ${escapeHtml(properties.status)}`,
          { direction: "top", className: "dawaad-monitoring-tooltip" },
        );
        marker.bindPopup(
          `<div class="dawaad-popup"><strong>${escapeHtml(properties.name)}</strong>` +
            `<span>${escapeHtml(properties.type)} · ${escapeHtml(properties.status)}</span>` +
            `<p>Depth <b>${properties.depthMeters ?? "—"} m</b><br>` +
            `ID <b>${escapeHtml(properties.id)}</b></p></div>`,
        );
        marker.addTo(layer);
      });
    }

    _setMonitoringState(state) {
      this.monitoringState = { ...state };
      if (typeof this.options.onMonitoringStatus === "function") {
        this.options.onMonitoringStatus(this.monitoringState, this);
      }
    }

    async reloadBoundaries() {
      return Promise.allSettled([
        this._loadBoundary("regions", this.options.boundarySources.regions),
        this._loadBoundary("districts", this.options.boundarySources.districts),
      ]);
    }

    async _loadBoundary(kind, source) {
      this._setLayerState(kind, { state: "loading", count: 0, error: null });
      try {
        const data = typeof source === "object" ? source : await this._fetchGeoJson(source);
        this.setBoundaryData(kind, data);
        const count = data.features.length;
        this._setLayerState(kind, { state: "ready", count, error: null });
        this._addBoundaryAttribution();
        this._emit("dawaad:layerload", { kind, count, source });
        return { kind, count };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        this._setLayerState(kind, { state: "error", count: 0, error: message });
        this._emit("dawaad:layererror", { kind, source, error: message });
        throw error;
      }
    }

    async _fetchGeoJson(url) {
      if (!url) throw new Error("Boundary GeoJSON URL is not configured.");
      const controller = new AbortController();
      const timeout = global.setTimeout(() => controller.abort(), this.options.boundaryTimeoutMs);
      try {
        const response = await fetch(url, {
          signal: controller.signal,
          headers: { Accept: "application/geo+json, application/json" },
          cache: "force-cache",
        });
        if (!response.ok) throw new Error(`GeoJSON request failed with HTTP ${response.status}`);
        const data = await response.json();
        if (data.type !== "FeatureCollection" || !Array.isArray(data.features)) {
          throw new Error("Boundary response is not a GeoJSON FeatureCollection.");
        }
        return data;
      } finally {
        global.clearTimeout(timeout);
      }
    }

    setBoundaryData(kind, data) {
      const layer = this.boundaryLayers[kind];
      if (!layer) throw new Error(`Unknown boundary layer: ${kind}`);
      if (!data || data.type !== "FeatureCollection" || !Array.isArray(data.features)) {
        throw new TypeError("Boundary data must be a GeoJSON FeatureCollection.");
      }
      layer.clearLayers();
      layer.addData(data);
      return this;
    }

    focusBoundaryLayer(kind, options = {}) {
      const layer = this.boundaryLayers[kind];
      if (!layer || !layer.getLayers().length) return false;
      this.map.fitBounds(layer.getBounds(), { padding: [24, 24], ...options });
      return true;
    }

    _addBoundaryAttribution() {
      if (this._boundaryAttributionAdded) return;
      this.map.attributionControl.addAttribution(
        '<a href="https://www.geoboundaries.org/" target="_blank" rel="noopener">geoBoundaries CC BY 4.0</a>',
      );
      this._boundaryAttributionAdded = true;
    }

    _setLayerState(kind, state) {
      this.layerState[kind] = { ...state };
      if (typeof this.options.onStatus === "function") {
        this.options.onStatus({ kind, ...this.layerState[kind] }, this);
      }
    }

    _emit(name, detail) {
      this.container.dispatchEvent(new CustomEvent(name, { detail }));
    }

    getMap() {
      return this.map;
    }

    destroy() {
      if (!this.map) return;
      this.map.remove();
      this.map = null;
      this.baseLayers = {};
      this.boundaryLayers = {};
      this.monitoringLayers = {};
      this.controls = {};
    }
  }

  global.DawaadMapComponent = DawaadMapComponent;
  global.DawaadMapUtils = Object.freeze({ boundaryName });
})(window);
