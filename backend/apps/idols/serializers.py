from rest_framework import serializers
from .models import Idol
from apps.accounts.models import UserRole


class IdolListSerializer(serializers.ModelSerializer):
    """
    Lean operational serializer for dashboard and maps.
    Strictly excludes sensitive personal phone numbers and emails.
    """
    height_classification = serializers.SerializerMethodField()
    is_operational_eligible = serializers.SerializerMethodField()

    class Meta:
        model = Idol
        fields = [
            'id',
            'gpid',
            'ref_no',
            'name',
            'association_name',
            'dist_name',
            'zone',
            'division',
            'police_station',
            'ps_code',
            'address',
            'latitude',
            'longitude',
            'geocoding_status',
            'geocoding_confidence',
            'geocoding_result_type',
            'resolved_address',
            'start_gate_eligible',
            'idol_height',
            'height_classification',
            'is_operational_eligible',
            'pandal_height',
            'immersion_date',
            'river_name',
            'lake_type',
            'idol_type',
            'status',
            'procession_state',
            'created_at',
            'updated_at',
        ]

    start_gate_eligible = serializers.SerializerMethodField()

    def get_start_gate_eligible(self, obj):
        return bool(
            obj.geocoding_confidence in ['EXACT', 'HIGH']
            and obj.latitude is not None
            and obj.longitude is not None
        )

    def get_height_classification(self, obj):
        if obj.idol_height is None:
            return 'UNKNOWN'
        h = float(obj.idol_height)
        if 15.0 <= h < 21.0:
            return 'GREEN'
        elif 21.0 <= h < 26.0:
            return 'YELLOW'
        elif h >= 26.0:
            return 'RED'
        return 'SUBTHRESHOLD'

    def get_is_operational_eligible(self, obj):
        return bool(obj.idol_height is not None and obj.idol_height >= 15.0)


class IdolDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for idol inspection drawer.
    Includes contact info only for authorized senior/station officers.
    """
    contact_info = serializers.SerializerMethodField()
    height_classification = serializers.SerializerMethodField()
    is_operational_eligible = serializers.SerializerMethodField()
    start_gate_eligible = serializers.SerializerMethodField()

    def get_start_gate_eligible(self, obj):
        return bool(
            obj.geocoding_confidence in ['EXACT', 'HIGH']
            and obj.latitude is not None
            and obj.longitude is not None
        )

    class Meta:
        model = Idol
        fields = [
            'id',
            'gpid',
            'ref_no',
            'name',
            'association_name',
            'dist_name',
            'zone',
            'division',
            'police_station',
            'ps_code',
            'address',
            'instal_h_no',
            'instal_street',
            'instal_floor',
            'instal_village',
            'instal_pin',
            'latitude',
            'longitude',
            'geocoding_status',
            'geocoded_at',
            'geocoding_confidence',
            'geocoding_result_type',
            'resolved_address',
            'geocoding_query_used',
            'start_gate_eligible',
            'idol_height',
            'height_classification',
            'is_operational_eligible',
            'pandal_height',
            'immersion_date',
            'river_name',
            'lake_type',
            'idol_type',
            'specify_type',
            'idol_area_type',
            'instal_from_date',
            'instal_to_date',
            'status',
            'procession_state',
            'contact_info',
            'created_at',
            'updated_at',
        ]

    def get_height_classification(self, obj):
        if obj.idol_height is None:
            return 'UNKNOWN'
        h = float(obj.idol_height)
        if 15.0 <= h < 21.0:
            return 'GREEN'
        elif 21.0 <= h < 26.0:
            return 'YELLOW'
        elif h >= 26.0:
            return 'RED'
        return 'SUBTHRESHOLD'

    def get_is_operational_eligible(self, obj):
        return bool(obj.idol_height is not None and obj.idol_height >= 15.0)

    def get_contact_info(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        # Only SHO and above can view contact phone numbers
        if request.user.role in [UserRole.MAIN_OFFICER, UserRole.ACP, UserRole.SHO]:
            raw = obj.raw_metadata or {}
            return {
                'mobile_no': raw.get('mobile_no', ''),
                'email': raw.get('email', ''),
                'member1': raw.get('member1', ''),
                'mob_member1': raw.get('mob_member1', ''),
                'member2': raw.get('member2', ''),
                'mob_member2': raw.get('mob_member2', ''),
            }
        return None
