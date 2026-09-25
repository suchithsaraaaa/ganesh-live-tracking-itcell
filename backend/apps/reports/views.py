from datetime import timedelta, datetime
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from common.permissions import filter_by_jurisdiction
from common.zones import zone_filter_q, ps_filter_q
from apps.idols.models import Idol, ProcessionState
from apps.tracking.models import IdolEvent, IdolEventType
from apps.assignments.models import Assignment
from apps.audit.models import AuditEvent
from .services import generate_idol_pdf_report, get_report_eligible_q, is_report_eligible
from .serializers import CompletedReportRegistrySerializer


class CompletedReportsRegistryView(APIView):
    """
    Operational registry endpoint for the Reports Page.
    Enforces that ONLY GPIDs that have reached completed operational status
    (IMMERSION_COMPLETED) or holding status (HOLDING / SENT_TO_HOLDING) are returned.
    Enforces server-side jurisdiction and hierarchical cascading AND filters:
    - zone
    - police_station (dependent on zone, using canonical ps_filter_q)
    - visarjan_date (today, tomorrow, YYYY-MM-DD)
    - height_bucket (all, all_15_plus, 15_20, 21_25, 26_plus, below_15)
    - operational_status (all, completed, holding)
    - search (GPID, organizer/idol name, association, police station)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Base population: all idols scoped by server-side jurisdiction
        qs = filter_by_jurisdiction(Idol.objects.all(), request.user)

        # 2. Operational eligibility: completed immersion or in holding
        completed_or_holding_condition = get_report_eligible_q()
        base_eligible_qs = qs.filter(completed_or_holding_condition).distinct()

        # 3. Summary KPIs across all qualifying records in user's jurisdiction
        total_eligible = base_eligible_qs.count()
        count_completed = base_eligible_qs.filter(
            Q(procession_state=ProcessionState.IMMERSION_COMPLETED) |
            Q(operational_events__event_type=IdolEventType.IMMERSION_COMPLETED)
        ).distinct().count()
        count_holding = base_eligible_qs.filter(
            Q(procession_state=ProcessionState.HOLDING) |
            Q(operational_events__event_type__in=[
                IdolEventType.SENT_TO_HOLDING,
                IdolEventType.HOLDING_POINT_ENTERED,
                IdolEventType.VISARJAN_NOT_DONE
            ])
        ).exclude(procession_state=ProcessionState.IMMERSION_COMPLETED).distinct().count()

        count_15_20 = base_eligible_qs.filter(idol_height__gte=15, idol_height__lt=21).count()
        count_21_25 = base_eligible_qs.filter(idol_height__gte=21, idol_height__lt=26).count()
        count_26_plus = base_eligible_qs.filter(idol_height__gte=26).count()
        count_below_15 = base_eligible_qs.filter(Q(idol_height__lt=15) | Q(idol_height__isnull=True)).count()
        count_15_plus = base_eligible_qs.filter(idol_height__gte=15).count()

        filtered_qs = base_eligible_qs

        # 4. Cascading AND filters
        # Zone filter
        zone = request.query_params.get('zone')
        if zone and zone not in ['All Zones', 'all', '']:
            filtered_qs = filtered_qs.filter(zone_filter_q('zone', zone.strip()))

        # Police Station filter (canonical normalization)
        ps = request.query_params.get('police_station')
        if ps and ps not in ['All Police Stations', 'all', '']:
            filtered_qs = filtered_qs.filter(ps_filter_q('police_station', ps.strip()))

        # Height bucket filter
        hb = request.query_params.get('height_bucket')
        if hb and hb not in ['All Heights', 'All 15+ FT', 'all', 'all_heights', '']:
            hb_clean = hb.lower().strip()
            if hb_clean in ['below_15', 'below-15', 'under_15', '<15', 'subthreshold']:
                filtered_qs = filtered_qs.filter(Q(idol_height__lt=15) | Q(idol_height__isnull=True))
            elif hb_clean in ['15_20', '15-20', 'green']:
                filtered_qs = filtered_qs.filter(idol_height__gte=15, idol_height__lt=21)
            elif hb_clean in ['21_25', '21-25', 'yellow']:
                filtered_qs = filtered_qs.filter(idol_height__gte=21, idol_height__lt=26)
            elif hb_clean in ['26_plus', '26+', 'above_25', 'red']:
                filtered_qs = filtered_qs.filter(idol_height__gte=26)
            elif hb_clean in ['all_15_plus', '15_plus', '15+']:
                filtered_qs = filtered_qs.filter(idol_height__gte=15)

        # Operational status filter
        op_status = request.query_params.get('operational_status')
        if op_status and op_status.lower() != 'all':
            op_clean = op_status.lower().strip()
            if op_clean in ['completed', 'immersion_completed', 'visarjan_completed', 'immersed']:
                filtered_qs = filtered_qs.filter(
                    Q(procession_state=ProcessionState.IMMERSION_COMPLETED) |
                    Q(operational_events__event_type=IdolEventType.IMMERSION_COMPLETED)
                ).distinct()
            elif op_clean in ['holding', 'sent_to_holding']:
                filtered_qs = filtered_qs.filter(
                    Q(procession_state=ProcessionState.HOLDING) |
                    Q(operational_events__event_type__in=[
                        IdolEventType.SENT_TO_HOLDING,
                        IdolEventType.HOLDING_POINT_ENTERED,
                        IdolEventType.VISARJAN_NOT_DONE
                    ])
                ).exclude(procession_state=ProcessionState.IMMERSION_COMPLETED).distinct()

        # Visarjan Date filter
        visarjan_date = request.query_params.get('visarjan_date')
        if visarjan_date and visarjan_date not in ['All Dates', 'all', '']:
            vdate_clean = visarjan_date.lower().strip()
            today = timezone.localdate()
            if vdate_clean == 'today':
                filtered_qs = filtered_qs.filter(immersion_date=today)
            elif vdate_clean == 'tomorrow':
                filtered_qs = filtered_qs.filter(immersion_date=today + timedelta(days=1))
            else:
                try:
                    target_date = datetime.strptime(vdate_clean, '%Y-%m-%d').date()
                    filtered_qs = filtered_qs.filter(immersion_date=target_date)
                except ValueError:
                    pass

        # Search query
        search = request.query_params.get('search')
        if search:
            search = search.strip()
            filtered_qs = filtered_qs.filter(
                Q(gpid__icontains=search) |
                Q(name__icontains=search) |
                Q(association_name__icontains=search) |
                Q(police_station__icontains=search)
            )

        # Ordering
        ordering = request.query_params.get('ordering')
        if ordering:
            filtered_qs = filtered_qs.order_by(ordering)
        else:
            filtered_qs = filtered_qs.order_by('zone', 'police_station', '-idol_height', 'gpid')

        # Pagination
        paginator = PageNumberPagination()
        try:
            page_size = int(request.query_params.get('page_size', 25))
            paginator.page_size = max(1, min(page_size, 100))
        except ValueError:
            paginator.page_size = 25

        page_records = paginator.paginate_queryset(filtered_qs, request)
        page_idol_ids = [idol.id for idol in page_records]

        # Batch-fetch assignments and events to prevent N+1 queries
        assignments_map = {}
        for a in Assignment.objects.filter(idol_id__in=page_idol_ids).select_related('constable').order_by('idol_id', '-started_at'):
            if a.idol_id not in assignments_map:
                assignments_map[a.idol_id] = a

        events_map = {}
        qualifying_event_types = [
            IdolEventType.IMMERSION_COMPLETED,
            IdolEventType.SENT_TO_HOLDING,
            IdolEventType.HOLDING_POINT_ENTERED,
            IdolEventType.VISARJAN_NOT_DONE
        ]
        for e in IdolEvent.objects.filter(idol_id__in=page_idol_ids, event_type__in=qualifying_event_types).order_by('idol_id', '-timestamp'):
            if e.idol_id not in events_map:
                events_map[e.idol_id] = e

        serializer = CompletedReportRegistrySerializer(
            page_records,
            many=True,
            context={
                'assignments_map': assignments_map,
                'events_map': events_map,
                'request': request,
            }
        )

        response_data = paginator.get_paginated_response(serializer.data).data
        response_data['summary'] = {
            'total_eligible': total_eligible,
            'count_completed': count_completed,
            'count_holding': count_holding,
            'count_15_20': count_15_20,
            'count_21_25': count_21_25,
            'count_26_plus': count_26_plus,
            'count_below_15': count_below_15,
            'count_15_plus': count_15_plus,
        }
        return Response(response_data)


class DownloadIdolReportView(APIView):
    """
    Produces and streams real server-generated PDF operational report for a GPID.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, gpid):
        idol = get_object_or_404(filter_by_jurisdiction(Idol.objects.all(), request.user), gpid__iexact=gpid)
        session_id = request.query_params.get('session_id')

        pdf_bytes, report_id = generate_idol_pdf_report(
            gpid=idol.gpid,
            session_id=session_id,
            generated_by_user=request.user
        )

        # Archive to S3 if configured
        s3_uri = None
        try:
            from .s3 import upload_report_to_s3
            s3_uri = upload_report_to_s3(pdf_bytes, f"{idol.gpid}_{report_id}.pdf")
        except Exception:
            pass

        # Log operational event and audit event
        try:
            from django.utils import timezone
            from apps.tracking.models import IdolEvent, IdolEventType, TrackingSession
            sess = None
            if session_id and str(session_id).isdigit():
                sess = TrackingSession.objects.filter(id=int(session_id)).first()
            IdolEvent.objects.create(
                idol=idol,
                gpid=idol.gpid,
                event_type=IdolEventType.REPORT_GENERATED,
                timestamp=timezone.now(),
                zone=idol.zone,
                actor=request.user,
                tracking_session=sess,
                metadata={'report_id': report_id, 'session_id': session_id}
            )
        except Exception:
            pass

        try:
            AuditEvent.objects.create(
                actor=request.user,
                action='DOWNLOAD_REPORT',
                target_model='Idol',
                target_id=idol.gpid,
                details={'report_id': report_id, 's3_uri': s3_uri, 'session_id': session_id},
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        response = HttpResponse(pdf_bytes, content_type='application/pdf')

        filename = f"{idol.gpid}_official_report.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Report-Id'] = report_id
        return response
