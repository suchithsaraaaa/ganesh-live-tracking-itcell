from rest_framework import serializers
from .models import Idol
from apps.accounts.models import UserRole


class IdolListSerializer(serializers.ModelSerializer):
    """
    Lean operational serializer for dashboard and maps.
    Strictly excludes sensitive personal phone numbers and emails.
    """
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
            'idol_height',
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


class IdolDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for idol inspection drawer.
    Includes contact info only for authorized senior/station officers.
    """
    contact_info = serializers.SerializerMethodField()

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
            'idol_height',
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
