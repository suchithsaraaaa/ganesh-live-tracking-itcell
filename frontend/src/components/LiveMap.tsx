import React, { useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';
import { Maximize2 } from 'lucide-react';
import { ActiveMarker, TimestampLookupResult, JourneyBreadcrumb } from '../types';

interface LiveMapProps {
  markers: ActiveMarker[];
  selectedMarker: ActiveMarker | null;
  onSelectMarker: (marker: ActiveMarker) => void;
  onClearSelection: () => void;
  historicalLookup: TimestampLookupResult | null;
  journeyTrail: JourneyBreadcrumb[] | null;
  filterKey?: string;
}

// Height Classification Palette (Strict Rule: Marker color = Height ONLY)
const HEIGHT_COLORS = {
  GREEN: '#10B981',  // 15–20 ft
  YELLOW: '#F59E0B', // 21–25 ft
  RED: '#EF4444',    // 26+ ft
};

export function getMarkerHeightColor(marker: ActiveMarker): string {
  if (marker.height_classification === 'RED' || (marker.idol_height !== null && marker.idol_height !== undefined && marker.idol_height >= 26)) {
    return HEIGHT_COLORS.RED;
  }
  if (marker.height_classification === 'YELLOW' || (marker.idol_height !== null && marker.idol_height !== undefined && marker.idol_height >= 21)) {
    return HEIGHT_COLORS.YELLOW;
  }
  return HEIGHT_COLORS.GREEN;
}

function getStatusIndicator(marker: ActiveMarker): { pulse: string; badgeColor: string; label: string } {
  if (marker.is_origin_marker) {
    return {
      pulse: '',
      badgeColor: '#64748B', // Slate gray for static origin
      label: 'ORIGIN ONLY',
    };
  }

  const isLive = marker.connection_state === 'LIVE';
  const isMoving = marker.procession_state === 'MOVING';

  if (isLive && isMoving) {
    return {
      pulse: '<span class="absolute -inset-1.5 rounded-full bg-emerald-400 opacity-50 animate-ping"></span>',
      badgeColor: '#10B981',
      label: 'LIVE MOVING',
    };
  }
  if (isLive) {
    return {
      pulse: '<span class="absolute -inset-1 rounded-full bg-emerald-400/30"></span>',
      badgeColor: '#10B981',
      label: 'LIVE',
    };
  }
  if (marker.connection_state === 'DEGRADED') {
    return {
      pulse: '',
      badgeColor: '#F59E0B',
      label: 'STALE',
    };
  }
  return {
    pulse: '',
    badgeColor: '#78716C',
    label: 'OFFLINE',
  };
}

function createMarkerIcon(marker: ActiveMarker, isSelected: boolean = false): L.DivIcon {
  const heightColor = getMarkerHeightColor(marker);
  const status = getStatusIndicator(marker);
  const size = isSelected ? 38 : 30;
  const isOrigin = !!marker.is_origin_marker;

  const iconPath = isOrigin
    ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path>'
    : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>';

  const isMediumConf = marker.geocoding_confidence === 'MEDIUM';
  const borderStyle = isSelected
    ? '3px solid #FFFFFF'
    : isOrigin && isMediumConf
    ? '2.5px dashed #F59E0B'
    : isOrigin
    ? '2px dashed rgba(255,255,255,0.7)'
    : '2px solid #0B0B0A';

  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `
      <div class="relative flex items-center justify-center" style="width: ${size}px; height: ${size}px;">
        ${status.pulse}
        <div style="background-color: ${heightColor}; width: ${size}px; height: ${size}px; border-radius: 50%; border: ${borderStyle}; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);" title="${isOrigin ? (isMediumConf ? 'Origin: Locality Level (Approximate)' : 'Origin: Authoritative Pandal') : 'Live Telemetry'}">
          <svg style="width: ${size * 0.48}px; height: ${size * 0.48}px; color: white;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            ${iconPath}
          </svg>
        </div>
        <!-- Status indicator dot on bottom right -->
        <span style="position: absolute; bottom: 0; right: 0; width: 9px; height: 9px; border-radius: 50%; background-color: ${status.badgeColor}; border: 1.5px solid #0B0B0A;" title="${status.label}"></span>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

function buildMarkerPopupHtml(m: ActiveMarker): string {
  const heightColor = getMarkerHeightColor(m);
  const heightText = m.idol_height ? `${m.idol_height} ft` : '>=15 ft';
  const heightCategory = m.height_classification === 'RED'
    ? '26+ FT'
    : m.height_classification === 'YELLOW'
    ? '21–25 FT'
    : '15–20 FT';

  const conf = m.geocoding_confidence || 'HIGH';
  const confBadge = conf === 'EXACT'
    ? '<span style="color: #10B981; font-weight:700;">EXACT (Pandal)</span>'
    : conf === 'HIGH'
    ? '<span style="color: #06B6D4; font-weight:700;">HIGH (Street)</span>'
    : '<span style="color: #F59E0B; font-weight:700;">MEDIUM (Locality Approx)</span>';

  const gateBadge = m.start_gate_eligible
    ? '<span style="color: #10B981; font-weight:600;">Eligible (&le;50m)</span>'
    : '<span style="color: #EF4444; font-weight:600;">Rejected (Locality Only)</span>';

  return `
    <div style="font-family: 'Inter', sans-serif; font-size: 12px; line-height: 1.4; min-width: 210px;">
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px; margin-bottom: 6px;">
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; color: #D9793B;">
          ${m.gpid}
        </span>
        <span style="background-color: ${heightColor}20; color: ${heightColor}; border: 1px solid ${heightColor}50; font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 4px;">
          ${heightText} (${heightCategory})
        </span>
      </div>
      <div style="font-weight: 600; color: #F2EFE9; margin-bottom: 2px;">
        ${m.idol_name}
      </div>
      <div style="color: #9C9890; margin-bottom: 6px;">
        ${m.association_name || 'Individual Mandap'}
      </div>
      <div style="display: grid; grid-template-columns: auto auto; gap: 4px; color: #C7C4BC; font-size: 11px;">
        <span style="color: #9C9890;">Type:</span> <span>${m.is_origin_marker ? '<span style="color: #94A3B8; font-weight:600;">Origin Location</span>' : '<span style="color: #10B981; font-weight:600;">Live Telemetry</span>'}</span>
        <span style="color: #9C9890;">Zone:</span> <span>${m.zone}</span>
        <span style="color: #9C9890;">Police Station:</span> <span>${m.police_station} (${m.ps_code})</span>
        <span style="color: #9C9890;">Confidence:</span> <span>${confBadge}</span>
        <span style="color: #9C9890;">50m Start Gate:</span> <span>${gateBadge}</span>
        <span style="color: #9C9890;">Constable:</span> <span>${m.assigned_constable?.name || 'Unassigned'}</span>
        <span style="color: #9C9890;">Procession:</span> <span style="font-weight: 600; color: #F2EFE9;">${m.procession_state}</span>
        <span style="color: #9C9890;">Freshness:</span> <span style="font-weight: 600; color: ${m.is_origin_marker ? '#94A3B8' : m.connection_state === 'LIVE' ? '#10B981' : '#F59E0B'};">${m.is_origin_marker ? 'NOT TRACKED' : m.connection_state}</span>
        ${m.immersion_date ? `<span style="color: #9C9890;">Immersion:</span> <span>${m.immersion_date}</span>` : ''}
      </div>
      <div style="margin-top: 6px; font-size: 10px; color: #6B675F; text-align: right;">
        ${m.is_origin_marker ? 'Origin Coordinates' : `GPS: ${new Date(m.last_gps_timestamp).toLocaleTimeString()}`}
      </div>
    </div>
  `;
}

function createHistoricalIcon(): L.DivIcon {
  return L.divIcon({
    className: 'historical-marker',
    html: `
      <div style="background-color: #EF4444; width: 32px; height: 32px; border-radius: 50%; border: 3px solid #FFFFFF; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
        <span style="color: #FFFFFF; font-weight: 700; font-size: 10px;">HIST</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

export const LiveMap: React.FC<LiveMapProps> = ({
  markers,
  selectedMarker,
  onSelectMarker,
  onClearSelection,
  historicalLookup,
  journeyTrail,
  filterKey,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const polylineLayerRef = useRef<L.Polyline | null>(null);
  const histMarkerRef = useRef<L.Marker | null>(null);

  // Managed Marker Map: Map<GPID, L.Marker> for O(1) in-place differential updates
  const markersMapRef = useRef<Map<string, L.Marker>>(new Map());

  // Viewport Invariant Controls
  const userInteractedRef = useRef<boolean>(false);
  const isProgrammaticMoveRef = useRef<boolean>(false);
  const initialFitDoneRef = useRef<boolean>(false);
  const prevFilterKeyRef = useRef<string>('');
  const prevSelectedGpidRef = useRef<string | null>(null);

  // Helper for safe programmatic camera transitions without tripping user interaction
  const performProgrammaticCameraAction = useCallback((action: (map: L.Map) => void) => {
    const map = mapInstanceRef.current;
    if (!map) return;
    isProgrammaticMoveRef.current = true;
    action(map);
    setTimeout(() => {
      isProgrammaticMoveRef.current = false;
    }, 450);
  }, []);

  // Explicit "FIT ALL" Action: user explicitly resets viewport to all visible markers
  const handleFitAll = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map || markers.length === 0) return;

    const validPoints: [number, number][] = markers
      .filter((m) => typeof m.latitude === 'number' && typeof m.longitude === 'number' && !isNaN(m.latitude) && !isNaN(m.longitude))
      .map((m) => [m.latitude, m.longitude] as [number, number]);

    if (validPoints.length > 0) {
      const bounds = L.latLngBounds(validPoints);
      if (bounds.isValid()) {
        performProgrammaticCameraAction((m) => {
          m.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
        });
        // Reset userInteracted flag so the current full viewport is acknowledged
        userInteractedRef.current = false;
      }
    }
  }, [markers, performProgrammaticCameraAction]);

  // Initialize Leaflet Map once
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Hyderabad Commissionerate Center (approx 17.3850 N, 78.4867 E)
    const map = L.map(mapContainerRef.current, {
      center: [17.3850, 78.4867],
      zoom: 12,
      zoomControl: false,
    });

    const tileUrl = import.meta.env.VITE_MAP_TILE_URL
      || 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}';
    const tileAttribution = import.meta.env.VITE_MAP_TILE_ATTRIBUTION
      || 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ';

    L.tileLayer(tileUrl, {
      attribution: tileAttribution,
      maxZoom: 19,
      maxNativeZoom: 16,
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    markersLayerRef.current = layerGroup;
    mapInstanceRef.current = map;
    (mapContainerRef.current as any)._leaflet_map = map;
    (window as any).__LEAFLET_MAP__ = map;

    // Event listeners to detect manual user interaction
    // Once the user zooms, drags, or moves the map, polling updates NEVER override the viewport!
    map.on('movestart', () => {
      if (!isProgrammaticMoveRef.current) {
        userInteractedRef.current = true;
      }
    });
    map.on('zoomstart', () => {
      if (!isProgrammaticMoveRef.current) {
        userInteractedRef.current = true;
      }
    });
    map.on('dragstart', () => {
      userInteractedRef.current = true;
    });

    return () => {
      delete (window as any).__LEAFLET_MAP__;
      map.remove();
      mapInstanceRef.current = null;
      markersLayerRef.current = null;
      markersMapRef.current.clear();
      polylineLayerRef.current = null;
      histMarkerRef.current = null;
    };
  }, []);

  // Update Markers: Differential in-place updates (Zero DOM thrashing, Zero map resetting)
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = markersLayerRef.current;
    if (!map || !layerGroup) return;

    // When an idol is selected: isolate and show only selected idol marker.
    // When unselected: restore all active markers!
    const displayMarkers = selectedMarker ? [selectedMarker] : markers;
    const currentGpidSet = new Set<string>();

    displayMarkers.forEach((m) => {
      currentGpidSet.add(m.gpid);
      const isSelected = selectedMarker?.gpid === m.gpid;
      const existing = markersMapRef.current.get(m.gpid);

      if (existing) {
        // 1. In-place position update: ONLY move marker coordinates
        const currentPos = existing.getLatLng();
        if (Math.abs(currentPos.lat - m.latitude) > 1e-6 || Math.abs(currentPos.lng - m.longitude) > 1e-6) {
          existing.setLatLng([m.latitude, m.longitude]);
        }

        // 2. Icon update: only if visual state changed
        const visualSignature = `${m.is_origin_marker}|${isSelected}|${m.height_classification}|${m.connection_state}|${m.procession_state}|${m.idol_height}`;
        if ((existing as any)._visualSignature !== visualSignature) {
          existing.setIcon(createMarkerIcon(m, isSelected));
          (existing as any)._visualSignature = visualSignature;
        }

        // 3. Popup content update
        existing.setPopupContent(buildMarkerPopupHtml(m));
      } else {
        // Create new marker instance
        const marker = L.marker([m.latitude, m.longitude], {
          icon: createMarkerIcon(m, isSelected),
          title: `GPID: ${m.gpid}`,
        });
        (marker as any)._visualSignature = `${m.is_origin_marker}|${isSelected}|${m.height_classification}|${m.connection_state}|${m.procession_state}|${m.idol_height}`;
        marker.bindPopup(buildMarkerPopupHtml(m), { autoPan: false });
        marker.on('click', () => {
          onSelectMarker(m);
        });
        layerGroup.addLayer(marker);
        markersMapRef.current.set(m.gpid, marker);
      }
    });

    // Remove pruned markers (e.g. filtered out or unselected)
    markersMapRef.current.forEach((marker, gpid) => {
      if (!currentGpidSet.has(gpid)) {
        layerGroup.removeLayer(marker);
        markersMapRef.current.delete(gpid);
      }
    });

    // --- Controlled Viewport Actions ---

    // 1. Initial Load Fit: only runs ONCE if user has not already interacted
    if (!initialFitDoneRef.current && !userInteractedRef.current && displayMarkers.length > 0) {
      const validPoints: [number, number][] = displayMarkers
        .filter((m) => typeof m.latitude === 'number' && typeof m.longitude === 'number' && !isNaN(m.latitude) && !isNaN(m.longitude))
        .map((m) => [m.latitude, m.longitude] as [number, number]);

      if (validPoints.length > 0) {
        const bounds = L.latLngBounds(validPoints);
        if (bounds.isValid()) {
          performProgrammaticCameraAction((m) => {
            m.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
          });
          initialFitDoneRef.current = true;
        }
      }
    }

    // 2. Explicit Filter Change Fit: if user changes filters, fit to the newly visible subset once
    if (filterKey && filterKey !== prevFilterKeyRef.current) {
      prevFilterKeyRef.current = filterKey;
      if (!selectedMarker && displayMarkers.length > 0) {
        const validPoints: [number, number][] = displayMarkers
          .filter((m) => typeof m.latitude === 'number' && typeof m.longitude === 'number' && !isNaN(m.latitude) && !isNaN(m.longitude))
          .map((m) => [m.latitude, m.longitude] as [number, number]);

        if (validPoints.length > 0) {
          const bounds = L.latLngBounds(validPoints);
          if (bounds.isValid()) {
            performProgrammaticCameraAction((m) => {
              m.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
            });
            userInteractedRef.current = false;
          }
        }
      }
    }

    // 3. Selection change: center on selected marker ONCE when first selected
    if (selectedMarker?.gpid !== prevSelectedGpidRef.current) {
      prevSelectedGpidRef.current = selectedMarker ? selectedMarker.gpid : null;
      if (selectedMarker) {
        performProgrammaticCameraAction((m) => {
          m.setView([selectedMarker.latitude, selectedMarker.longitude], 15, { animate: true });
        });
      }
    }
  }, [markers, selectedMarker, onSelectMarker, filterKey, performProgrammaticCameraAction]);

  // Handle Journey Polyline Trail: fits bounds ONCE upon loading breadcrumbs
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (polylineLayerRef.current) {
      map.removeLayer(polylineLayerRef.current);
      polylineLayerRef.current = null;
    }

    if (journeyTrail && journeyTrail.length > 1) {
      const latlngs: L.LatLngExpression[] = journeyTrail.map((p) => [p.latitude, p.longitude]);
      const poly = L.polyline(latlngs, {
        color: '#F59E0B',
        weight: 4,
        opacity: 0.85,
        dashArray: '4, 8',
      }).addTo(map);
      polylineLayerRef.current = poly;
      performProgrammaticCameraAction((m) => {
        m.fitBounds(poly.getBounds(), { padding: [40, 40] });
      });
    }
  }, [journeyTrail, performProgrammaticCameraAction]);

  // Handle Historical Timestamp Lookup Focus Marker
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (histMarkerRef.current) {
      map.removeLayer(histMarkerRef.current);
      histMarkerRef.current = null;
    }

    if (historicalLookup?.nearest_point) {
      const np = historicalLookup.nearest_point;
      const marker = L.marker([np.latitude, np.longitude], {
        icon: createHistoricalIcon(),
        zIndexOffset: 1000,
      }).addTo(map);

      const histPopupHtml = `
        <div style="font-family: 'Inter', sans-serif; font-size: 12px; color: #C7C4BC;">
          <div style="font-weight: 600; color: #EF4444; margin-bottom: 4px;">HISTORICAL GPS POINT</div>
          <div><b style="color:#F2EFE9;">GPID:</b> ${historicalLookup.gpid}</div>
          <div><b style="color:#F2EFE9;">Recorded:</b> ${new Date(np.recorded_at).toLocaleString()}</div>
          <div><b style="color:#F2EFE9;">Time Delta:</b> ${np.time_difference_seconds}s from query</div>
          <div><b style="color:#F2EFE9;">Officer on Duty:</b> ${historicalLookup.constable.name} (${historicalLookup.constable.police_id})</div>
        </div>
      `;
      marker.bindPopup(histPopupHtml).openPopup();
      histMarkerRef.current = marker;
      performProgrammaticCameraAction((m) => {
        m.setView([np.latitude, np.longitude], 16, { animate: true });
      });
    }
  }, [historicalLookup, performProgrammaticCameraAction]);

  return (
    <div className="relative w-full h-full flex-1">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Explicit FIT ALL Map Control */}
      <div className="absolute top-3 right-3 z-[1000]">
        <button
          onClick={handleFitAll}
          id="btn-fit-all"
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-elevated/90 hover:bg-elevated border border-border-default hover:border-accent/60 text-text-primary rounded-md shadow-lg backdrop-blur-md transition-all text-xs font-medium cursor-pointer"
          title="Fit view to all visible idols"
        >
          <Maximize2 className="w-3.5 h-3.5 text-accent" />
          <span>Fit All</span>
        </button>
      </div>

      {/* Honest Empty State Overlay */}
      {markers.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-base/60 backdrop-blur-sm z-[999] pointer-events-none">
          <div className="p-4 bg-elevated-1 border border-border-default rounded-lg text-center max-w-sm pointer-events-auto shadow-2xl">
            <p className="text-sm font-semibold text-text-primary mb-1">No Idols Plotted</p>
            <p className="text-xs text-text-secondary">
              No eligible (15+ ft) idols with valid geographic coordinates match the selected filters.
            </p>
          </div>
        </div>
      )}

      {/* Floating Single-Selection Banner */}
      {selectedMarker && (
        <div className="absolute top-3 left-3 z-[1000] bg-elevated/95 border border-accent/40 rounded-lg p-3 shadow-xl backdrop-blur max-w-sm flex items-start justify-between">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-accent">
                {selectedMarker.is_origin_marker ? 'Static Origin Mode' : 'Isolated Tracking Mode'}
              </span>
              <span
                className="text-[9px] font-bold px-1.5 py-0.5 rounded border"
                style={{
                  color: getMarkerHeightColor(selectedMarker),
                  borderColor: `${getMarkerHeightColor(selectedMarker)}50`,
                  backgroundColor: `${getMarkerHeightColor(selectedMarker)}15`,
                }}
              >
                {selectedMarker.idol_height ? `${selectedMarker.idol_height} ft` : '>=15 ft'}
              </span>
            </div>
            <div className="text-sm font-semibold text-text-primary mono mt-0.5">
              GPID: {selectedMarker.gpid}
            </div>
            <div className="text-xs text-text-secondary truncate">
              {selectedMarker.idol_name} &bull; {selectedMarker.police_station}
            </div>
            <div className="text-[11px] text-text-tertiary mt-1">
              Procession: <span className="font-semibold text-text-primary">{selectedMarker.procession_state}</span>
              &nbsp;&bull;&nbsp; Type: <span className="font-semibold text-text-secondary">{selectedMarker.is_origin_marker ? 'Origin Location' : selectedMarker.connection_state}</span>
            </div>
          </div>
          <button
            onClick={onClearSelection}
            className="ml-3 p-1.5 rounded bg-elevated-2 hover:bg-border-default/50 text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
            title="Restore all markers"
          >
            <span className="text-[11px] font-medium px-1">Restore Map</span>
          </button>
        </div>
      )}

      {/* Compact Operational Map Legend (Dual-Dimension: Height vs Telemetry) */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-elevated/90 border border-border-default/60 backdrop-blur-md rounded-md p-2.5 shadow-xl text-[11px] pointer-events-auto">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary mb-1.5">
          Idol Height
        </div>
        <div className="flex flex-col gap-1 mb-2">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] shrink-0" />
            <span className="text-text-primary font-medium">15–20 FT (Green)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B] shrink-0" />
            <span className="text-text-primary font-medium">21–25 FT (Yellow)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444] shrink-0" />
            <span className="text-text-primary font-medium">26+ FT (Red)</span>
          </div>
        </div>
        <div className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary mb-1.5 pt-1.5 border-t border-border-subtle">
          Telemetry & Markers
        </div>
        <div className="flex flex-col gap-1">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-emerald-400/30 shrink-0" />
            <span className="text-text-secondary">LIVE (Active Fix)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" />
            <span className="text-text-secondary">STALE (Degraded)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-stone-500 shrink-0" />
            <span className="text-text-secondary">OFFLINE</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-slate-400 shrink-0 border border-white/40" />
            <span className="text-text-secondary font-medium">ORIGIN ONLY (Not Tracked)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
