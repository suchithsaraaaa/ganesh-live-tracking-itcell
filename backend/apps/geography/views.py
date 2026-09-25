from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import PoliceStationBoundary


class PoliceStationListView(APIView):
    """
    Read-only endpoint returning the authoritative 72 Hyderabad Police Station master list.
    Sourced from the authoritative reference dataset (UNIQUE-CODE-FINAL-LIST.xlsx).
    Server-side jurisdiction applies to Zonal System Admins and station officers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_zone = (getattr(user, 'zone', '') or '').strip()
        is_global = bool(user.is_superuser or user.role == 'SUPER_ADMIN' or (user.role == 'MAIN_OFFICER' and not user_zone))

        qs = PoliceStationBoundary.objects.all().order_by('ps_name')

        if not is_global:
            from common.zones import zone_filter_q
            if user.role == 'SYS_ADMIN':
                if user_zone:
                    qs = qs.filter(zone_filter_q('zone', user_zone))
                else:
                    qs = qs.none()
            elif user.role == 'ACP':
                if user_zone:
                    qs = qs.filter(zone_filter_q('zone', user_zone))
                elif user.division:
                    qs = qs.filter(division__iexact=user.division)
                else:
                    qs = qs.none()
            elif user.role == 'SHO':
                if user.police_station:
                    from common.zones import ps_filter_q
                    qs = qs.filter(ps_filter_q('ps_name', user.police_station))
                else:
                    qs = qs.none()
            elif user.role == 'MAIN_OFFICER' and user_zone:
                qs = qs.filter(zone_filter_q('zone', user_zone))

        zone = request.query_params.get('zone')
        division = request.query_params.get('division')
        search = request.query_params.get('search')

        if zone and zone not in ['All Zones', 'all', '']:
            from common.zones import zone_filter_q
            qs = qs.filter(zone_filter_q('zone', zone))
        if division:
            qs = qs.filter(division__iexact=division)
        if search:
            qs = qs.filter(ps_name__icontains=search)

        from common.zones import normalize_zone
        stations = [
            {
                'id': ps.id,
                'ps_name': ps.ps_name,
                'ps_code': ps.ps_code,
                'zone': normalize_zone(ps.zone),
                'division': ps.division,
                'first_unique_id': ps.first_unique_id,
                'starting_gpid_number': ps.starting_gpid_number,
            }
            for ps in qs
        ]
        return Response({
            'count': len(stations),
            'results': stations
        })


class ZoneListView(APIView):
    """
    Read-only endpoint returning authoritative distinct zones.
    Scoped by caller jurisdiction for Zonal System Admins and station officers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_zone = (getattr(user, 'zone', '') or '').strip()
        is_global = bool(user.is_superuser or user.role == 'SUPER_ADMIN' or (user.role == 'MAIN_OFFICER' and not user_zone))

        from common.zones import normalize_zone, AUTHORITATIVE_ZONES
        if not is_global:
            if user.role == 'SYS_ADMIN':
                canonical = normalize_zone(user_zone)
                zones = [canonical] if canonical else []
            elif user.role == 'ACP':
                canonical = normalize_zone(user_zone)
                zones = [canonical] if canonical else []
            elif user.role == 'SHO':
                from common.zones import ps_filter_q
                ps = PoliceStationBoundary.objects.filter(ps_filter_q('ps_name', user.police_station)).first()
                raw_zone = ps.zone if ps and ps.zone else user_zone
                canonical = normalize_zone(raw_zone)
                zones = [canonical] if canonical else []
            else:
                canonical = normalize_zone(user_zone)
                zones = [canonical] if canonical else []
        else:
            zones = list(AUTHORITATIVE_ZONES)

        return Response({
            'count': len(zones),
            'results': zones,
            'zones': zones
        })

