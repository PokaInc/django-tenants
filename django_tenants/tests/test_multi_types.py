from django.apps import apps
from django.conf import settings
from django.test.client import RequestFactory

from django_tenants.middleware import TenantMainMiddleware
from django_tenants.tests.testcases import BaseTestCase
from django_tenants.utils import get_tenant_model, get_tenant_domain_model, get_public_schema_name


class MultiTypeTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        delattr(settings, 'SHARED_APPS')
        delattr(settings, 'TENANT_APPS')

        settings.HAS_MULTI_TYPE_TENANTS = True
        settings.MULTI_TYPE_DATABASE_FIELD = 'type'  # needs to be a char field length depends of the max type value

        tenant_types = {
            "public": {  # this is the name of the public schema from get_public_schema_name
                "APPS": ['django_tenants',
                         'customers'],
                "URLCONF": "dts_test_project.urls",
            },
            "type1": {  # this is the name of the public schema from get_public_schema_name
                "APPS": ['dts_test_app',
                         'django.contrib.contenttypes',
                         'django.contrib.auth', ],
                "URLCONF": "dts_test_project.urls",
            },

        }

        settings.TENANT_TYPES = tenant_types

        installed_apps = []
        for schema in tenant_types:
            installed_apps += [app for app in tenant_types[schema]["APPS"] if app not in installed_apps]

        settings.INSTALLED_APPS = installed_apps
        cls.available_apps = settings.INSTALLED_APPS
        cls.sync_shared()
        cls.public_tenant = get_tenant_model()(schema_name=get_public_schema_name())
        cls.public_tenant.save()
        cls.public_domain = get_tenant_domain_model()(domain='test.com', tenant=cls.public_tenant)
        cls.public_domain.save()

    def tearDown(self):
        apps.unset_installed_apps()
        delattr(settings, 'HAS_MULTI_TYPE_TENANTS')
        delattr(settings, 'MULTI_TYPE_DATABASE_FIELD')
        delattr(settings, 'TENANT_TYPES')
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        from django.db import connection

        connection.set_schema_to_public()
        delattr(settings, 'HAS_MULTI_TYPE_TENANTS')
        delattr(settings, 'MULTI_TYPE_DATABASE_FIELD')
        delattr(settings, 'TENANT_TYPES')

        cls.public_domain.delete()
        cls.public_tenant.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.tm = TenantMainMiddleware()

        self.tenant_domain = 'tenant.test.com'
        self.tenant = get_tenant_model()(schema_name='test')
        self.tenant.save()
        self.domain = get_tenant_domain_model()(tenant=self.tenant, domain=self.tenant_domain)
        self.domain.save()

    def tearDown(self):
        from django.db import connection

        connection.set_schema_to_public()

        self.domain.delete()
        self.tenant.delete(force_drop=True)

        super().tearDown()

    def test_multi_routing(self):
        """
        Request path should not be altered.
        """
        request_url = '/any/request/'
        request = self.factory.get('/any/request/',
                                   HTTP_HOST=self.tenant_domain)
        self.tm.process_request(request)

        self.assertEqual(request.path_info, request_url)

        # request.tenant should also have been set
        self.assertEqual(request.tenant, self.tenant)

    # def test_tenant_routing(self):
    #     """
    #     Request path should not be altered.
    #     """
    #     request_url = '/any/request/'
    #     request = self.factory.get('/any/request/',
    #                                HTTP_HOST=self.tenant_domain)
    #     self.tm.process_request(request)
    #
    #     self.assertEqual(request.path_info, request_url)
    #
    #     # request.tenant should also have been set
    #     self.assertEqual(request.tenant, self.tenant)
    #
    # def test_public_schema_routing(self):
    #     """
    #     Request path should not be altered.
    #     """
    #     request_url = '/any/request/'
    #     request = self.factory.get('/any/request/',
    #                                HTTP_HOST=self.public_domain.domain)
    #     self.tm.process_request(request)
    #
    #     self.assertEqual(request.path_info, request_url)
    #
    #     # request.tenant should also have been set
    #     self.assertEqual(request.tenant, self.public_tenant)


