"""
Pure server-side PDF Report generation using ReportLab.
Produces official Telangana / Hyderabad Police Ganesh Visarjan Live Tracking Journey Report.
"""
import io
import math
import uuid
from datetime import timedelta
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from apps.idols.models import Idol
from apps.assignments.models import Assignment
from apps.tracking.models import TrackingSession, LocationPoint, IdolEvent
from apps.geography.models import BoundaryEvent
from apps.geography.services import bulk_get_cached_locations, get_bucket


def format_ps_display(ps_name: str) -> str:
    """
    Formats the Police Station name for display, ensuring canonical 'PS' suffix.
    Preserves 'Jurisdiction unavailable' and 'Boundary / Ambiguous' without alteration.
    """
    if not ps_name or ps_name in ['Jurisdiction unavailable', 'Boundary / Ambiguous', 'N/A']:
        return ps_name or 'Jurisdiction unavailable'
    cleaned = str(ps_name).strip()
    if cleaned.upper().endswith('PS') or cleaned.upper().endswith('POLICE STATION'):
        return cleaned
    return f"{cleaned} PS"


def format_location_cell(place_name: str, ps_name: str) -> str:
    """
    Renders official two-line location cell:
    <Place Name>
    PS: <Police Station>
    Strictly suppresses raw coordinates from human-readable PDF.
    Gracefully formats jurisdictional area when granular street name is unindexed.
    """
    place = (place_name or '').strip()
    ps = format_ps_display(ps_name)
    color = '#475569' if ps != 'Jurisdiction unavailable' else '#64748B'

    if place and place not in ['Location unavailable', 'Jurisdiction unavailable']:
        return f"<b>{place}</b><br/><font color='{color}'>PS: {ps}</font>"

    if ps and ps != 'Jurisdiction unavailable':
        clean_ps = ps.replace(' PS', '').replace(' Police Station', '').strip()
        return f"<b>{clean_ps} Area</b><br/><font color='{color}'>PS: {ps}</font>"

    return f"<b>Telangana / HYD Area</b><br/><font color='{color}'>PS: Jurisdiction unavailable</font>"


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_height_badge(height):
    if height is None:
        return 'N/A'
    h = float(height)
    if 15.0 <= h < 21.0:
        return f"{h:.1f} ft (15–20 FT - GREEN)"
    elif 21.0 <= h < 26.0:
        return f"{h:.1f} ft (21–25 FT - YELLOW)"
    elif h >= 26.0:
        return f"{h:.1f} ft (26+ FT - RED)"
    return f"{h:.1f} ft (<15 FT Subthreshold)"


def get_report_eligible_q():
    """
    Authoritative Django Q expression defining report-eligible idols.
    A GPID is report eligible when its procession has reached a terminal operational state:
    - IMMERSION_COMPLETED (Immersion Completed / Immersed)
    - HOLDING (Holding / Sent to Holding)
    Or has authoritative terminal operational events logged:
    - IMMERSION_COMPLETED
    - SENT_TO_HOLDING
    - HOLDING_POINT_ENTERED
    - VISARJAN_NOT_DONE
    """
    from django.db.models import Q
    from apps.idols.models import ProcessionState
    from apps.tracking.models import IdolEventType
    return (
        Q(procession_state__in=[ProcessionState.IMMERSION_COMPLETED, ProcessionState.HOLDING]) |
        Q(operational_events__event_type__in=[
            IdolEventType.IMMERSION_COMPLETED,
            IdolEventType.SENT_TO_HOLDING,
            IdolEventType.HOLDING_POINT_ENTERED,
            IdolEventType.VISARJAN_NOT_DONE
        ])
    )


