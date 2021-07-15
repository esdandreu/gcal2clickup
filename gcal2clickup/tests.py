from django.test import TestCase
from .gcal import Gcal

class GcalTestCase(TestCase):

    def test_get_credentials(self):
        print(Gcal.get_credentials())
