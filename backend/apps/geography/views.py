from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import PoliceStationBoundary


class PoliceStationListView(APIView):
    """
    Read-only endpoint returning the authoritative 72 Hyderabad Police Station master list.
    Sourced from the authoritative reference dataset (UNIQUE-CODE-FINAL-LIST.xlsx).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        zone = request.query_params.get('zone')
        division = request.query_params.get('division')
        search = request.query_params.get('search')

        qs = PoliceStationBoundary.objects.all().order_by('ps_name')
        if zone:
            qs = qs.filter(zone__iexact=zone)
        if division:
            qs = qs.filter(division__iexact=division)
        if search:
            qs = qs.filter(ps_name__icontains=search)

        stations = [
            {
                'id': ps.id,
                'ps_name': ps.ps_name,
                'ps_code': ps.ps_code,
                'zone': ps.zone,
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
