from django.test import TestCase
from django.db import IntegrityError
from apps.idols.models import Idol, ImportRun, ImportIssue, ImportIssueType


class IdolModelTests(TestCase):
    def test_create_idol_with_gpid(self):
        idol = Idol.objects.create(
            gpid='HYDCMRZCMNR0112',
            ref_no='REF1001',
            name='Vinayaka Association',
            zone='Charminar',
            division='Charminar',
            police_station='Charminar',
            ps_code='CMNR'
        )
        self.assertEqual(str(idol), 'HYDCMRZCMNR0112 - Vinayaka Association')
        self.assertEqual(idol.procession_state, 'NOT_STARTED')

    def test_gpid_uniqueness_enforced_at_db_level(self):
        Idol.objects.create(
            gpid='HYDCMRZCMNR0112',
            name='First Idol'
        )
        with self.assertRaises(IntegrityError):
            Idol.objects.create(
                gpid='HYDCMRZCMNR0112',
                name='Duplicate Idol'
            )

    def test_import_issue_creation(self):
        run = ImportRun.objects.create(file_name='test.xls', total_rows=10)
        issue = ImportIssue.objects.create(
            import_run=run,
            row_number=5,
            gpid='',
            issue_type=ImportIssueType.MISSING_GPID,
            error_message='Source record has no GPID.'
        )
        self.assertEqual(run.issues.count(), 1)
        self.assertEqual(issue.issue_type, ImportIssueType.MISSING_GPID)