def is_report_eligible(idol):
    """
    Authoritative evaluation for a single Idol instance.
    Returns True if the idol's procession has reached a terminal operational state
    (completed or holding) or has qualifying terminal operational events.
    """
    if idol is None:
        return False
    from apps.idols.models import ProcessionState
    from apps.tracking.models import IdolEventType
    if idol.procession_state in [ProcessionState.IMMERSION_COMPLETED, ProcessionState.HOLDING]:
        return True
    if hasattr(idol, 'operational_events'):
        return idol.operational_events.filter(
            event_type__in=[
                IdolEventType.IMMERSION_COMPLETED,
                IdolEventType.SENT_TO_HOLDING,
                IdolEventType.HOLDING_POINT_ENTERED,
                IdolEventType.VISARJAN_NOT_DONE
            ]
        ).exists()
    return False


def generate_idol_pdf_report(gpid, session_id=None, generated_by_user=None):
    """
    Generates a formal police operational report for a specific GPID and TrackingSession.
    Returns bytes of the PDF and report ID.
    Guarantees session-specific telemetry and durable operational event timeline.
    """
    from django.db.models import Q
    idol = Idol.objects.get(gpid__iexact=gpid)
    buffer = io.BytesIO()

    # Resolve tracking session
    session = None
    if session_id and str(session_id).isdigit():
        session = TrackingSession.objects.filter(
            id=int(session_id),
            assignment__idol=idol
        ).select_related('assignment__constable').first()

    if not session:
        session = TrackingSession.objects.filter(
            assignment__idol=idol,
            status='ACTIVE'
        ).order_by('-started_at').select_related('assignment__constable').first()

    if not session:
        session = TrackingSession.objects.filter(
            assignment__idol=idol
        ).order_by('-started_at').select_related('assignment__constable').first()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=colors.HexColor('#0F172A')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        alignment=1,
        textColor=colors.HexColor('#1E3A8A')
    )
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        alignment=1,
        textColor=colors.HexColor('#64748B')
    )
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=4,
        spaceBefore=7
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#334155')
    )
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#0F172A')
    )
    timeline_cell = ParagraphStyle(
        'TimelineCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#334155')
    )
    timeline_header = ParagraphStyle(
        'TimelineHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )

    elements = []

    # 1. Header & Official Metadata
    elements.append(Paragraph("TELANGANA POLICE DEPARTMENT — HYDERABAD COMMISSIONERATE", title_style))
    elements.append(Paragraph("GANESH VISARJAN LIVE TRACKING — OFFICIAL PROCESSION INCIDENT REPORT", subtitle_style))

    report_id = f"HYD-REP-{uuid.uuid4().hex[:8].upper()}"
    now_str = timezone.localtime(timezone.now()).strftime('%d-%b-%Y %I:%M:%S %p IST')
    by_str = generated_by_user.username if generated_by_user else 'System Officer'
    role_str = getattr(generated_by_user, 'role', 'Authorized Officer') if generated_by_user else 'Authorized'

    # Gather session-scoped points & metrics
    if session:
        points = list(LocationPoint.objects.filter(session=session).order_by('recorded_at'))
        raw_events = list(IdolEvent.objects.filter(
            Q(tracking_session=session) | Q(idol=idol, tracking_session__isnull=True)
        ).order_by('timestamp').select_related('actor'))
    else:
        points = list(LocationPoint.objects.filter(session__assignment__idol=idol).order_by('recorded_at'))
        raw_events = list(IdolEvent.objects.filter(idol=idol).order_by('timestamp').select_related('actor'))

    total_pts = len(points)
    session_id_str = f"#{session.id}" if session else "N/A"
    assigned_officer_str = (
        session.assignment.constable.get_full_name() or session.assignment.constable.username
    ) if (session and session.assignment and session.assignment.constable) else (
        (session.assignment.officer_name_snapshot if session and session.assignment else None) or "Unassigned"
    )
    proc_start_str = (
        timezone.localtime(session.started_at).strftime('%d-%b-%Y %I:%M:%S %p')
        if (session and session.started_at)
        else "Not Started"
    )
    proc_end_str = (
        timezone.localtime(session.ended_at).strftime('%d-%b-%Y %I:%M:%S %p')
        if (session and session.ended_at)
        else ("IN PROGRESS (Active)" if (session and session.status == 'ACTIVE') else "N/A")
    )


    duration_str = "0:00:00"
    total_dist_km = 0.0
    max_speed = 0.0
    if total_pts > 0:
        first_pt = points[0]
        last_pt = points[-1]
        start_time_dt = first_pt.recorded_at
        end_time_dt = session.ended_at or last_pt.recorded_at
        duration_sec = max(0, int((end_time_dt - start_time_dt).total_seconds()))
        duration_str = str(timedelta(seconds=duration_sec))

        for i in range(1, len(points)):
            seg = haversine_km(points[i-1].latitude, points[i-1].longitude, points[i].latitude, points[i].longitude)
            if seg >= 0.005:
                total_dist_km += seg

        speeds = [p.speed for p in points if p.speed is not None]
        max_speed = (max(speeds) * 3.6) if speeds else 0.0

    # Collect all coordinates to perform a single batch cache lookup (ZERO external network requests)
    all_coords = []
    if total_pts > 0:
        all_coords.append((points[0].latitude, points[0].longitude))
        all_coords.append((points[-1].latitude, points[-1].longitude))
        for p in points[1:-1]:
            all_coords.append((p.latitude, p.longitude))
    for ev in raw_events:
        if ev.latitude and ev.longitude:
            all_coords.append((ev.latitude, ev.longitude))
    for be in BoundaryEvent.objects.filter(idol=idol):
        if be.latitude and be.longitude:
            all_coords.append((be.latitude, be.longitude))

    loc_cache_map = bulk_get_cached_locations(all_coords)

    # Build chronological timeline items first to know timeline count
    timeline_items = []

    # A. Add operational events
    for ev in raw_events:
        source_label = 'Ground Staff Device' if ('Device' in str(ev.metadata)) else (ev.actor.username if ev.actor else 'Field Officer')
        if ev.latitude and ev.longitude:
            b = get_bucket(ev.latitude, ev.longitude)
            pl, ps, _, _ = loc_cache_map.get(b, ('Location unavailable', 'Jurisdiction unavailable', '', ''))
            loc_str = format_location_cell(pl, ps)
        else:
            fallback_loc = f"{ev.zone} Zone" if ev.zone else idol.police_station
            loc_str = f"<b>{fallback_loc}</b><br/><font color='#64748B'>PS: {format_ps_display(idol.police_station)}</font>"
        desc = ev.metadata.get('description') or ev.metadata.get('source') or f"{ev.get_event_type_display()} recorded"
        timeline_items.append({
            'time': ev.timestamp,
            'event': ev.get_event_type_display(),
            'source': source_label,
            'location': loc_str,
            'details': desc,
        })

    # B. Add Boundary Events
    for be in BoundaryEvent.objects.filter(idol=idol).select_related('police_station'):
        b = get_bucket(be.latitude, be.longitude)
        pl, ps, _, _ = loc_cache_map.get(b, ('Location unavailable', be.police_station.ps_name, '', ''))
        if ps == 'Jurisdiction unavailable' and be.police_station:
            ps = be.police_station.ps_name
        timeline_items.append({
            'time': be.timestamp,
            'event': f"PS Boundary {be.get_event_type_display()}",
            'source': 'PostGIS Boundary Geofence',
            'location': format_location_cell(pl, ps),
            'details': f"Crossed into {be.police_station.ps_name} ({be.police_station.zone})",
        })

    # C. Add GPS Telemetry points (sample dense points chronologically)
    if total_pts > 0:
        # Start point
        b_first = get_bucket(points[0].latitude, points[0].longitude)
        pl_first, ps_first, _, _ = loc_cache_map.get(b_first, ('Location unavailable', 'Jurisdiction unavailable', '', ''))
        timeline_items.append({
            'time': points[0].recorded_at,
            'event': 'Initial GPS Telemetry',
            'source': 'Mobile GPS Service',
            'location': format_location_cell(pl_first, ps_first),
            'details': f"Accuracy: {points[0].accuracy:.1f}m" if points[0].accuracy else "Start Position Logged",
        })

        # Sample intermediate points (every ~10 minutes or distance jump)
        if total_pts > 2:
            last_sampled_time = points[0].recorded_at
            for pt in points[1:-1]:
                delta_mins = (pt.recorded_at - last_sampled_time).total_seconds() / 60.0
                if delta_mins >= 12.0:
                    spd_kmh = (pt.speed * 3.6) if pt.speed is not None else 0.0
                    b_pt = get_bucket(pt.latitude, pt.longitude)
                    pl_pt, ps_pt, _, _ = loc_cache_map.get(b_pt, ('Location unavailable', 'Jurisdiction unavailable', '', ''))
                    timeline_items.append({
                        'time': pt.recorded_at,
                        'event': 'GPS Telemetry Breadcrumb',
                        'source': 'Mobile GPS Service',
                        'location': format_location_cell(pl_pt, ps_pt),
                        'details': f"Moving: {spd_kmh:.1f} km/h, Accuracy: {pt.accuracy or 'N/A'}m",
                    })
                    last_sampled_time = pt.recorded_at

        # Last point if distinct from first
        if total_pts > 1:
            last_pt = points[-1]
            last_spd = (last_pt.speed * 3.6) if last_pt.speed is not None else 0.0
            b_last = get_bucket(last_pt.latitude, last_pt.longitude)
            pl_last, ps_last, _, _ = loc_cache_map.get(b_last, ('Location unavailable', 'Jurisdiction unavailable', '', ''))
            timeline_items.append({
                'time': last_pt.recorded_at,
                'event': 'Latest GPS Telemetry' if (session and session.status == 'ACTIVE') else 'Final GPS Position',
                'source': 'Mobile GPS Service',
                'location': format_location_cell(pl_last, ps_last),
                'details': f"Speed: {last_spd:.1f} km/h, Accuracy: {last_pt.accuracy or 'N/A'}m",
            })

    # Chronologically sort the unified timeline
    timeline_items.sort(key=lambda x: x['time'])
    timeline_count = len(timeline_items)

    meta_text = (
        f"Report ID: <b>{report_id}</b> &nbsp;|&nbsp; Generated At: <b>{now_str}</b> &nbsp;|&nbsp; "
        f"Generated By: <b>{by_str} ({role_str})</b> &nbsp;|&nbsp; Timeline Events: <b>{timeline_count}</b>"
    )
    elements.append(Spacer(1, 3))
    elements.append(Paragraph(meta_text, meta_style))
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceBefore=2, spaceAfter=6))

    # 2. Key Operational Summary & Idol Specifications
    can_view_sensitive = bool(generated_by_user and getattr(generated_by_user, 'role', None) in ['MAIN_OFFICER', 'ACP', 'SHO'])
    contact_val = idol.raw_metadata.get('mobile_no', 'N/A') if (can_view_sensitive and idol.raw_metadata) else 'RESTRICTED (Station Officer+ Only)'

    origin_loc = f"{idol.address or ''} {idol.instal_street or ''} {idol.instal_village or ''}".strip() or idol.police_station
    destination_loc = idol.river_name or idol.lake_type or 'Designated Visarjan Point'

    elements.append(Paragraph("1. PRIMARY OPERATIONAL SPECIFICATIONS & REPORT METADATA", section_style))
    idol_data = [
        [
            Paragraph("<b>GPID:</b>", body_style), Paragraph(f"<font color='#1E3A8A'><b>{idol.gpid}</b></font>", body_bold),
            Paragraph("<b>Procession State:</b>", body_style), Paragraph(f"<b>{idol.get_procession_state_display()}</b>", body_bold),
        ],
        [
            Paragraph("<b>Tracking Session ID:</b>", body_style), Paragraph(f"<b>{session_id_str}</b>", body_bold),
            Paragraph("<b>Assigned Officer:</b>", body_style), Paragraph(f"<b>{assigned_officer_str}</b>", body_style),
        ],
        [
            Paragraph("<b>Procession Start Time:</b>", body_style), Paragraph(proc_start_str, body_style),
            Paragraph("<b>Procession End Time:</b>", body_style), Paragraph(proc_end_str, body_style),
        ],
        [
            Paragraph("<b>Total Duration:</b>", body_style), Paragraph(f"<b>{duration_str}</b>", body_bold),
            Paragraph("<b>Total GPS Points:</b>", body_style), Paragraph(f"<b>{total_pts}</b> recorded", body_style),
        ],
        [
            Paragraph("<b>Idol Height / Class:</b>", body_style), Paragraph(get_height_badge(idol.idol_height), body_bold),
            Paragraph("<b>Origin Jurisdiction:</b>", body_style), Paragraph(f"{idol.zone} Zone ({idol.police_station})", body_style),
        ],
        [
            Paragraph("<b>Applicant / Samithi:</b>", body_style), Paragraph(f"{idol.name or 'Individual'} / {idol.association_name or 'N/A'}", body_style),
            Paragraph("<b>Destination Waterbody:</b>", body_style), Paragraph(f"<font color='#0D9488'><b>{destination_loc}</b></font>", body_style),
        ],
        [
            Paragraph("<b>Origin Location:</b>", body_style), Paragraph(origin_loc, body_style),
            Paragraph("<b>Contact (Auth):</b>", body_style), Paragraph(contact_val, body_style),
        ]
    ]

    t_idol = Table(idol_data, colWidths=[1.3 * inch, 2.2 * inch, 1.4 * inch, 2.1 * inch])
    t_idol.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t_idol)
    elements.append(Spacer(1, 5))

    # 3. Constable Assignment & Handover History
    elements.append(Paragraph("2. FIELD OFFICER ASSIGNMENT & HANDOVER CHRONOLOGY", section_style))
    assignments = Assignment.objects.filter(idol=idol).order_by('started_at').select_related('constable', 'assigned_by', 'handover_to')

    if assignments.exists():
        assign_rows = [[
            Paragraph("<b>Constable</b>", body_style),
            Paragraph("<b>Police ID</b>", body_style),
            Paragraph("<b>Started At</b>", body_style),
            Paragraph("<b>Ended At</b>", body_style),
            Paragraph("<b>Handover / Status</b>", body_style),
        ]]
        for a in assignments:
            start_str = timezone.localtime(a.started_at).strftime('%d-%b %H:%M') if a.started_at else 'N/A'
            end_str = timezone.localtime(a.ended_at).strftime('%d-%b %H:%M') if a.ended_at else 'ACTIVE'
            details = "ACTIVE ASSIGNMENT" if a.is_active else f"Handover to {a.handover_to.username if a.handover_to else 'N/A'}: {a.handover_reason}"
            constable_name = (a.constable.get_full_name() or a.constable.username) if a.constable else (a.officer_name_snapshot or 'Historical Officer')
            constable_pid = (a.constable.police_id or 'N/A') if a.constable else (a.police_id_snapshot or 'N/A')
            assign_rows.append([
                Paragraph(constable_name, body_style),
                Paragraph(constable_pid, body_style),
                Paragraph(start_str, body_style),
                Paragraph(end_str, body_style),
                Paragraph(details, body_style),
            ])
        t_assign = Table(assign_rows, colWidths=[1.5 * inch, 1.0 * inch, 1.1 * inch, 1.1 * inch, 2.3 * inch])
        t_assign.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 2.2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_assign)
    else:
        elements.append(Paragraph("No constable duty assignments recorded.", body_style))

    elements.append(Spacer(1, 5))

    # 4. GPS Procession Tracking Metrics
    elements.append(Paragraph("3. GPS TRACKING & PROCESSION METRICS", section_style))
    if total_pts > 0:
        first_pt = points[0]
        last_pt = points[-1]
        start_time = timezone.localtime(first_pt.recorded_at).strftime('%d-%b-%Y %I:%M:%S %p')
        last_time = timezone.localtime(last_pt.recorded_at).strftime('%d-%b-%Y %I:%M:%S %p')

        start_b = get_bucket(first_pt.latitude, first_pt.longitude)
        start_pl, start_ps, _, _ = loc_cache_map.get(start_b, ('Location unavailable', 'Jurisdiction unavailable', '', ''))

        latest_b = get_bucket(last_pt.latitude, last_pt.longitude)
        latest_pl, latest_ps, _, _ = loc_cache_map.get(latest_b, ('Location unavailable', 'Jurisdiction unavailable', '', ''))

        gps_data = [
            [
                Paragraph("<b>Total Telemetry Points:</b>", body_style), Paragraph(str(total_pts), body_style),
                Paragraph("<b>Distance Travelled:</b>", body_style), Paragraph(f"<b>{total_dist_km:.2f} km</b>", body_bold),
            ],
            [
                Paragraph("<b>First Telemetry Fix:</b>", body_style), Paragraph(start_time, body_style),
                Paragraph("<b>Tracking Duration:</b>", body_style), Paragraph(duration_str, body_style),
            ],
            [
                Paragraph("<b>Latest Telemetry Fix:</b>", body_style), Paragraph(last_time, body_style),
                Paragraph("<b>Max Speed Recorded:</b>", body_style), Paragraph(f"{max_speed:.1f} km/h", body_style),
            ],
            [
                Paragraph("<b>Start Location:</b>", body_style), Paragraph(format_location_cell(start_pl, start_ps), body_style),
                Paragraph("<b>Latest Location:</b>", body_style), Paragraph(format_location_cell(latest_pl, latest_ps), body_style),
            ]
        ]
        t_gps = Table(gps_data, colWidths=[1.3 * inch, 2.2 * inch, 1.4 * inch, 2.1 * inch])
        t_gps.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 2.2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_gps)
    else:
        elements.append(Paragraph("No active or historical GPS points recorded for this tracking session.", body_style))

    elements.append(Spacer(1, 5))

    # 5. Chronological Procession Timeline (Official Requirement)
    elements.append(Paragraph("4. PROCESSION TIMELINE", section_style))

    if timeline_items:
        t_rows = [[
            Paragraph("<b>TIME (IST)</b>", timeline_header),
            Paragraph("<b>EVENT</b>", timeline_header),
            Paragraph("<b>OFFICER / SOURCE</b>", timeline_header),
            Paragraph("<b>LOCATION</b>", timeline_header),
            Paragraph("<b>DETAILS</b>", timeline_header),
        ]]
        for item in timeline_items[:40]:  # up to 40 chronological milestones
            t_str = timezone.localtime(item['time']).strftime('%d-%b %H:%M:%S')
            t_rows.append([
                Paragraph(t_str, timeline_cell),
                Paragraph(f"<b>{item['event']}</b>", timeline_cell),
                Paragraph(item['source'], timeline_cell),
                Paragraph(item['location'], timeline_cell),
                Paragraph(item['details'], timeline_cell),
            ])
        t_timeline = Table(t_rows, colWidths=[1.1 * inch, 1.4 * inch, 1.3 * inch, 1.3 * inch, 2.4 * inch])
        t_timeline.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 2.0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.0),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_timeline)
    else:
        elements.append(Paragraph("No operational lifecycle events or telemetry recorded for this session.", body_style))

    elements.append(Spacer(1, 8))

    # 6. Official Sign-off & Legal Notice
    footer_text = (
        "<i>This document is an official administrative operational record produced by the Hyderabad Police "
        "Ganesh Visarjan Live Tracking System. Generated in compliance with Telangana Police Department standards. "
        "Report snapshot represents operational telemetry state as of generation timestamp.</i>"
    )
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceBefore=3, spaceAfter=5))
    elements.append(Paragraph(footer_text, meta_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes, report_id

