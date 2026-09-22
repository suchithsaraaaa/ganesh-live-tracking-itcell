import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { ActiveMarker, ProcessionState, TimestampLookupResult, JourneyBreadcrumb } from '../types';

interface LiveMapProps {
  markers: ActiveMarker[];
  selectedMarker: ActiveMarker | null;
  onSelectMarker: (marker: ActiveMarker) => void;
  onClearSelection: () => void;
  historicalLookup: TimestampLookupResult | null;
  journeyTrail: JourneyBreadcrumb[] | null;
}

// Color map for Procession States
const STATE_COLORS: Record<ProcessionState, string> = {
  NOT_STARTED: '#64748b',
  TRACKING: '#3b82f6',
  MOVING: '#10b981',
  HOLDING: '#f59e0b',
  AT_VISARJAN: '#8b5cf6',
  IMMERSION_COMPLETED: '#475569',
};

function createMarkerIcon(state: ProcessionState, isSelected: boolean = false): L.DivIcon {
  const color = STATE_COLORS[state] || '#3b82f6';
  const size = isSelected ? 36 : 28;
  const pulse = state === 'MOVING' ? '<span class="absolute -inset-1 rounded-full bg-emerald-400 opacity-40 animate-ping"></span>' : '';

  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `
      <div class="relative flex items-center justify-center" style="width: ${size}px; height: ${size}px;">
        ${pulse}
        <div style="background-color: ${color}; width: ${size}px; height: ${size}px; border-radius: 50%; border: ${isSelected ? '3px solid #ffffff' : '2px solid #0f172a'}; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);">
          <svg style="width: ${size * 0.5}px; height: ${size * 0.5}px; color: white;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
          </svg>
        </div>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

function createHistoricalIcon(): L.DivIcon {
  return L.divIcon({
    className: 'historical-marker',
    html: `
      <div style="background-color: #ef4444; width: 32px; height: 32px; border-radius: 50%; border: 3px solid #ffffff; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
        <span style="color: white; font-weight: bold; font-size: 11px;">HIST</span>
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
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const polylineLayerRef = useRef<L.Polyline | null>(null);
  const histMarkerRef = useRef<L.Marker | null>(null);

  // Initialize Leaflet Map once
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Hyderabad Commissionerate Center (approx 17.3850 N, 78.4867 E)
    const map = L.map(mapContainerRef.current, {
      center: [17.3850, 78.4867],
      zoom: 12,
      zoomControl: false,
    });

    // Clean Dark Map Tiles (CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    markersLayerRef.current = layerGroup;
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Markers based on Selection Mode
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = markersLayerRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    // RULE 16: When an officer clicks an idol:
    // 1. Select the idol.
    // 2. Hide all other idol markers.
    // 3. Keep only the selected idol visible.
    // When unselected: restore all active markers!
    const displayMarkers = selectedMarker ? [selectedMarker] : markers;

    displayMarkers.forEach((m) => {
      const isSelected = selectedMarker?.gpid === m.gpid;
      const marker = L.marker([m.latitude, m.longitude], {
        icon: createMarkerIcon(m.procession_state, isSelected),
        title: `GPID: ${m.gpid}`,
      });

      // Build Marker Popup
      const popupHtml = `
        <div style="font-family: sans-serif; font-size: 12px; line-height: 1.4;">
          <div style="font-size: 13px; font-weight: bold; color: #60a5fa; border-bottom: 1px solid #334155; padding-bottom: 4px; margin-bottom: 6px;">
            GPID: ${m.gpid}
          </div>
          <div style="font-weight: 600; color: #f1f5f9; margin-bottom: 2px;">
            ${m.idol_name}
          </div>
          <div style="color: #94a3b8; margin-bottom: 6px;">
            ${m.association_name || 'Individual Mandap'}
          </div>
          <div style="display: grid; grid-template-columns: auto auto; gap: 4px; color: #cbd5e1; font-size: 11px;">
            <span style="color: #94a3b8;">Zone:</span> <span>${m.zone}</span>
            <span style="color: #94a3b8;">Police Station:</span> <span>${m.police_station} (${m.ps_code})</span>
            <span style="color: #94a3b8;">Constable:</span> <span>${m.assigned_constable?.name || 'Unassigned'}</span>
            <span style="color: #94a3b8;">Status:</span> <span style="font-weight: bold; color: ${STATE_COLORS[m.procession_state]};">${m.procession_state}</span>
            <span style="color: #94a3b8;">Freshness:</span> <span style="font-weight: bold;">${m.connection_state}</span>
          </div>
          <div style="margin-top: 6px; font-size: 10px; color: #64748b; text-align: right;">
            GPS: ${new Date(m.last_gps_timestamp).toLocaleTimeString()}
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml);

      marker.on('click', () => {
        onSelectMarker(m);
      });

      layerGroup.addLayer(marker);
    });

    if (selectedMarker) {
      map.setView([selectedMarker.latitude, selectedMarker.longitude], 15, { animate: true });
    }
  }, [markers, selectedMarker, onSelectMarker]);

  // Handle Journey Polyline Trail
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
        color: '#3b82f6',
        weight: 4,
        opacity: 0.8,
        dashArray: '4, 8',
      }).addTo(map);
      polylineLayerRef.current = poly;
      map.fitBounds(poly.getBounds(), { padding: [40, 40] });
    }
  }, [journeyTrail]);

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
        <div style="font-family: sans-serif; font-size: 12px;">
          <div style="font-weight: bold; color: #f87171; margin-bottom: 4px;">HISTORICAL GPS POINT</div>
          <div><b>GPID:</b> ${historicalLookup.gpid}</div>
          <div><b>Recorded:</b> ${new Date(np.recorded_at).toLocaleString()}</div>
          <div><b>Time Delta:</b> ${np.time_difference_seconds}s from query</div>
          <div><b>Officer on Duty:</b> ${historicalLookup.constable.name} (${historicalLookup.constable.police_id})</div>
        </div>
      `;
      marker.bindPopup(histPopupHtml).openPopup();
      histMarkerRef.current = marker;
      map.setView([np.latitude, np.longitude], 16, { animate: true });
    }
  }, [historicalLookup]);

  return (
    <div className="relative w-full h-full flex-1">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating Single-Selection Banner */}
      {selectedMarker && (
        <div className="absolute top-3 left-3 z-[1000] bg-slate-900/95 border border-blue-500/50 rounded-lg p-3 shadow-xl backdrop-blur max-w-sm flex items-start justify-between">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-blue-400">
              Isolated Tracking Mode
            </div>
            <div className="text-sm font-bold text-white mono">
              GPID: {selectedMarker.gpid}
            </div>
            <div className="text-xs text-slate-300 truncate">
              {selectedMarker.idol_name} &bull; {selectedMarker.police_station}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Status: <span style={{ color: STATE_COLORS[selectedMarker.procession_state] }} className="font-semibold">{selectedMarker.procession_state}</span>
              &nbsp;&bull;&nbsp; Freshness: <span className="font-semibold">{selectedMarker.connection_state}</span>
            </div>
          </div>
          <button
            onClick={onClearSelection}
            className="ml-3 p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Restore all markers"
          >
            <span className="text-xs font-semibold px-1">Restore Map</span>
          </button>
        </div>
      )}
    </div>
  );
};
